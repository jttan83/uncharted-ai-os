"""Constrained local CLI for Phase 1F-A inspection and development rehearsal."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence  # noqa: TC003
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .canonical import canonical_digest, canonical_json_bytes
from .contracts import BlindReviewBundle, CaseBrief
from .development_runner import (
    APPROVED_DEVELOPMENT_PROFILES,
    DevelopmentRunError,
    execute_approved_development_run,
)
from .manifest import FreezeManifest, create_freeze_receipt

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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
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
        else:  # pragma: no cover - argparse enforces the choices.
            return 2
    except DevelopmentRunError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, ValueError):
        # Validation errors may echo sensitive input values, so the CLI reports
        # only the path and contract type. Detailed debugging stays local.
        if args.command == "run-development":
            print("Development rehearsal validation failed.", file=sys.stderr)
        else:
            print(f"Validation failed for {args.path}.", file=sys.stderr)
        return 2
    return 0


def _read_model(path: Path, model_type: type[ModelT]) -> ModelT:
    return model_type.model_validate_json(path.read_bytes())


def _print_summary(model: BaseModel) -> None:
    print(f"valid {type(model).__name__} {canonical_digest(model)}")
