from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from astrofairy import FairyError, Workshop
from astrofairy.tests._support import ROOT, WorkshopTest


class InitialAgreementTests(WorkshopTest):
    def cli_start(self, spec: dict[str, Any], home: Path) -> subprocess.CompletedProcess[str]:
        path = Path(self.temporary.name) / "spec.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "astrofairy",
                "--home",
                str(home),
                "start",
                "--request",
                "Work",
                "--spec",
                str(path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_invalid_field_values_create_no_task_blob_workspace_or_cli_home(self) -> None:
        variants = (
            [{"goal": value} for value in (None, False, 0, [], {}, "", " ")]
            + [{"assumptions": value} for value in (None, False, 0, {}, "text", ["valid", 3])]
            + [{"criteria": value} for value in (None, False, 0, {}, [], "text")]
            + [{"unexpected": "value"}]
        )
        attachment = Path(self.temporary.name) / "input.txt"
        attachment.write_text("Do not capture invalid requests", encoding="utf-8")
        for index, spec in enumerate(variants):
            with self.subTest(spec=spec):
                home = Path(self.temporary.name) / f"invalid-{index}"
                result = self.cli_start(spec, home)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(json.loads(result.stdout)["error"], "invalid")
                self.assertFalse(home.exists())
                with self.assertRaises(FairyError):
                    self.workshop.start("Work", spec=spec, inputs=[attachment])
                self.assertEqual(self.workshop.store.tasks(), [])
                self.assertEqual(
                    self.workshop.store.connection.execute("SELECT count(*) FROM blobs").fetchone()[0], 0
                )
                self.assertFalse((self.home / "workspaces").exists())

    def test_accepted_initial_agreement_is_the_first_and_only_event(self) -> None:
        spec = {
            "goal": "Create an internal brief",
            "assumptions": ["Internal audience", "Source amounts fixed"],
        }
        home = Path(self.temporary.name) / "valid"
        result = self.cli_start(spec, home)
        self.assertEqual(result.returncode, 0, result.stderr)
        with Workshop(home) as other:
            task = json.loads(result.stdout)["task"]
            state = other.state(task)
            self.assertEqual((state.seq, state.revision), (1, 1))
            self.assertEqual(state.spec["goal"], spec["goal"])
            self.assertEqual(state.spec["assumptions"], spec["assumptions"])
            self.assertEqual(other.store.events(task)[0]["payload"]["spec"], state.spec)
        empty = self.workshop.start("Use defaults", spec={"assumptions": []})
        self.assertEqual(self.workshop.state(empty).spec["goal"], "Use defaults")
        self.assertEqual(self.workshop.state(empty).spec["assumptions"], [])

    def test_later_attachment_failure_rolls_back_earlier_blob(self) -> None:
        source = Path(self.temporary.name) / "first.txt"
        source.write_bytes(b"A valid first input")
        with self.assertRaises(OSError):
            self.workshop.start("Work", inputs=[source, source.with_name("missing.txt")])
        self.assertEqual(self.workshop.store.tasks(), [])
        self.assertEqual(
            self.workshop.store.connection.execute("SELECT count(*) FROM blobs").fetchone()[0], 0
        )
        self.assertFalse((self.home / "workspaces").exists())

    def test_initial_contract_detaches_caller_parameters(self) -> None:
        parameters: dict[str, Any] = {"text": "fixed"}
        spec = {
            "criteria": [
                {
                    "id": "text",
                    "description": "Keep fixed text",
                    "checker": "contains",
                    "parameters": parameters,
                }
            ]
        }
        task = self.workshop.start("Work", spec=spec)
        parameters["text"] = "changed"
        self.assertEqual(self.workshop.state(task).spec["criteria"][0]["parameters"], {"text": "fixed"})
