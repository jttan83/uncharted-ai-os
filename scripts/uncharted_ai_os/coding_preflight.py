#!/usr/bin/env python3
"""Coding-executor preflight for Uncharted AI OS MVP 1 tasks.

This is a deliberately small, standard-library-only helper. Given a task
record and a checkout, it confirms the run is safe to start and prints a JSON
recommendation for which coding executor should pick the task up.

It is a recommendation tool only. It never calls a model, never touches
Notion, never writes a task record, never prints task contents or secrets,
and never commits or pushes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

DEFAULT_EXECUTOR = "deepseek"
ESCALATED_EXECUTOR = "codex"

# Branches a coding executor must never treat as a task branch.
PROTECTED_BRANCHES = frozenset({"main", "master"})

EXIT_OK = 0
EXIT_PREFLIGHT_FAILED = 2


class PreflightError(Exception):
    """Raised when a checkout is not safe for a coding executor to start."""


def _git(repo: Path, *args: str) -> "subprocess.CompletedProcess[str]":
    """Run a git command inside ``repo`` without raising on failure."""
    try:
        return subprocess.run(
            ["git", "-C", os.fspath(repo), *args],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise PreflightError("git could not be started") from exc


def _git_output(repo: Path, *args: str) -> str:
    """Run a git command and return its stripped stdout, raising on failure."""
    result = _git(repo, *args)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise PreflightError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def resolve_repo(repo_arg: str) -> Path:
    """Return the resolved path to a git work tree root, or raise ``PreflightError``.

    ``--repo`` must point at the exact worktree root; a subdirectory of a
    repository is rejected so executors always operate from a well-defined
    top-level checkout.
    """
    repo = Path(repo_arg).expanduser()
    if not repo.exists():
        raise PreflightError(f"repository path does not exist: {repo}")
    if not repo.is_dir():
        raise PreflightError(f"repository path is not a directory: {repo}")

    inside = _git(repo, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        raise PreflightError(f"not a git working tree: {repo}")

    resolved_repo = repo.resolve()
    toplevel = Path(_git_output(repo, "rev-parse", "--show-toplevel")).resolve()
    if resolved_repo != toplevel:
        raise PreflightError(
            "--repo must be the exact git worktree root; "
            f"use {toplevel} instead of {resolved_repo}"
        )
    return resolved_repo


def validate_task_file(task_file_arg: str) -> Path:
    """Confirm the task file exists and is non-empty, without exposing its text."""
    task_file = Path(task_file_arg).expanduser()
    if not task_file.exists():
        raise PreflightError(f"task file does not exist: {task_file}")
    if not task_file.is_file():
        raise PreflightError(f"task file is not a regular file: {task_file}")

    contents = task_file.read_text(encoding="utf-8", errors="replace")
    if not contents.strip():
        raise PreflightError("task file is empty")
    return task_file.resolve()


def current_branch(repo: Path) -> str:
    """Return the current branch name, rejecting detached HEAD and protected branches."""
    branch = _git_output(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if branch == "HEAD":
        raise PreflightError(
            "repository is in a detached HEAD state; a named task branch is required"
        )
    if not branch:
        raise PreflightError("repository has no current branch")
    if branch in PROTECTED_BRANCHES:
        raise PreflightError(
            f"refusing to start a task on protected branch: {branch}"
        )
    return branch


def ensure_clean_work_tree(repo: Path) -> None:
    """Reject a working tree with staged, modified, or untracked changes."""
    status = _git_output(repo, "status", "--porcelain")
    if status:
        raise PreflightError(
            "working tree is not clean; commit or stash changes before starting"
        )


def head_commit(repo: Path) -> str:
    """Return the full SHA of HEAD."""
    return _git_output(repo, "rev-parse", "HEAD")


def build_recommendation(
    *,
    task_id: str,
    repo: Path,
    branch: str,
    commit: str,
    escalate: bool,
) -> dict:
    """Build the JSON-serialisable preflight recommendation."""
    return {
        "task_id": task_id,
        "repo": str(repo),
        "branch": branch,
        "head_commit": commit,
        "recommended_executor": ESCALATED_EXECUTOR if escalate else DEFAULT_EXECUTOR,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coding_preflight",
        description=(
            "Validate a checkout and recommend a coding executor for a task. "
            "Task file contents are checked for emptiness and never printed."
        ),
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Path to the target git repository (must be the worktree root).",
    )
    parser.add_argument(
        "--task-id",
        required=True,
        help="Identifier of the task being started.",
    )
    parser.add_argument(
        "--task-file",
        required=True,
        help="Path to the task record; only its non-emptiness is checked.",
    )
    parser.add_argument(
        "--escalate",
        action="store_true",
        help="Recommend the stronger executor after a failed or risky attempt.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", args.task_id):
            raise PreflightError("task id must be a short identifier")
        repo = resolve_repo(args.repo)
        validate_task_file(args.task_file)
        branch = current_branch(repo)
        ensure_clean_work_tree(repo)
        commit = head_commit(repo)
    except PreflightError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return EXIT_PREFLIGHT_FAILED

    recommendation = build_recommendation(
        task_id=args.task_id,
        repo=repo,
        branch=branch,
        commit=commit,
        escalate=args.escalate,
    )
    print(json.dumps(recommendation, indent=2, sort_keys=True))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
