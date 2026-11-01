from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from dev.check_work_program import ROOT, validate


class WorkProgramTests(unittest.TestCase):
    def test_current_source_scope_routes_all_original_objects(self) -> None:
        counts = validate(ROOT / "docs/repairs/work-program.json")
        self.assertEqual(
            counts,
            {
                "checks": 117,
                "requirements": 17,
                "scenarios": 16,
                "object_dispositions": 69,
                "notes": 4,
                "workstreams": 8,
            },
        )

    def test_missing_scope_and_premature_acceptance_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-runs") as temporary:
            root = Path(temporary)
            (root / "reviews").mkdir()
            (root / "repairs").mkdir()
            shutil.copyfile(
                ROOT / "docs/reviews/overall-assessment.json", root / "reviews/overall-assessment.json"
            )
            for name in ("work-program.json", "status.json", "F07-bounded-agent-responses.md"):
                shutil.copyfile(ROOT / "docs/repairs" / name, root / "repairs" / name)
            path = root / "repairs/work-program.json"
            original = json.loads(path.read_text(encoding="utf-8"))
            for fault in ("route", "note", "acceptance", "repairs"):
                value = json.loads(json.dumps(original))
                ledger = json.loads((ROOT / "docs/repairs/status.json").read_text(encoding="utf-8"))
                if fault == "route":
                    del value["routes"]["R07"]
                elif fault == "note":
                    value["work"][4]["notes"] = []
                elif fault == "acceptance":
                    value["product_accepted"] = True
                else:
                    ledger["findings"][0]["status"] = "verifying"
                path.write_text(json.dumps(value), encoding="utf-8")
                (root / "repairs/status.json").write_text(json.dumps(ledger), encoding="utf-8")
                with self.subTest(fault=fault), self.assertRaises(ValueError):
                    validate(path)
