from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

from dev.sync_metadata import ROOT, render, sync


class MetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        shutil.copyfile(ROOT / "pyproject.toml", self.root / "pyproject.toml")
        shutil.copyfile(ROOT / "LICENSE", self.root / "LICENSE")
        self.version = self.root / "skills/astrofairy/scripts/astrofairy/_version.py"
        self.version.parent.mkdir(parents=True)
        self.manifest = self.root / ".claude-plugin/plugin.json"

    def source(self, value: Any) -> None:
        self.version.write_text(f"__version__ = {value!r}\n", encoding="utf-8")

    def test_version_change_is_detected_without_mutating_manifests(self) -> None:
        self.source("1.2.3rc4")
        sync(self.root, check=False)
        self.assertEqual(json.loads(self.manifest.read_bytes())["version"], "1.2.3-rc.4")
        original = self.manifest.read_bytes()
        self.source("1.2.3")
        self.assertIn(".claude-plugin/plugin.json", sync(self.root, check=True))
        self.assertEqual(self.manifest.read_bytes(), original)
        self.assertEqual(json.loads(render(self.root)[self.manifest])["version"], "1.2.3")

    def test_supported_versions_normalize_each_numeric_field_and_phase(self) -> None:
        pairs = [
            ("0.1.0a1", "0.1.0-alpha.1"),
            ("0.0.0", "0.0.0"),
            ("10.20.30", "10.20.30"),
            ("01.2.3", "1.2.3"),
            ("1.02.3", "1.2.3"),
            ("1.2.03", "1.2.3"),
            ("1.2.3a01", "1.2.3-alpha.1"),
            ("1.2.3a10", "1.2.3-alpha.10"),
            ("1.2.3b00", "1.2.3-beta.0"),
            ("1.2.3rc04", "1.2.3-rc.4"),
            ("1.2.3alpha", "1.2.3-alpha.0"),
            ("1.2.3BETA-02", "1.2.3-beta.2"),
            ("1.2.3preview4", "1.2.3-rc.4"),
            ("1.2.3.c4", "1.2.3-rc.4"),
            (" v1.2.3RC04 ", "1.2.3-rc.4"),
            ("0!1.2.3", "1.2.3"),
        ]
        for source, target in pairs:
            with self.subTest(source=source):
                self.source(source)
                actual = json.loads(render(self.root)[self.manifest])["version"]
                self.assertEqual(actual, target)
                self.assertTrue(actual.isascii())

    def test_rejection_leaves_present_or_absent_consumers_unchanged_in_both_modes(self) -> None:
        invalid = (
            "",
            "junk",
            "-1.2.3",
            "1.2",
            "1.2.3.0",
            "1!1.2.3",
            "1.2.3.post0",
            "1.2.3.dev0",
            "1.2.3+local",
            "1.2.3rc1.post2",
            "1.2.3a1.dev2",
            "\u0661.2.3",
            "1.2.3a\u0661",
            "\uff11.2.3",
            None,
            123,
            ["1.2.3"],
        )
        outputs = (
            self.manifest,
            self.root / ".claude-plugin/marketplace.json",
            self.root / "skills/astrofairy/LICENSE",
        )
        for existing in (False, True):
            for path in outputs:
                if path.exists():
                    path.unlink()
                if existing:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"Preserve exact fixture bytes")
            for value in invalid:
                for check in (False, True):
                    with self.subTest(value=value, check=check, existing=existing):
                        self.source(value)
                        before = {
                            path.relative_to(self.root): path.read_bytes()
                            for path in self.root.rglob("*")
                            if path.is_file()
                        }
                        with self.assertRaises(ValueError if isinstance(value, str) else TypeError):
                            sync(self.root, check=check)
                        after = {
                            path.relative_to(self.root): path.read_bytes()
                            for path in self.root.rglob("*")
                            if path.is_file()
                        }
                        self.assertEqual(after, before)

    def test_normalized_write_converges_without_rewriting_the_source_literal(self) -> None:
        self.source("01.02.03a04")
        original = self.version.read_bytes()
        self.assertEqual(len(sync(self.root, check=False)), 3)
        self.assertEqual(json.loads(self.manifest.read_bytes())["version"], "1.2.3-alpha.4")
        self.assertEqual(self.version.read_bytes(), original)
        self.assertEqual(sync(self.root, check=True), [])
        self.assertEqual(sync(self.root, check=False), [])
