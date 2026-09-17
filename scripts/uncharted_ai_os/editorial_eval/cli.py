"""Constrained local CLI for Phase 1F-A inspection and development rehearsal."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence  # noqa: TC003
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .canonical import canonical_digest, canonical_json_bytes
from .contracts import BlindReviewBundle, CaseBrief, PreUnblindingRecord, Stage1Assessment, Stage2Comparison
from .custody import reveal_mapping
from .development_runner import (
    APPROVED_DEVELOPMENT_PROFILES,
    DevelopmentRunError,
    execute_approved_development_run,
)
from .freeze_kit import (
    create_and_persist_freeze,
    intake_holdout_batch,
    load_frozen_manifest,
    run_frozen_main_holdout_batch,
)
from .manifest import FreezeManifest, create_freeze_receipt
from .review import (
    lock_pre_unblinding_record,
    lock_stage_1_assessment,
    lock_stage_2_comparison,
    next_stage_1_candidate,
    next_stage_2_bundle,
)
from .storage import PrivateExperimentStorage

ModelT = TypeVar("ModelT", bound=BaseModel)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect offline Phase 1F-A experimental JSON.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("validate-case", "Validate a canonical CaseBrief JSON file."),
        ("validate-manifest", "Validate a draft or frozen manifest JSON file."),
        ("validate-blind-bundle", "Validate a primary-review blind bundle."),
        ("emit-freeze-receipt", "Emit a sanitized receipt from a validated frozen manifest."),
    ):
        subparser = subparsers.add_parser(command, help=help_text)
        subparser.add_argument("path", type=Path)
    run_development = subparsers.add_parser(
        "run-development",
        help="Run one approved contaminated development fixture with durable private evidence.",
    )
    run_development.add_argument(
        "--profile",
        required=True,
        choices=APPROVED_DEVELOPMENT_PROFILES,
        help="V1 is pre-calibration; V2 is capacity-calibrated from contaminated development diagnostics.",
    )
    run_development.add_argument("--case", required=True)
    create_freeze = subparsers.add_parser("create-freeze", help="Persist the one private Phase 1F-A freeze.")
    create_freeze.add_argument("--experiment-id", required=True)
    create_freeze.add_argument("--operator", required=True)
    create_freeze.add_argument("--custodian", required=True)
    create_freeze.add_argument("--max-pilot-cost", required=True, type=Decimal)
    create_freeze.add_argument("--max-review-minutes", required=True, type=int)
    create_freeze.add_argument("--retention-days", required=True, type=int)
    intake = subparsers.add_parser("intake-holdouts", help="Validate and privately persist one frozen holdout batch.")
    intake.add_argument("--experiment-id", required=True)
    intake.add_argument("--source", required=True, type=Path)
    run_holdouts = subparsers.add_parser(
        "run-holdout-batch",
        help="Run or safely resume the frozen MAIN holdout batch and build its blind bundle.",
    )
    run_holdouts.add_argument("--experiment-id", required=True)
    for command, help_text in (
        ("present-next-stage-1", "Show only the next independently reviewed candidate."),
        ("present-next-stage-2", "Show the next comparison after Stage 1 is fully locked."),
        ("lock-stage-1", "Lock one Stage 1 assessment from a local JSON record."),
        ("lock-stage-2", "Lock one Stage 2 comparison from a local JSON record."),
        ("lock-pre-unblinding", "Lock identity guesses and the pre-unblinding decision record."),
        ("reveal", "Reveal the mapping only after every required review lock."),
    ):
        command_parser = subparsers.add_parser(command, help=help_text)
        command_parser.add_argument("--experiment-id", required=True)
        command_parser.add_argument("--bundle-id", required=True)
        if command.startswith("lock-"):
            command_parser.add_argument("--record", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command in {
            "present-next-stage-1",
            "present-next-stage-2",
            "lock-stage-1",
            "lock-stage-2",
            "lock-pre-unblinding",
            "reveal",
        }:
            load_frozen_manifest(
                PrivateExperimentStorage(Path.cwd()),
                args.experiment_id,
                repo_root=Path.cwd(),
            )
        if args.command == "validate-case":
            model = _read_model(args.path, CaseBrief)
            _print_summary(model)
        elif args.command == "validate-manifest":
            model = _read_model(args.path, FreezeManifest)
            _print_summary(model)
        elif args.command == "validate-blind-bundle":
            model = _read_model(args.path, BlindReviewBundle)
            _print_summary(model)
        elif args.command == "emit-freeze-receipt":
            manifest = _read_model(args.path, FreezeManifest)
            print(canonical_json_bytes(create_freeze_receipt(manifest)).decode())
        elif args.command == "run-development":
            result = execute_approved_development_run(
                Path.cwd(),
                profile=args.profile,
                case_id=args.case,
            )
            candidate = result.candidate
            print(f"operator_run_id: {result.operator_run_id}")
            print(f"candidate_id: {candidate.blind_candidate_id}")
            print(f"decision: {candidate.submission.decision.value}")
            if candidate.submission.spoken_script is not None:
                print(f"spoken_script: {candidate.submission.spoken_script}")
            if candidate.submission.explanation is not None:
                print(f"explanation: {candidate.submission.explanation}")
            if candidate.submission.next_action is not None:
                print(f"next_action: {candidate.submission.next_action}")
        elif args.command == "create-freeze":
            receipt = create_and_persist_freeze(
                Path.cwd(),
                PrivateExperimentStorage(Path.cwd()),
                experiment_id=args.experiment_id,
                experiment_operator=args.operator,
                mapping_custodian=args.custodian,
                max_pilot_cost=args.max_pilot_cost,
                max_human_review_minutes_per_case=args.max_review_minutes,
                retention_days=args.retention_days,
                timestamp=datetime.now(timezone.utc),
            )
            print(canonical_json_bytes(receipt).decode())
        elif args.command == "intake-holdouts":
            batch = intake_holdout_batch(
                PrivateExperimentStorage(Path.cwd()),
                experiment_id=args.experiment_id,
                source_path=args.source,
                timestamp=datetime.now(timezone.utc),
                repo_root=Path.cwd(),
            )
            print(f"accepted holdout batch: count={len(batch.cases)} digest={canonical_digest(batch)}")
        elif args.command == "run-holdout-batch":
            result = run_frozen_main_holdout_batch(
                Path.cwd(),
                PrivateExperimentStorage(Path.cwd()),
                experiment_id=args.experiment_id,
                timestamp=datetime.now(timezone.utc),
            )
            print(f"experiment_id: {result.experiment_id}")
            print(f"completed_case_count: {result.completed_case_count}")
            print(f"bundle_id: {result.bundle_id}")
            print(f"candidate_count: {result.candidate_count}")
            print("READY FOR STAGE 1")
        elif args.command == "present-next-stage-1":
            candidate = next_stage_1_candidate(
                PrivateExperimentStorage(Path.cwd()),
                experiment_id=args.experiment_id,
                bundle_id=args.bundle_id,
            )
            print("stage 1 complete" if candidate is None else canonical_json_bytes(candidate).decode())
        elif args.command == "present-next-stage-2":
            bundle = next_stage_2_bundle(
                PrivateExperimentStorage(Path.cwd()),
                experiment_id=args.experiment_id,
                bundle_id=args.bundle_id,
            )
            print("stage 2 complete" if bundle is None else canonical_json_bytes(bundle).decode())
        elif args.command == "lock-stage-1":
            lock_stage_1_assessment(
                PrivateExperimentStorage(Path.cwd()),
                experiment_id=args.experiment_id,
                bundle_id=args.bundle_id,
                assessment=_read_model(args.record, Stage1Assessment),
            )
            print("Stage 1 assessment locked.")
        elif args.command == "lock-stage-2":
            lock_stage_2_comparison(
                PrivateExperimentStorage(Path.cwd()),
                experiment_id=args.experiment_id,
                bundle_id=args.bundle_id,
                comparison=_read_model(args.record, Stage2Comparison),
            )
            print("Stage 2 comparison locked.")
        elif args.command == "lock-pre-unblinding":
            lock_pre_unblinding_record(
                PrivateExperimentStorage(Path.cwd()),
                experiment_id=args.experiment_id,
                bundle_id=args.bundle_id,
                record=_read_model(args.record, PreUnblindingRecord),
            )
            print("Pre-unblinding record locked.")
        elif args.command == "reveal":
            mapping = reveal_mapping(
                PrivateExperimentStorage(Path.cwd()),
                repo_root=Path.cwd(),
                experiment_id=args.experiment_id,
                bundle_id=args.bundle_id,
                timestamp=datetime.now(timezone.utc),
            )
            print(canonical_json_bytes(mapping).decode())
        else:  # pragma: no cover - argparse enforces the choices.
            return 2
    except DevelopmentRunError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, RuntimeError, ValueError):
        # Validation errors may echo sensitive input values, so the CLI reports
        # only the path and contract type. Detailed debugging stays local.
        if args.command == "run-development":
            print("Development rehearsal validation failed.", file=sys.stderr)
        elif hasattr(args, "path"):
            print(f"Validation failed for {args.path}.", file=sys.stderr)
        else:
            print(f"{args.command} failed.", file=sys.stderr)
        return 2
    return 0


def _read_model(path: Path, model_type: type[ModelT]) -> ModelT:
    return model_type.model_validate_json(path.read_bytes())


def _print_summary(model: BaseModel) -> None:
    print(f"valid {type(model).__name__} {canonical_digest(model)}")
