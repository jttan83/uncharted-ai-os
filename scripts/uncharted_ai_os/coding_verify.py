#!/usr/bin/env python3
"""Run focused checks and append the outcome to the original coding task file.

This helper does not invoke a model, commit, push, or mark a task complete.
Check output is suppressed because tools may emit credentials or customer data.

A run is reported as ``checks_passed`` only when every check passes *and* the
git working tree contains changes to verify. If every check passes but the
working tree is clean, the run is reported as ``no_changes`` and the process
exits nonzero so an empty verification cannot be mistaken for real work.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

from coding_preflight import (
    PreflightError,
    current_branch,
    head_commit,
    resolve_repo,
    validate_task_file,
)


def verify(repo: Path, checks: list[str]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    commands = [
        ("git diff --check", ["git", "-C", str(repo), "diff", "--check"]),
        (
            "git diff --cached --check",
            ["git", "-C", str(repo), "diff", "--cached", "--check"],
        ),
    ]
    for index, check in enumerate(checks, start=1):
        try:
            argv = shlex.split(check)
        except ValueError as exc:
            raise PreflightError(f"check {index} has invalid quoting") from exc
        if not argv:
            raise PreflightError(f"check {index} is empty")
        commands.append((f"check {index}", argv))

    for label, argv in commands:
        try:
            completed = subprocess.run(
                argv, cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            passed = completed.returncode == 0
        except OSError:
            passed = False
        results.append({"name": label, "passed": passed})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify code and record results in the original task file"
    )
    parser.add_argument("--repo", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--executor", choices=["deepseek", "codex", "kimi"], required=True)
    parser.add_argument(
        "--check", action="append", required=True, help="A check command; may be repeated"
    )
    args = parser.parse_args(argv)

    try:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", args.task_id):
            raise PreflightError("task id must be a short identifier")
        repo = resolve_repo(args.repo)
        task_file = validate_task_file(args.task_file)
        branch = current_branch(repo)
        commit = head_commit(repo)
        status = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True,
            text=True,
        )
        if status.returncode != 0:
            raise PreflightError("git status failed")
        has_changes = bool(status.stdout.strip())

        results = verify(repo, args.check)
        checks_passed = all(result["passed"] for result in results)

        if not checks_passed:
            outcome = "checks_failed"
            result_line = "checks failed; repair or escalate"
        elif not has_changes:
            outcome = "no_changes"
            result_line = "no changes detected; nothing to verify"
        else:
            outcome = "checks_passed"
            result_line = "checks passed; review required"

        lines = [
            "",
            "## Coding verification",
            f"- Task: {args.task_id}",
            f"- Executor: {args.executor}",
            f"- Git branch: {branch}",
            f"- Git HEAD: {commit}",
            f"- Uncommitted changes: {'yes' if has_changes else 'no'}",
            f"- Result: {result_line}",
            *(
                f"- {result['name']}: {'pass' if result['passed'] else 'fail'}"
                for result in results
            ),
            "",
        ]
        with task_file.open("a", encoding="utf-8") as task:
            task.write("\n".join(lines))
    except (PreflightError, OSError) as exc:
        # A filesystem error can reveal a path; never echo its raw exception.
        message = str(exc) if isinstance(exc, PreflightError) else "could not write task record"
        print(json.dumps({"error": message}), file=sys.stderr)
        return 2

    print(json.dumps({
        "task_id": args.task_id,
        "result": outcome,
        "checks": results,
    }))
    return 0 if outcome == "checks_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
