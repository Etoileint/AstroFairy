from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from dev.lock_runtime import ROOT, render


class RuntimeLockTests(unittest.TestCase):
    def test_exact_generated_consumers_and_official_identity_guard(self) -> None:
        expected = render(ROOT)
        for path, value in expected.items():
            self.assertEqual(path.read_text(encoding="utf-8"), value)
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = Path(temporary)
            shutil.copyfile(ROOT / "pyproject.toml", root / "pyproject.toml")
            shutil.copytree(ROOT / "dev/runtime_snapshots", root / "dev/runtime_snapshots")
            snapshot = next((root / "dev/runtime_snapshots").glob("*.source"))
            snapshot.write_bytes(snapshot.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "identity"):
                render(root)

    def test_mismatched_runtime_closure_is_refused(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = Path(temporary)
            project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
            (root / "pyproject.toml").write_text(
                "\n".join(line for line in project.splitlines() if '"referencing==' not in line) + "\n",
                encoding="utf-8",
            )
            shutil.copytree(ROOT / "dev/runtime_snapshots", root / "dev/runtime_snapshots")
            manifest_path = root / "dev/runtime_snapshots/manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            del manifest["referencing"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "dependency"):
                render(root)
