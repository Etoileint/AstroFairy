from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from dev.package_skill import ROOT, package


class DistributionTests(unittest.TestCase):
    def test_source_skill_copy_runs_without_parent_checkout(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            folder = Path(temporary)
            skill = folder / "installed/astrofairy"
            shutil.copytree(
                ROOT / "skills/astrofairy", skill, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info")
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    str(skill / "scripts/fairy.py"),
                    "--home",
                    str(folder / "data"),
                    "start",
                    "--request",
                    "Use an installed skill",
                ],
                cwd=folder,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["action"], "produce")
            self.assertTrue((skill / "LICENSE").is_file())

    def test_packaged_skill_runs_without_checkout_or_installed_package(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            folder = Path(temporary)
            archive = package(folder / "dist")
            with zipfile.ZipFile(archive) as bundle:
                self.assertEqual(len(bundle.namelist()), len(set(bundle.namelist())))
                self.assertFalse(any("tests/" in name or "__pycache__" in name for name in bundle.namelist()))
                self.assertNotIn("astrofairy/package-manifest.json", bundle.namelist())
                for name in bundle.namelist():
                    relative = Path(name).relative_to("astrofairy")
                    self.assertEqual(bundle.read(name), (ROOT / "skills/astrofairy" / relative).read_bytes())
                bundle.extractall(folder / "unpacked")
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    str(folder / "unpacked/astrofairy/scripts/fairy.py"),
                    "--home",
                    str(folder / "state"),
                    "start",
                    "--request",
                    "A task from an installed skill",
                ],
                cwd=folder,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["action"], "produce")
