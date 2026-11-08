from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _run(
    home: Path,
    *arguments: str,
    data: dict[str, Any] | None = None,
    directory: Path = ROOT,
    launcher: Path | None = None,
    trace: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    prefix = [sys.executable, "-I", "-B"]
    prefix += [str(launcher)] if launcher is not None else ["-m", "astrofairy"]
    command = [*prefix, "--home", str(home), *arguments]
    started = datetime.now(UTC).isoformat()
    launch_error = None
    try:
        completed = subprocess.run(
            command,
            cwd=directory,
            input=None if data is None else json.dumps(data).encode("utf-8"),
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        launch_error = {"type": type(exc).__name__, "message": str(exc)}
        completed = subprocess.CompletedProcess(command, -1, b"", str(exc).encode("utf-8"))
    if trace is not None:
        trace.append(
            {
                "argv": command,
                "cwd": str(directory),
                "started": started,
                "ended": datetime.now(UTC).isoformat(),
                "exit": completed.returncode,
                "launch_error": launch_error,
                "stdin_json": data,
                "stdout_base64": base64.b64encode(completed.stdout).decode("ascii"),
                "stderr_base64": base64.b64encode(completed.stderr).decode("ascii"),
            }
        )
    try:
        result = json.loads(completed.stdout)
    except ValueError as exc:
        raise RuntimeError(f"{arguments[0]} returned invalid JSON: {completed.stdout!r}") from exc
    if completed.returncode != 0:
        raise RuntimeError(f"{arguments[0]} failed: {result}")
    return result


def smoke(
    home: Path,
    *,
    directory: Path = ROOT,
    launcher: Path | None = None,
    trace: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    def run(*arguments: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        return _run(home, *arguments, data=data, directory=directory, launcher=launcher, trace=trace)

    existed = home.exists()
    doctor = run("doctor")
    if not existed and home.exists():
        raise RuntimeError("doctor created the task home")
    if not doctor.get("ready"):
        raise RuntimeError(f"doctor is not ready: {doctor}")
    spec = {
        "criteria": [
            {
                "id": "usable",
                "description": "The delivered member is nonempty",
                "checker": "nonempty",
                "scope": "collection",
            }
        ]
    }
    started = run(
        "start",
        "--request",
        "Deliver one checked member",
        "--spec",
        "-",
        data=spec,
    )
    task = started["task"]
    request = run(
        "submit",
        task,
        data={"op": "request", "purpose": "Produce the member"},
    )
    report = run(
        "submit",
        task,
        data={
            "op": "report",
            "call": request["call"],
            "text": "Actual delivered bytes",
            "path": "result.txt",
            "media_type": "text/plain",
        },
    )
    run(
        "submit",
        task,
        data={
            "op": "publish",
            "members": [
                {
                    "ref": report["ref"],
                    "path": report["path"],
                    "bytes": report["bytes"],
                    "media_type": report["media_type"],
                    "role": "main",
                }
            ],
        },
    )
    checked = run("submit", task, data={"op": "check"})
    verdicts = [item["result"].get("verdict") for item in checked["checks"]]
    if verdicts != ["pass"]:
        raise RuntimeError(f"mechanical check did not pass: {checked}")
    closed = run("submit", task, data={"op": "close", "outcome": "complete"})
    delivery = closed.get("delivery", {})
    if delivery.get("state") != "validated":
        raise RuntimeError(f"close did not validate the export: {closed}")
    import bagit  # type: ignore[import-untyped]  # noqa: PLC0415 - native smoke verification.

    if not bagit.Bag(delivery["bag_path"]).validate():
        raise RuntimeError("the native BagIt export did not pass upstream validation")
    packet = run("next", task)
    if packet["action"] != "verify_delivery":
        raise RuntimeError(f"closed task did not expose the delivery observation: {packet['action']}")
    return {
        "task": task,
        "state": delivery["state"],
        "seq": delivery["seq"],
        "files": sorted(delivery["files"]),
        "bag": delivery["bag_path"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="smoke_task")
    parser.add_argument("--home", type=Path)
    parser.add_argument("--cwd", type=Path, default=ROOT)
    parser.add_argument("--launcher", type=Path)
    parser.add_argument("--trace", type=Path)
    arguments = parser.parse_args(argv)
    directory = arguments.cwd / ".test-runs"
    directory.mkdir(exist_ok=True)
    trace: list[dict[str, Any]] = []
    try:
        if arguments.home is not None:
            result = smoke(arguments.home, directory=arguments.cwd, launcher=arguments.launcher, trace=trace)
        else:
            with tempfile.TemporaryDirectory(dir=directory) as temporary:
                result = smoke(
                    Path(temporary) / "state",
                    directory=arguments.cwd,
                    launcher=arguments.launcher,
                    trace=trace,
                )
    finally:
        if arguments.trace is not None:
            arguments.trace.parent.mkdir(parents=True, exist_ok=True)
            arguments.trace.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
    print("Native task smoke passed:", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
