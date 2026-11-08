from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv
from pathlib import Path
from unittest.mock import patch

from dev.lock_dependencies import (
    ROOT,
    LockError,
    Pin,
    _active,
    _cross_profile_consistency,
    _dev_tool_pin,
    _environment_selections,
    _environments,
    _freeze_metadata,
    _input_digest,
    _metadata,
    _parse_lock,
    _profiles,
    _read_config,
    _run_update,
    _uv_command,
    _uv_executable,
    _uv_executable_digest,
    _verify_pin_artifacts,
    check,
)

COPIED = (
    "pyproject.toml",
    "requirements-dev.lock",
    "dev/dependency-profiles.toml",
    "dev/search-requirements.in",
    "dev/lock-provenance.json",
    "skills/fairy/scripts/requirements-runtime.lock",
    "skills/fairy/scripts/requirements-search.lock",
    "skills/fairy/scripts/astrofairy/_dependency_manifest.json",
)


def _tree(temporary: str) -> Path:
    root = Path(temporary)
    for name in COPIED:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    shutil.copytree(ROOT / "dev/runtime_snapshots", root / "dev/runtime_snapshots")
    shutil.copytree(ROOT / "dev/search_snapshots", root / "dev/search_snapshots")
    return root


class DependencyLockTests(unittest.TestCase):
    def test_committed_locks_and_diagnostics_match_official_snapshots(self) -> None:
        summary = check(ROOT)
        self.assertEqual(summary, {"profiles": {"core": 10, "search": 41}})
        search = (ROOT / "skills/fairy/scripts/requirements-search.lock").read_text(encoding="utf-8")
        self.assertIn("colorama==0.4.6 ; sys_platform == 'win32'", search)
        self.assertIn("win32-setctime==1.2.1 ; sys_platform == 'win32'", search)
        self.assertNotIn(" ; ", (ROOT / "skills/fairy/scripts/requirements-runtime.lock").read_text("utf-8"))
        diagnostics = json.loads(
            (ROOT / "skills/fairy/scripts/astrofairy/_dependency_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(diagnostics["format"], 2)
        windows = [
            item for item in diagnostics["profiles"]["search"]["requirements"] if item["name"] == "colorama"
        ]
        self.assertEqual(windows[0]["marker"], "sys_platform == 'win32'")
        self.assertEqual(diagnostics["recovery"]["search"], "assets prepare")

    def test_parser_preserves_conditional_branches_and_fails_closed(self) -> None:
        pins = _parse_lock("demo==1.0 ; sys_platform == 'win32' \\\n    --hash=sha256:" + "a" * 64 + "\n")
        self.assertEqual(pins[0].marker, "sys_platform == 'win32'")
        self.assertEqual(len(pins[0].hashes), 1)
        with self.assertRaisesRegex(LockError, "no hashes|Unsupported"):
            _parse_lock("-r other.txt\n")
        with self.assertRaisesRegex(LockError, "Unsupported"):
            _parse_lock("demo[extra]==1.0 \\\n    --hash=sha256:" + "a" * 64 + "\n")
        with self.assertRaisesRegex(LockError, "Duplicate hash"):
            _parse_lock(
                "demo==1.0 \\\n    --hash=sha256:" + "a" * 64 + " \\\n    --hash=sha256:" + "a" * 64 + "\n"
            )

    def test_marker_branches_select_windows_and_interpreter_conditions(self) -> None:
        config = json.loads(
            json.dumps(
                {
                    "policy": {
                        "python_versions": ["3.12", "3.13"],
                        "platforms": ["linux", "win32"],
                        "machines": {"linux": ["x86_64"], "win32": ["AMD64"]},
                    }
                }
            )
        )
        environments = _environments(config)
        windows = next(item for item in environments if item["sys_platform"] == "win32")
        linux = next(item for item in environments if item["sys_platform"] == "linux")
        pin = _parse_lock("demo==1.0 ; sys_platform == 'win32' \\\n    --hash=sha256:" + "a" * 64 + "\n")[0]
        self.assertTrue(_active(pin, windows))
        self.assertFalse(_active(pin, linux))

    def test_removing_a_conditional_dependency_is_refused(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            path = root / "skills/fairy/scripts/requirements-search.lock"
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
            kept = []
            skipping = False
            for line in lines:
                if line.startswith("colorama=="):
                    skipping = True
                    continue
                if skipping and line.startswith("    --hash="):
                    continue
                skipping = False
                kept.append(line)
            path.write_text("".join(kept), encoding="utf-8")
            with self.assertRaisesRegex(LockError, "colorama"):
                check(root)

    def test_snapshot_identity_and_policy_changes_are_refused(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            snapshot = root / "dev/search_snapshots/colorama-0.4.6.source"
            snapshot.write_bytes(snapshot.read_bytes() + b" ")
            with self.assertRaisesRegex(LockError, "snapshot bytes"):
                check(root)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            config = root / "dev/dependency-profiles.toml"
            config.write_text(
                config.read_text(encoding="utf-8").replace(
                    'index_url = "https://pypi.org/simple"', 'index_url = "https://example.invalid/simple"'
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(LockError, "policy"):
                check(root)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            roots = root / "dev/search-requirements.in"
            roots.write_text(
                roots.read_text(encoding="utf-8").replace("fastembed==0.9.1\n", ""), encoding="utf-8"
            )
            with self.assertRaisesRegex(LockError, "roots|fastembed"):
                check(root)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            tools = root / "requirements-dev.lock"
            tools.write_text(
                tools.read_text(encoding="utf-8").replace("uv==0.13.7", "uv==0.13.6"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(LockError, "resolver identity"):
                check(root)

    def test_unrelated_project_metadata_does_not_invalidate_the_lock(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            core = next(profile for profile in _profiles(_read_config(root)) if profile.name == "core")
            original = _input_digest(root, core)
            project = root / "pyproject.toml"
            project.write_text(
                project.read_text(encoding="utf-8").replace(
                    "Structured AI task delivery", "Structured task delivery"
                ),
                encoding="utf-8",
            )
            updated = _input_digest(root, core)
            self.assertEqual(original, updated)
            check(root)

    def test_legacy_snapshot_manifest_is_not_accepted_offline(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            path = root / "dev/runtime_snapshots/manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            legacy = {key.split("==")[0]: value for key, value in manifest["sources"].items()}
            path.write_text(json.dumps(legacy), encoding="utf-8")
            with self.assertRaisesRegex(LockError, "manifest format"):
                check(root)

    def test_wheel_only_artifacts_are_required(self) -> None:
        profile = next(item for item in _profiles(_read_config(ROOT)) if item.name == "core")
        pin = _parse_lock((ROOT / profile.lock).read_text(encoding="utf-8"))[0]
        metadata = _metadata(ROOT, profile, pin)
        sdist = next(
            item["digests"]["sha256"]
            for item in metadata["urls"]
            if item["packagetype"] == "sdist" and not item["yanked"]
        )
        with self.assertRaisesRegex(LockError, "not a wheel"):
            _verify_pin_artifacts(profile, Pin(pin.name, pin.version, None, (sdist,)), metadata)

    def test_tool_identity_probe_ignores_ambient_modules(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            shadow = Path(temporary)
            marker = shadow / "undeclared-module-executed"
            (shadow / "uv.py").write_text(
                "from pathlib import Path\n"
                f"Path({str(marker)!r}).write_text('host module ran')\n"
                "print('uv 0.13.7')\n",
                encoding="utf-8",
            )
            previous = Path.cwd()
            os.chdir(shadow)
            try:
                with patch.dict(os.environ, {"PYTHONPATH": str(shadow)}):
                    command = _uv_command(ROOT)
            finally:
                os.chdir(previous)
            self.assertFalse(marker.exists())
            self.assertEqual(command[:2], [sys.executable, "-I"])
            self.assertIn("-m", command)

    def test_tool_digest_follows_upstream_resolution_in_an_isolated_venv(self) -> None:
        import uv  # noqa: PLC0415 - only the selected interpreter's package identifies the binary.

        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            prefix = Path(temporary) / "toolenv"
            builder = venv.EnvBuilder(with_pip=False)
            builder.create(prefix)
            python = Path(builder.ensure_directories(prefix).env_exec_cmd)
            purelib = Path(
                subprocess.check_output(
                    [str(python), "-I", "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
                    text=True,
                    encoding="utf-8",
                ).strip()
            )
            shutil.copytree(Path(uv.__file__).parent, purelib / "uv")
            (purelib / "bin").mkdir()
            binary = Path(uv.find_uv_bin())
            shutil.copy2(binary, purelib / "bin" / binary.name)
            with patch.object(sys, "executable", str(python)):
                command = _uv_command(ROOT)
                executable = _uv_executable(command)
                digest = _uv_executable_digest(command)
            actual = subprocess.run(
                [str(python), "-I", "-c", "import uv; print(uv.find_uv_bin())"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            self.assertEqual(executable, Path(actual))
            self.assertNotEqual(executable, python.with_name(binary.name))
            self.assertEqual(digest, hashlib.sha256(Path(actual).read_bytes()).hexdigest())
            version = subprocess.run(
                [*command, "--version"], capture_output=True, text=True, check=True
            ).stdout.split()
            policy = _read_config(ROOT)["policy"]
            self.assertEqual(version[1], _dev_tool_pin(ROOT, policy["uv_pin_name"], policy["uv_pin_file"]))

    def test_check_rejects_a_missing_recorded_tool_digest(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            check(root)
            path = root / "dev/lock-provenance.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["tool"]["sha256"] = None
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(LockError, "executable digest is missing or malformed"):
                check(root)

    def test_update_refuses_to_bless_existing_source_drift(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            profile = next(item for item in _profiles(_read_config(root)) if item.name == "core")
            path = root / profile.snapshots / "manifest.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            key = next(iter(data["sources"]))
            data["sources"][key]["retrieved_at"] = "2099-01-01T00:00:00+00:00"
            path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
            with (
                patch("dev.lock_dependencies.urlopen", side_effect=AssertionError("network forbidden")),
                self.assertRaisesRegex(LockError, "differs from its recorded update"),
            ):
                _run_update(root, profile, ["uv"], root / "cache")
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            profile = next(item for item in _profiles(_read_config(root)) if item.name == "core")
            path = root / profile.snapshots / "manifest.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["sources"]["not-a-package==0"] = {
                "url": "https://example.invalid/not-approved",
                "sha256": "0" * 64,
                "retrieved_at": "now",
            }
            path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
            with self.assertRaisesRegex(LockError, "official PyPI"):
                _run_update(root, profile, ["uv"], root / "cache")

    def test_partial_profile_overlap_still_compares_involved_profiles(self) -> None:
        environments = _environments(_read_config(ROOT))
        conflicting = {
            "core": [{"shared": "1.0"} for _ in environments],
            "search": [{"shared": "2.0"} for _ in environments],
            "independent": [{"other": "1.0"} for _ in environments],
        }
        with self.assertRaisesRegex(LockError, "different versions"):
            _cross_profile_consistency(conflicting, environments)
        pins = _parse_lock(
            "demo==1.0 ; sys_platform != 'win32' \\\n    --hash=sha256:"
            + "a" * 64
            + "\ndemo==2.0 ; sys_platform == 'win32' \\\n    --hash=sha256:"
            + "b" * 64
            + "\n"
        )
        forks = {
            name: _environment_selections(pins, environments, profile=name) for name in ("core", "search")
        }
        forks["independent"] = [{"other": "1.0"} for _ in environments]
        _cross_profile_consistency(forks, environments)

    def test_identical_environment_forks_are_accepted_per_cell(self) -> None:
        environments = _environments(_read_config(ROOT))
        pins = _parse_lock(
            "demo==1.0 ; sys_platform != 'win32' \\\n    --hash=sha256:"
            + "a" * 64
            + "\ndemo==2.0 ; sys_platform == 'win32' \\\n    --hash=sha256:"
            + "b" * 64
            + "\n"
        )
        selections = {
            name: _environment_selections(pins, environments, profile=name) for name in ("core", "search")
        }
        _cross_profile_consistency(selections, environments)
        conflict = {name: [dict(item) for item in value] for name, value in selections.items()}
        conflict["search"][0]["demo"] = "9.9"
        with self.assertRaisesRegex(LockError, "different versions"):
            _cross_profile_consistency(conflict, environments)

    def test_marker_environment_is_complete_and_host_independent(self) -> None:
        from packaging.markers import default_environment  # noqa: PLC0415

        environments = _environments(_read_config(ROOT))
        self.assertLessEqual(set(default_environment()), set(environments[0]))
        pin = Pin(
            "demo",
            "1.0",
            'platform_release == "6.0.0-review" and platform_version == "#1 SMP review-linux"',
            ("a" * 64,),
        )
        linux = next(item for item in environments if item["sys_platform"] == "linux")
        host = {**default_environment(), "platform_release": "other", "platform_version": "other"}
        with patch("packaging.markers.default_environment", return_value=host):
            first = _active(pin, linux)
        with patch("packaging.markers.default_environment", return_value=default_environment()):
            second = _active(pin, linux)
        self.assertEqual(first, second)
        with self.assertRaisesRegex(LockError, "cannot express"):
            _parse_lock('demo==1.0 ; platform_release == "5.15" \\\n    --hash=sha256:' + "a" * 64 + "\n")

    def test_ambient_environment_cannot_reach_the_resolver(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            profile = next(item for item in _profiles(_read_config(root)) if item.name == "core")
            lines = (root / profile.lock).read_text(encoding="utf-8").splitlines(keepends=True)
            start = next(index for index, line in enumerate(lines) if line and not line.startswith("#"))
            body = "".join(lines[start:])
            completed = __import__("subprocess").CompletedProcess([], 0, stdout=body, stderr="")
            polluted = {
                "UV_CONSTRAINT": str(root / "missing-constraints.txt"),
                "UV_OFFLINE": "true",
                "PIP_INDEX_URL": "https://example.invalid/simple",
                "CONDA_PREFIX": str(root / "conda"),
                "PYTHONPATH": str(root / "shadow"),
            }
            with (
                patch.dict(os.environ, polluted),
                patch("dev.lock_dependencies.subprocess.run", return_value=completed) as invoked,
            ):
                updated = _run_update(root, profile, ["uv"], root / "cache")
            environment = invoked.call_args.kwargs["env"]
            self.assertFalse(
                [
                    key
                    for key in environment
                    if key.startswith(("UV_", "PIP_", "CONDA_", "PYTHON", "VIRTUAL_ENV"))
                ]
            )
            self.assertIn("PATH", environment)
            self.assertEqual(updated["lock"], (root / profile.lock).read_bytes())

    def test_source_url_identity_and_manifest_binding_are_checked(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            path = root / "dev/search_snapshots/manifest.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["sources"]["colorama==0.4.6"]["url"] = "https://example.invalid/pypi/colorama/0.4.6/json"
            path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
            with self.assertRaisesRegex(LockError, "official PyPI"):
                check(root)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            path = root / "dev/search_snapshots/manifest.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["sources"]["colorama==0.4.6"]["retrieved_at"] = "2026-11-08T00:00:00+00:00"
            path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
            with self.assertRaisesRegex(LockError, "snapshot manifest bytes"):
                check(root)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            path = root / "dev/search_snapshots/manifest.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["sources"]["colorama==0.4.6"]["url"] = "https://pypi.org/pypi/colorama/0.4.5/json"
            path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
            with self.assertRaisesRegex(LockError, "identity"):
                check(root)

    def test_legacy_manifest_is_rejected_by_update_and_check(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = _tree(temporary)
            profile = next(item for item in _profiles(_read_config(root)) if item.name == "core")
            path = root / profile.snapshots / "manifest.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            legacy = {key.split("==")[0]: value for key, value in data["sources"].items()}
            path.write_text(json.dumps(legacy), encoding="utf-8")
            pins = _parse_lock((root / profile.lock).read_text(encoding="utf-8"))
            with (
                patch("dev.lock_dependencies.urlopen", side_effect=AssertionError("network forbidden")),
                self.assertRaisesRegex(LockError, "manifest format"),
            ):
                _freeze_metadata(root, profile, pins)
            with self.assertRaisesRegex(LockError, "manifest format"):
                check(root)
