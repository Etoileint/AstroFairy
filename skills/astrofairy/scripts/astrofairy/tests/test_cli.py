from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from astrofairy.tests._support import ROOT, WorkshopTest


class CliTests(WorkshopTest):
    def test_missing_dependencies_are_diagnosed_by_both_entrypoints_without_home_creation(self) -> None:
        module = (
            "import runpy,sys;sys.path.insert(0,sys.argv[1]);"
            "sys.argv=['astrofairy',*sys.argv[2:]];runpy.run_module('astrofairy',run_name='__main__')"
        )
        entries = [
            [sys.executable, "-I", "-S", str(ROOT / "skills/astrofairy/scripts/fairy.py")],
            [sys.executable, "-I", "-S", "-c", module, str(ROOT / "skills/astrofairy/scripts")],
        ]
        for index, entry in enumerate(entries):
            for operation in ("doctor", "schema", "start"):
                with self.subTest(entry=index, operation=operation):
                    home = self.home / f"missing-{index}-{operation}"
                    arguments = [*entry, "--home", str(home), operation]
                    if operation == "start":
                        arguments.extend(["--request", "Work"])
                    result = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True, check=False)
                    data = json.loads(result.stdout)
                    self.assertEqual(result.stderr, "")
                    self.assertFalse(home.exists())
                    if operation == "schema":
                        self.assertEqual(result.returncode, 0)
                    elif operation == "doctor":
                        self.assertFalse(data["ready"])
                        self.assertEqual(data["runtime"]["error"], "runtime_setup_required")
                    else:
                        self.assertEqual(data["error"], "runtime_setup_required")

    def test_doctor_rejects_a_file_in_the_data_directory_path(self) -> None:
        blocker = self.home / "not-a-directory"
        blocker.write_text("file", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "astrofairy", "--home", str(blocker / "state"), "doctor"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["ready"])
        self.assertEqual(blocker.read_text(encoding="utf-8"), "file")

    def test_doctor_checks_environment_without_creating_state(self) -> None:
        home = self.home / "not-created"
        result = subprocess.run(
            [sys.executable, "-m", "astrofairy", "--home", str(home), "doctor"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ready"])
        self.assertFalse(home.exists())

    def test_failed_invocation_has_nonzero_status_and_keeps_receipt(self) -> None:
        ref = self.workshop.library.propose(self.proposal())
        task = self.workshop.start("Use a guide")
        result = self.cli(
            "submit", task, data={"op": "invoke", "capability": "asset.read", "parameters": {"ref": ref}}
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "failed")
        self.assertEqual(next(iter(self.workshop.state(task).calls.values()))["status"], "failed")

    def cli(self, *arguments: str, data: dict[str, Any] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "astrofairy", "--home", str(self.home), *arguments],
            cwd=ROOT,
            input=json.dumps(data) if data is not None else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_request_with_shell_syntax_is_plain_data(self) -> None:
        request = "给我整理材料 $(echo never) `echo literal`"
        result = self.cli("start", "--request", request)
        self.assertEqual(result.returncode, 0, result.stderr)
        task = json.loads(result.stdout)["task"]
        self.assertEqual(self.workshop.state(task).spec["request"], request)

    def test_json_submission_errors_have_nonzero_status(self) -> None:
        task = self.workshop.start("Work")
        result = self.cli("submit", task, data={"op": "observe", "actor": "runner"})
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["error"], "invalid")

    def test_schema_is_available_without_creating_home(self) -> None:
        home = self.home / "never-created"
        result = subprocess.run(
            [sys.executable, "-m", "astrofairy", "--home", str(home), "schema"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertFalse(home.exists())
        self.assertIn("review", json.loads(result.stdout)["commands"])
