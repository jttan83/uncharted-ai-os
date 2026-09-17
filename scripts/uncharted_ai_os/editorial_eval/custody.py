"""Separate persistent reveal custody for the Phase 1F-A holdout."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Literal

from pydantic import model_validator

from .blinding import balanced_position_assignments, build_blind_bundle, case_review_order
from .canonical import canonical_digest
from .contracts import BlindReviewBundle, RevealMapping, StrictModel
from .freeze_kit import (
    HoldoutBlindBundleRecord,
    HoldoutExecutionRecord,
    _experiment_base,
    _load_freeze_seed,
    load_frozen_manifest,
    load_holdout_batch,
)
from .review import locked_review_digests
from .storage import StorageRecordExistsError

if TYPE_CHECKING:
    from .storage import PrivateExperimentStorage


class RevealCustodyRecord(StrictModel):
    schema_version: Literal["phase-1f-a-reveal-custody-v1"] = "phase-1f-a-reveal-custody-v1"
    experiment_id: str
    freeze_digest: str
    bundle_digest: str
    mapping_digest: str
    mapping: RevealMapping

    @model_validator(mode="after")
    def validate_mapping_digest(self) -> RevealCustodyRecord:
        if canonical_digest(self.mapping) != self.mapping_digest:
            msg = "reveal mapping does not match its custody digest"
            raise ValueError(msg)
        return self


class RevealAuditRecord(StrictModel):
    schema_version: Literal["phase-1f-a-reveal-audit-v1"] = "phase-1f-a-reveal-audit-v1"
    experiment_id: str
    freeze_digest: str
    bundle_id: str
    mapping_digest: str
    locked_review_digests: dict[str, str]
    revealed_at: datetime

    @model_validator(mode="after")
    def validate_timestamp(self) -> RevealAuditRecord:
        if self.revealed_at.tzinfo is None:
            msg = "reveal audit timestamp must be timezone-aware"
            raise ValueError(msg)
        return self


class PersistentRevealCustodian:
    """Seal a mapping in memory only until it can be written to custody."""

    def __init__(self) -> None:
        self.__mapping: RevealMapping | None = None
        self.__bundle_digest: str | None = None

    def _seal(self, blind_bundle: BlindReviewBundle, mapping: RevealMapping) -> None:
        if self.__mapping is not None:
            msg = "persistent reveal custodian is already sealed"
            raise RuntimeError(msg)
        blind_ids = {candidate.blind_candidate_id for candidate in blind_bundle.candidates}
        mapped_ids = {entry.blind_candidate_id for entry in mapping.entries}
        if blind_ids != mapped_ids:
            msg = "reveal mapping must cover the blind bundle exactly"
            raise ValueError(msg)
        self.__mapping = mapping
        self.__bundle_digest = canonical_digest(blind_bundle)

    def persist(
        self,
        storage: PrivateExperimentStorage,
        *,
        experiment_id: str,
        freeze_digest: str,
        bundle_id: str,
    ) -> RevealCustodyRecord:
        if self.__mapping is None or self.__bundle_digest is None:
            msg = "persistent reveal custodian has not been sealed"
            raise RuntimeError(msg)
        record = RevealCustodyRecord(
            experiment_id=experiment_id,
            freeze_digest=freeze_digest,
            bundle_digest=self.__bundle_digest,
            mapping_digest=canonical_digest(self.__mapping),
            mapping=self.__mapping,
        )
        try:
            storage.write_json_once(_mapping_path(experiment_id, bundle_id), record)
        except StorageRecordExistsError:
            existing = storage.read_model(_mapping_path(experiment_id, bundle_id), RevealCustodyRecord)
            if existing != record:
                msg = "existing reveal custody does not match the deterministic blind mapping"
                raise ValueError(msg) from None
        return record


def validate_bundle_custody(
    storage: PrivateExperimentStorage,
    record: HoldoutBlindBundleRecord,
) -> None:
    """Verify custody exists for a persisted presentation without returning its mapping."""
    custody = storage.read_model(_mapping_path(record.experiment_id, record.bundle_id), RevealCustodyRecord)
    candidate_ids = {candidate.blind_candidate_id for candidate in record.bundle.candidates}
    mapped_ids = {entry.blind_candidate_id for entry in custody.mapping.entries}
    if (
        custody.experiment_id != record.experiment_id
        or custody.freeze_digest != record.freeze_digest
        or custody.bundle_digest != canonical_digest(record.bundle)
        or mapped_ids != candidate_ids
    ):
        msg = "persisted reveal custody does not match the main blind bundle"
        raise ValueError(msg)


def create_main_blind_bundle(
    storage: PrivateExperimentStorage,
    *,
    repo_root: Path,
    experiment_id: str,
    executions: tuple[HoldoutExecutionRecord, ...],
) -> HoldoutBlindBundleRecord:
    """Build the main blind bundle and persist its mapping on a separate path."""
    manifest = load_frozen_manifest(storage, experiment_id, repo_root=repo_root)
    batch = load_holdout_batch(storage, experiment_id)
    if any(record.run_kind != "main" or record.status != "succeeded" for record in executions):
        msg = "main blind bundle requires successful main executions only"
        raise ValueError(msg)
    execution_case_ids = [record.case_id for record in executions]
    if len(execution_case_ids) != len(set(execution_case_ids)) or set(execution_case_ids) != set(batch.case_digests):
        msg = "main blind bundle requires exactly one execution for every frozen holdout case"
        raise ValueError(msg)
    if any(
        record.experiment_id != experiment_id or record.freeze_digest != manifest.freeze_digest
        for record in executions
    ):
        msg = "holdout execution does not match the frozen experiment"
        raise ValueError(msg)
    for record in executions:
        persisted = storage.read_model(
            f"{_experiment_base(experiment_id)}/executions/{record.case_id}/{record.execution_id}.json",
            HoldoutExecutionRecord,
        )
        if persisted != record:
            msg = "blind bundle input does not match its immutable execution record"
            raise ValueError(msg)
        if any(
            submission.trace.experiment_version != manifest.experiment_version
            or submission.trace.manifest_version != manifest.manifest_version
            for submission in record.submissions
        ):
            msg = "execution trace does not bind the frozen experiment and manifest versions"
            raise ValueError(msg)
    seed = _load_freeze_seed(storage, manifest)
    positions = balanced_position_assignments(execution_case_ids, seed)
    custodian = PersistentRevealCustodian()
    bundle = build_blind_bundle(
        tuple(submission for record in executions for submission in record.submissions),
        secret_seed=seed,
        position_orders=positions,
        bundle_label=f"{experiment_id}_main",
        reveal_custodian=custodian,  # type: ignore[arg-type]
    )
    freeze_digest = manifest.freeze_digest
    if freeze_digest is None:  # pragma: no cover - validated frozen manifest.
        msg = "frozen manifest is missing its digest"
        raise RuntimeError(msg)
    record = HoldoutBlindBundleRecord(
        experiment_id=experiment_id,
        freeze_digest=freeze_digest,
        bundle_id=bundle.bundle_id,
        execution_ids=tuple(execution.execution_id for execution in executions),
        case_review_order=case_review_order(execution_case_ids, seed),
        bundle=bundle,
    )
    custodian.persist(
        storage,
        experiment_id=experiment_id,
        freeze_digest=freeze_digest,
        bundle_id=bundle.bundle_id,
    )
    storage.write_json_once(
        f"{_experiment_base(experiment_id)}/presentations/{bundle.bundle_id}.json",
        record,
    )
    return record


def reveal_mapping(
    storage: PrivateExperimentStorage,
    *,
    repo_root: Path,
    experiment_id: str,
    bundle_id: str,
    timestamp: datetime,
) -> RevealMapping:
    """Read custody only after every immutable human-review lock exists."""
    manifest = load_frozen_manifest(storage, experiment_id, repo_root=repo_root)
    review_digests = locked_review_digests(
        storage,
        experiment_id=experiment_id,
        bundle_id=bundle_id,
    )
    custody = storage.read_model(_mapping_path(experiment_id, bundle_id), RevealCustodyRecord)
    if custody.freeze_digest != manifest.freeze_digest:
        msg = "reveal custody does not match the frozen experiment"
        raise ValueError(msg)
    if custody.bundle_digest != review_digests["blind_bundle"]:
        msg = "reveal custody does not match the reviewed blind bundle"
        raise ValueError(msg)
    audit = RevealAuditRecord(
        experiment_id=experiment_id,
        freeze_digest=custody.freeze_digest,
        bundle_id=bundle_id,
        mapping_digest=custody.mapping_digest,
        locked_review_digests=review_digests,
        revealed_at=timestamp,
    )
    storage.write_json_once(
        f"{_experiment_base(experiment_id)}/reveals/{bundle_id}.json",
        audit,
    )
    return custody.mapping


def _mapping_path(experiment_id: str, bundle_id: str) -> str:
    return f"{_experiment_base(experiment_id)}/custody/mappings/{bundle_id}.json"
