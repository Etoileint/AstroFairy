from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dev import check_model_profile as model_check
from dev.check_model_profile import ROOT, validate


def _tree(temporary: str) -> Path:
    root = Path(temporary)
    shutil.copytree(ROOT / "dev/model_profiles", root / "dev/model_profiles")
    shutil.copytree(ROOT / "dev/search_snapshots", root / "dev/search_snapshots")
    lock = root / "skills/fairy/scripts/requirements-search.lock"
    lock.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "skills/fairy/scripts/requirements-search.lock", lock)
    return root


class ModelProfileTests(unittest.TestCase):
    def test_committed_consumer_audit_is_identity_bound(self) -> None:
        result = validate()
        self.assertEqual(result["files"], 6)
        self.assertEqual(result["consumer"], "fastembed==0.9.1")
        manifest = json.loads(
            (ROOT / "dev/model_profiles/fastembed-0.9.1/consumer_manifest.json").read_text(encoding="utf-8")
        )
        self.assertTrue(manifest["wheel_sha256"].startswith(str(result["consumer_wheel"])))

    def test_zero_wheel_identity_is_refused(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            profile = root / "dev/model_profiles/multilingual-e5-large.json"
            data = json.loads(profile.read_text(encoding="utf-8"))
            data["consumer_audit"]["wheel_sha256"] = "0" * 64
            profile.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "consumer identity"):
                validate(root)

    def test_consumer_source_change_requires_reaudit(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            source = root / "dev/model_profiles/fastembed-0.9.1/fastembed/common/preprocessor_utils.py"
            source.write_bytes(source.read_bytes() + b"\n# changed\n")
            with self.assertRaisesRegex(ValueError, "changed without re-audit"):
                validate(root)

    def test_consumer_manifest_must_match_committed_sources(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            path = root / "dev/model_profiles/fastembed-0.9.1/consumer_manifest.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["consumed_files"].pop("config.json")
            data["sources"]["fastembed/common/preprocessor_utils.py"]["consumes"].remove("config.json")
            path.write_text(json.dumps(data), encoding="utf-8")
            profile = root / "dev/model_profiles/multilingual-e5-large.json"
            declared = json.loads(profile.read_text(encoding="utf-8"))
            declared["files"].pop("config.json")
            profile.write_text(json.dumps(declared), encoding="utf-8")
            files = {name: value for name, value in model_check.MODEL_FILES.items() if name != "config.json"}
            sizes = {
                name: value for name, value in model_check.MODEL_FILE_SIZES.items() if name != "config.json"
            }
            runtime = json.loads(json.dumps(model_check.PROFILE))
            runtime["embedding"]["files"] = files
            with (
                patch.object(model_check, "MODEL_FILES", files),
                patch.object(model_check, "MODEL_FILE_SIZES", sizes),
                patch.object(model_check, "PROFILE", runtime),
                self.assertRaisesRegex(ValueError, "declaration disagrees|consumed file set"),
            ):
                validate(root)

    def test_synchronized_omission_is_not_proof(self) -> None:
        # The fixed consumer source still reads config.json even when every
        # mutable declaration removes it; the gate must remain red.
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        files = {name: value for name, value in model_check.MODEL_FILES.items() if name != "config.json"}
        sizes = {name: value for name, value in model_check.MODEL_FILE_SIZES.items() if name != "config.json"}
        profile = json.loads(json.dumps(model_check.PROFILE))
        profile["embedding"]["files"] = files
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            manifest_path = root / "dev/model_profiles/multilingual-e5-large.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"].pop("config.json")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with (
                patch.object(model_check, "MODEL_FILES", files),
                patch.object(model_check, "MODEL_FILE_SIZES", sizes),
                patch.object(model_check, "PROFILE", profile),
                self.assertRaisesRegex(ValueError, "consumed file set"),
            ):
                validate(root)

    def test_locked_version_change_reopens_the_audit(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            lock = root / "skills/fairy/scripts/requirements-search.lock"
            lock.write_text(
                lock.read_text(encoding="utf-8").replace("fastembed==0.9.1", "fastembed==0.9.2"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "fastembed differs"):
                validate(root)


if __name__ == "__main__":
    unittest.main()
