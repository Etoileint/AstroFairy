# ruff: noqa: INP001 - Standalone handoff collector, not a runtime package.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import venv
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


class _Runs:
    def __init__(self, output: Path) -> None:
        self.output = output
        self.rows: list[dict[str, Any]] = []
        self.env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        self.env.update(PYTHONNOUSERSITE="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")

    def run(self, name: str, argv: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[bytes]:
        started = datetime.now(UTC).isoformat()
        sys.stdout.write(f"Running {name}\n")
        sys.stdout.flush()
        launch_error = None
        try:
            result = subprocess.run(argv, cwd=cwd, env=self.env, capture_output=True, check=False)
        except OSError as exc:
            launch_error = {"type": type(exc).__name__, "message": str(exc)}
            result = subprocess.CompletedProcess(argv, -1, b"", str(exc).encode("utf-8"))
        stdout = self.output / (name + ".stdout.txt")
        stderr = self.output / (name + ".stderr.txt")
        stdout.write_bytes(result.stdout)
        stderr.write_bytes(result.stderr)
        self.rows.append(
            {
                "name": name,
                "argv": argv,
                "cwd": str(cwd),
                "started": started,
                "ended": datetime.now(UTC).isoformat(),
                "exit": result.returncode,
                "launch_error": launch_error,
                "stdout": stdout.name,
                "stderr": stderr.name,
            }
        )
        return result


def _artifact_smoke(runs: _Runs, assignment: dict[str, Any], work: Path) -> None:
    for row in assignment["artifacts"]:
        artifact = ROOT / row["path"]
        kind = (
            "wheel" if artifact.suffix == ".whl" else "sdist" if artifact.name.endswith(".tar.gz") else "zip"
        )
        directory = work / kind
        directory.mkdir()
        prefix = directory / "venv"
        result = runs.run(kind + "-venv", [sys.executable, "-m", "venv", str(prefix)], directory)
        if result.returncode:
            continue
        python = str(venv.EnvBuilder().ensure_directories(prefix).env_exec_cmd)
        commands = [
            [
                python,
                "-m",
                "pip",
                "install",
                "--require-hashes",
                "--only-binary=:all:",
                "-r",
                str(ROOT / "skills/fairy/scripts/requirements-runtime.lock"),
            ],
            [
                python,
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                str(ROOT / "skills/fairy/scripts/wheels"),
                "--require-hashes",
                "-r",
                str(ROOT / "skills/fairy/scripts/requirements-delivery.lock"),
            ],
        ]
        if kind == "sdist":
            commands.append([python, "-m", "pip", "install", "-r", str(ROOT / "requirements-dev.lock")])
        launcher = None
        if kind == "zip":
            with zipfile.ZipFile(artifact) as archive:
                for member in archive.namelist():
                    path = PurePosixPath(member)
                    if path.is_absolute() or ".." in path.parts or "\\" in member or ":" in member:
                        raise ValueError("The assigned skill ZIP contains an unsafe path")
                archive.extractall(directory / "skill")
            launcher = directory / "skill/fairy/scripts/fairy.py"
        else:
            commands.append(
                [python, "-m", "pip", "install", "--no-deps", "--no-build-isolation", str(artifact)]
            )
        commands.append([python, "-m", "pip", "check"])
        failed = False
        for index, command in enumerate(commands):
            if runs.run(f"{kind}-install-{index}", command, directory).returncode:
                failed = True
                break
        if failed:
            continue
        if launcher is None:
            imported = runs.run(
                kind + "-module",
                [python, "-I", "-c", "import astrofairy; print(astrofairy.__file__)"],
                directory,
            )
            module = Path(imported.stdout.decode("utf-8").strip())
            if imported.returncode or not module.resolve().is_relative_to(prefix.resolve()):
                raise ValueError("Installed runtime was not imported from its new environment")
        command = [
            python,
            "-I",
            "-B",
            str(ROOT / "dev/smoke_task.py"),
            "--cwd",
            str(directory),
            "--home",
            str(directory / "state"),
            "--trace",
            str(runs.output / (kind + "-cli.json")),
        ]
        if launcher is not None:
            command += ["--launcher", str(launcher)]
        runs.run(kind + "-task", command, directory)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect a complete native validation return without editing source"
    )
    parser.add_argument(
        "--out", type=Path, required=True, help="New directory under this checkout's .evaluation"
    )
    args = parser.parse_args()
    output = args.out.resolve()
    archive_path = output.with_name(output.name + ".zip")
    sidecar_path = archive_path.with_name(archive_path.name + ".sha256")
    if (
        not output.is_relative_to(ROOT / ".evaluation")
        or output == ROOT / ".evaluation"
        or any(path.exists() for path in (output, archive_path, sidecar_path))
    ):
        parser.error("Use a new, dedicated directory inside .evaluation")
    output.mkdir(parents=True)
    runs = _Runs(output)
    assignment = json.loads((HERE / "assignment.json").read_text(encoding="utf-8"))
    environment = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version,
        "executable": sys.executable,
        "sqlite": sqlite3.sqlite_version,
        "candidate": assignment["candidate_commit"],
        "scope": "Observed platform only; no model inference or real-host adherence implied",
    }
    (output / "environment.json").write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
    programs = output / "programs"
    programs.mkdir()
    for program in [Path(__file__), HERE / "verify_candidate.py", ROOT / "dev/smoke_task.py"]:
        shutil.copy2(program, programs / program.name)
    failure = None
    try:
        before = runs.run("source-before", [sys.executable, "-B", str(HERE / "verify_candidate.py")])
        if before.returncode:
            raise ValueError("Source identity differs; validation was not started")
        runs.run("pip-check", [sys.executable, "-m", "pip", "check"])
        runs.run("canonical", [sys.executable, "-B", str(ROOT / "dev/check.py")])
        with tempfile.TemporaryDirectory(prefix="astrofairy-validation-") as temporary:
            work = Path(temporary)
            runs.run(
                "native-task",
                [
                    sys.executable,
                    "-I",
                    "-B",
                    str(ROOT / "dev/smoke_task.py"),
                    "--cwd",
                    str(work),
                    "--home",
                    str(work / "state"),
                    "--trace",
                    str(output / "native-cli.json"),
                ],
                work,
            )
            runs.run(
                "imports",
                [
                    sys.executable,
                    "-I",
                    "-c",
                    (
                        "import astrofairy,lancedb,fastembed,onnxruntime,tokenizers; "
                        "print(astrofairy.__file__, lancedb.__file__, fastembed.__file__, "
                        "onnxruntime.get_available_providers(), tokenizers.__file__)"
                    ),
                ],
                work,
            )
            _artifact_smoke(runs, assignment, work)
    except Exception as exc:  # noqa: BLE001 - retain a failed collector's original evidence for review.
        failure = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        runs.run("source-after", [sys.executable, "-B", str(HERE / "verify_candidate.py")])
    (output / "runs.json").write_text(json.dumps(runs.rows, indent=2) + "\n", encoding="utf-8")
    failed = failure is not None or any(row["exit"] for row in runs.rows)
    summary = {
        "state": "failed" if failed else "checks_passed",
        "collector_failure": failure,
        "candidate": assignment["candidate_commit"],
        "not_run": [
            "cold model download/interruption",
            "model-cache process concurrency",
            "real host",
            "full skills CLI matrix",
            "real E5 inference",
        ],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    rows = [
        {
            "path": p.relative_to(output).as_posix(),
            "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        }
        for p in sorted(output.rglob("*"))
        if p.is_file()
    ]
    (output / "evidence-inventory.json").write_text(
        json.dumps({"files": rows}, indent=2) + "\n", encoding="utf-8"
    )
    with zipfile.ZipFile(archive_path, "x", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(output).as_posix())
    checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    sidecar_path.write_text(checksum + "  " + archive_path.name + "\n", encoding="utf-8")
    sys.stdout.write(
        json.dumps(
            {
                "archive": str(archive_path),
                "bytes": archive_path.stat().st_size,
                "sha256": checksum,
                **summary,
            },
            indent=2,
        )
        + "\n"
    )
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
