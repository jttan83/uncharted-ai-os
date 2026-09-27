"""Focused tests for recording coding verification in the original task."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[6]
CLI = ROOT / "scripts" / "uncharted_ai_os" / "coding_verify.py"


class CodingVerifyTest(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        for args in (
            ("init", "-q"),
            ("config", "user.email", "test@example.com"),
            ("config", "user.name", "Test"),
        ):
            subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)
        (self.repo / "README.md").write_text("start\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "initial"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "checkout", "-qb", "task/TASK-57"], check=True)
        self.task = self.root / "TASK-57.txt"
        self.task.write_text("Original task text.\n", encoding="utf-8")

    def run_cli(self, check: str, task_id: str = "TASK-57") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), "--repo", str(self.repo), "--task-id", task_id,
             "--task-file", str(self.task), "--executor", "deepseek", "--check", check],
            capture_output=True, text=True,
        )

    def test_success_appends_to_original_task_without_completing_it(self) -> None:
        result = self.run_cli(f"{sys.executable} -c 'import sys; sys.exit(0)'")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["result"], "checks_passed")
        content = self.task.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("Original task text.\n"))
        self.assertIn("checks passed; review required", content)
        self.assertIn("Git branch: task/TASK-57", content)
        self.assertIn("Uncommitted changes: no", content)

    def test_failure_is_recorded_without_leaking_check_output(self) -> None:
        result = self.run_cli(f"{sys.executable} -c 'import sys; print(\"secret\"); sys.exit(1)'")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["result"], "checks_failed")
        self.assertIn("checks failed; repair or escalate", self.task.read_text(encoding="utf-8"))
        self.assertNotIn("secret", result.stdout + result.stderr + self.task.read_text(encoding="utf-8"))

    def test_invalid_task_id_does_not_modify_task(self) -> None:
        result = self.run_cli("true", "TASK-57\nspoofed")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.task.read_text(encoding="utf-8"), "Original task text.\n")

    def test_staged_whitespace_error_fails_verification(self) -> None:
        (self.repo / "README.md").write_text("bad trailing space \n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(self.repo), "add", "README.md"], check=True
        )
        result = self.run_cli("true")
        self.assertEqual(result.returncode, 1)
        self.assertIn("git diff --cached --check: fail", self.task.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
