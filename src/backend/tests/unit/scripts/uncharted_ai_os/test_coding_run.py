"""A local end-to-end test of the DeepSeek launcher without an API call."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[6]
CLI = ROOT / "scripts" / "uncharted_ai_os" / "coding_run.py"


class CodingRunTest(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        for command in (
            ("init", "-q"),
            ("config", "user.email", "test@example.com"),
            ("config", "user.name", "Test"),
        ):
            subprocess.run(["git", "-C", str(self.repo), *command], check=True, capture_output=True)
        (self.repo / "AGENTS.md").write_text("Follow the task.\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "AGENTS.md"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "initial"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "checkout", "-qb", "task-59"], check=True)
        self.task = self.root / "TASK-59.txt"
        self.task.write_text("Create result.txt.\n", encoding="utf-8")
        self.bin = self.root / "bin"
        self.bin.mkdir()

    def run_cli(self, *, key: str = "test-key") -> subprocess.CompletedProcess[str]:
        env = dict(os.environ, DEEPSEEK_API_KEY=key, PATH=f"{self.bin}:{os.environ['PATH']}")
        return subprocess.run(
            [
                sys.executable, str(CLI),
                "--repo", str(self.repo), "--task-id", "TASK-59",
                "--task-file", str(self.task), "--file", "result.txt",
                "--check", f"{sys.executable} -c 'import sys; sys.exit(0)'",
            ],
            env=env, capture_output=True, text=True,
        )

    def fake_aider(self, content: str) -> None:
        path = self.bin / "aider"
        path.write_text("#!/bin/sh\n" + content, encoding="utf-8")
        path.chmod(0o755)

    def test_success_records_checks_in_original_task(self) -> None:
        self.fake_aider("printf 'done\\n' > result.txt\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DeepSeek is starting", result.stdout)
        self.assertIn('"result": "checks_passed"', result.stdout)
        self.assertIn("checks passed; review required", self.task.read_text(encoding="utf-8"))
        self.assertEqual((self.repo / "result.txt").read_text(encoding="utf-8"), "done\n")

    def test_executor_failure_does_not_claim_checks_passed(self) -> None:
        self.fake_aider("exit 1\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("executor failed", self.task.read_text(encoding="utf-8"))
        self.assertNotIn("checks passed", self.task.read_text(encoding="utf-8"))

    def test_no_change_run_is_not_accepted(self) -> None:
        self.fake_aider("exit 0\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn('"result": "no_changes"', result.stdout)
        self.assertIn("no changes detected", self.task.read_text(encoding="utf-8"))

    def test_missing_key_stops_before_executor(self) -> None:
        self.fake_aider("printf 'wrong\\n' > result.txt\n")
        result = self.run_cli(key="")
        self.assertEqual(result.returncode, 2)
        self.assertIn("nothing started", result.stderr)
        self.assertFalse((self.repo / "result.txt").exists())


if __name__ == "__main__":
    unittest.main()
