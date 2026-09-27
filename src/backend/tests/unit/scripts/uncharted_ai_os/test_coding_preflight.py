"""Tests for the Uncharted AI OS coding-executor preflight CLI."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# test file: src/backend/tests/unit/scripts/uncharted_ai_os/test_coding_preflight.py
# parents[6] is the repository root.
REPO_ROOT = Path(__file__).resolve().parents[6]
MODULE_PATH = REPO_ROOT / "scripts" / "uncharted_ai_os" / "coding_preflight.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("coding_preflight", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


coding_preflight = _load_module()


class CodingPreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp = Path(self._tmpdir.name)

        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self._git("init", "-q")
        self._git("config", "user.email", "preflight@example.com")
        self._git("config", "user.name", "Preflight Test")

        (self.repo / "README.md").write_text("initial\n", encoding="utf-8")
        self._git("add", "README.md")
        self._git("commit", "-q", "-m", "Initial commit")
        self._git("checkout", "-q", "-b", "task/TASK-57")

        self.task_file = self.tmp / "task-57.md"
        self.task_file.write_text("Do the bounded thing.\n", encoding="utf-8")

    def _git(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"git {' '.join(args)} failed: {completed.stderr.strip()}"
            )
        return completed.stdout

    def _run(
        self,
        *extra: str,
        task_file: Path | None = None,
        repo: Path | None = None,
    ):
        argv = [
            "--repo",
            str(repo if repo is not None else self.repo),
            "--task-id",
            "TASK-57",
            "--task-file",
            str(task_file if task_file is not None else self.task_file),
            *extra,
        ]
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = coding_preflight.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_clean_task_branch_recommends_deepseek(self) -> None:
        code, out, err = self._run()

        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["task_id"], "TASK-57")
        self.assertEqual(payload["branch"], "task/TASK-57")
        self.assertEqual(payload["recommended_executor"], "deepseek")
        self.assertEqual(
            payload["head_commit"], self._git("rev-parse", "HEAD").strip()
        )
        self.assertEqual(Path(payload["repo"]), self.repo.resolve())

        # Task contents must never be echoed back in the recommendation.
        self.assertNotIn("Do the bounded thing.", out)

    def test_dirty_work_tree_is_rejected(self) -> None:
        (self.repo / "README.md").write_text("changed\n", encoding="utf-8")

        code, out, err = self._run()

        self.assertNotEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("clean", err.lower())

    def test_explicit_escalation_recommends_codex(self) -> None:
        code, out, err = self._run("--escalate")

        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["recommended_executor"], "codex")

    def test_empty_task_file_is_rejected(self) -> None:
        self.task_file.write_text("   \n", encoding="utf-8")

        code, out, err = self._run()

        self.assertNotEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("empty", err.lower())

    def test_detached_head_is_rejected(self) -> None:
        self._git("checkout", "-q", "--detach")

        code, out, err = self._run()

        self.assertNotEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("detached", err.lower())

    def test_repo_must_be_exact_worktree_root(self) -> None:
        nested = self.repo / "nested"
        nested.mkdir()

        code, out, err = self._run(repo=nested)

        self.assertNotEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("root", err.lower())

    def test_default_branches_are_rejected(self) -> None:
        for branch in ("main", "master"):
            with self.subTest(branch=branch):
                self._git("checkout", "-q", "-B", branch)
                try:
                    code, out, err = self._run()

                    self.assertNotEqual(code, 0)
                    self.assertEqual(out, "")
                    self.assertIn("protected", err.lower())
                finally:
                    self._git("checkout", "-q", "task/TASK-57")
                    self._git("branch", "-q", "-D", branch)

    def test_empty_task_id_is_rejected(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = coding_preflight.main([
                "--repo", str(self.repo),
                "--task-id", "  ",
                "--task-file", str(self.task_file),
            ])
        self.assertEqual(code, coding_preflight.EXIT_PREFLIGHT_FAILED)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("task id must be a short identifier", stderr.getvalue())

    def test_missing_git_is_reported_clearly(self) -> None:
        with patch.object(coding_preflight.subprocess, "run", side_effect=FileNotFoundError()):
            code, out, err = self._run()
        self.assertEqual(code, coding_preflight.EXIT_PREFLIGHT_FAILED)
        self.assertEqual(out, "")
        self.assertIn("git could not be started", err)


if __name__ == "__main__":
    unittest.main()
