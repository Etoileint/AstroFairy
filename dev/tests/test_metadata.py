from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from dev.sync_metadata import ROOT, render, sync


class MetadataTests(unittest.TestCase):
    def test_version_change_is_detected_without_mutating_manifests(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = Path(temporary)
            shutil.copyfile(ROOT / "pyproject.toml", root / "pyproject.toml")
            shutil.copyfile(ROOT / "LICENSE", root / "LICENSE")
            version = root / "skills/astrofairy/scripts/astrofairy/_version.py"
            version.parent.mkdir(parents=True)
            version.write_text('__version__ = "1.2.3rc4"\n', encoding="utf-8")
            sync(root, check=False)
            manifest = root / ".claude-plugin/plugin.json"
            self.assertEqual(json.loads(manifest.read_bytes())["version"], "1.2.3-rc.4")
            original = manifest.read_bytes()
            version.write_text('__version__ = "1.2.3"\n', encoding="utf-8")
            self.assertIn(".claude-plugin/plugin.json", sync(root, check=True))
            self.assertEqual(manifest.read_bytes(), original)
            self.assertEqual(json.loads(render(root)[manifest])["version"], "1.2.3")
