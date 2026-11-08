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
    def test_sdist_retains_locked_inputs_and_rebuilds_identical_skill(self) -> None:
        from dev.check_vendor import validate  # noqa: PLC0415 - compares original and extracted authority.

        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            folder = Path(temporary)
            built = subprocess.run(
                [sys.executable, "-B", "-m", "build", "--sdist", "--no-isolation", "--outdir", str(folder)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            shutil.unpack_archive(next(folder.glob("astrofairy-*.tar.gz")), folder / "source", filter="data")
            source = next((folder / "source").iterdir())
            probe = (
                "import runpy,sys; from pathlib import Path; root=Path(sys.argv[1]); "
                "vendor=runpy.run_path(str(root/'dev/check_vendor.py'))['validate'](); "
                "lock=runpy.run_path(str(root/'dev/lock_dependencies.py'))['check'](root); "
                "print(vendor); print(lock); "
                "runpy.run_path(str(root/'dev/package_skill.py'))['package'](root/'dist')"
            )
            checked = subprocess.run(
                [sys.executable, "-I", "-c", probe, str(source)],
                cwd=folder,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertIn(str(validate()["wheel_sha256"]), checked.stdout)
            self.assertIn("'core': 10", checked.stdout)
            self.assertIn("'search': 41", checked.stdout)
            self.assertEqual(
                (ROOT / "skills/fairy/scripts/requirements-search.lock").read_text(encoding="utf-8"),
                (source / "skills/fairy/scripts/requirements-search.lock").read_text(encoding="utf-8"),
            )
            self.assertTrue((source / "dev/dependency-profiles.toml").is_file())
            original = package(folder / "original")
            with zipfile.ZipFile(original) as expected, zipfile.ZipFile(source / "dist/fairy.zip") as rebuilt:
                self.assertEqual(rebuilt.namelist(), expected.namelist())
                for name in expected.namelist():
                    self.assertEqual(rebuilt.read(name), expected.read(name), name)

    def test_source_skill_copy_runs_without_parent_checkout(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            folder = Path(temporary)
            skill = folder / "installed/fairy"
            shutil.copytree(
                ROOT / "skills/fairy", skill, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info")
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
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
            self.assertEqual(json.loads(result.stdout)["action"], "refine")
            self.assertTrue((skill / "LICENSE").is_file())

    def test_packaged_skill_uses_prepared_runtime_outside_checkout(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            folder = Path(temporary)
            archive = package(folder / "dist")
            with zipfile.ZipFile(archive) as bundle:
                self.assertEqual(len(bundle.namelist()), len(set(bundle.namelist())))
                self.assertFalse(any("tests/" in name or "__pycache__" in name for name in bundle.namelist()))
                self.assertIn("fairy/references/operation.md", bundle.namelist())
                self.assertNotIn("fairy/package-manifest.json", bundle.namelist())
                for name in bundle.namelist():
                    relative = Path(name).relative_to("fairy")
                    self.assertEqual(bundle.read(name), (ROOT / "skills/fairy" / relative).read_bytes())
                bundle.extractall(folder / "unpacked")
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(folder / "unpacked/fairy/scripts/fairy.py"),
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
            self.assertEqual(json.loads(result.stdout)["action"], "refine")
