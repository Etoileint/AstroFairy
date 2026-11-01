from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from dev.check_validation_handoff import FILE_FIELDS, PACKAGE, ROOT, check_files, check_return, fingerprint


class ValidationHandoffTests(unittest.TestCase):
    def test_identity_checks_reject_drift_and_path_escape(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-runs") as temporary:
            directory = Path(temporary)
            path = directory / "input.txt"
            path.write_text("Declared input", encoding="utf-8")
            rows = [{"path": path.name, **fingerprint(path)}]
            self.assertEqual(check_files(directory, rows), 1)
            path.write_text("Changed input", encoding="utf-8")
            with self.assertRaises(ValueError):
                check_files(directory, rows)
            rows[0]["path"] = "../escape"
            with self.assertRaises(ValueError):
                check_files(directory, rows)

    def test_return_structure_is_not_acceptance_and_evidence_drift_refuses(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-runs") as temporary:
            directory = Path(temporary)
            record = directory / "record.md"
            record.write_text("Explicitly unavailable in this validation fixture", encoding="utf-8")
            inventory = [{"path": record.name, **fingerprint(record)}]
            (directory / "inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
            baseline = json.loads((PACKAGE / "baseline.json").read_text(encoding="utf-8"))
            value = {
                "format": 1,
                "claim": "for_original_session_review",
                "source_manifest_sha256": baseline["source_manifest_sha256"],
                "product_accepted": False,
                "human_evidence": None,
                "work": {
                    f"P{number:02d}": {
                        "outcome": "not_observed",
                        "basis": "Fixture has no execution",
                        "evidence": [],
                    }
                    for number in range(3, 8)
                },
                **dict.fromkeys(FILE_FIELDS, record.name),
                "evidence_inventory": "inventory.json",
            }
            submission = directory / "submission.json"
            submission.write_text(json.dumps(value), encoding="utf-8")
            self.assertEqual(check_return(directory)["structure_and_file_identities"], "valid")
            value["work"]["P05"].update(outcome="supported", evidence=[record.name])
            submission.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(ValueError):
                check_return(directory)
            submission.write_text(
                json.dumps(value).replace('"format": 1', '"format": 1, "format": 1'), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                check_return(directory)
            value["work"]["P05"]["outcome"] = "not_observed"
            submission.write_text(json.dumps(value), encoding="utf-8")
            record.write_text("Changed after inventory", encoding="utf-8")
            with self.assertRaises(ValueError):
                check_return(directory)
