#!/usr/bin/env python3
"""Run the MVP coding lane: preflight, Aider/DeepSeek, then verification.

The task file remains the original task record. This command never commits,
pushes, or marks the task complete. A human still reviews the code diff.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one bounded DeepSeek coding task")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--file", action="append", required=True, help="Editable repo path; repeat")
    parser.add_argument("--check", action="append", required=True, help="Check command; repeat")
    args = parser.parse_args(argv)

    repo = Path(args.repo).expanduser().resolve()
    script_dir = Path(__file__).resolve().parent
    preflight = subprocess.run(
        [
            sys.executable, str(script_dir / "coding_preflight.py"),
            "--repo", str(repo), "--task-id", args.task_id,
            "--task-file", args.task_file,
        ],
        capture_output=True, text=True,
    )
    if preflight.returncode:
        sys.stderr.write(preflight.stderr)
        return preflight.returncode
    recommendation = json.loads(preflight.stdout)
    if recommendation["recommended_executor"] != "deepseek":
        print("This launcher only runs the DeepSeek lane", file=sys.stderr)
        return 2

    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DeepSeek key is not loaded in this Terminal; nothing started", file=sys.stderr)
        return 2
    if shutil.which("aider") is None:
        print("aider is not installed or is not on PATH; nothing started", file=sys.stderr)
        return 2
    if not (repo / "AGENTS.md").is_file():
        print("AGENTS.md is missing from this repo; nothing started", file=sys.stderr)
        return 2

    editable: list[str] = []
    for name in args.file:
        path = (repo / name).resolve()
        if not path.is_relative_to(repo) or path == repo:
            print("--file must name a path inside the repo", file=sys.stderr)
            return 2
        editable.append(str(path))

    task_file = str(Path(args.task_file).expanduser().resolve())
    print(f"Preflight passed on {recommendation['branch']}; DeepSeek is starting.", flush=True)
    run = subprocess.run(
        [
            "aider", "--model", "deepseek/deepseek-flash", "--map-tokens", "0",
            "--no-auto-commits", "--no-dirty-commits", "--no-gitignore",
            "--yes", "--read", "AGENTS.md", "--message-file", task_file,
            *editable,
        ],
        cwd=repo,
    )
    if run.returncode:
        with Path(task_file).open("a", encoding="utf-8") as task:
            task.write(
                "\n## Coding execution\n"
                f"- Task: {args.task_id}\n- Executor: deepseek\n"
                "- Result: executor failed; review or retry required\n"
            )
        print("DeepSeek run failed; recorded in task. No verification was claimed.", file=sys.stderr)
        return 1

    print("DeepSeek finished. Running checks and recording the result.", flush=True)
    verify = subprocess.run(
        [
            sys.executable, str(script_dir / "coding_verify.py"),
            "--repo", str(repo), "--task-id", args.task_id,
            "--task-file", task_file, "--executor", "deepseek",
            *(item for check in args.check for item in ("--check", check)),
        ],
        cwd=repo,
    )
    print("Review the diff before accepting or committing the change.", flush=True)
    return verify.returncode


if __name__ == "__main__":
    raise SystemExit(main())
