from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _run(home: Path, *arguments: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-B", "-m", "astrofairy", "--home", str(home), *arguments],
        cwd=ROOT,
        input=None if data is None else json.dumps(data),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    try:
        result = json.loads(completed.stdout)
    except ValueError as exc:
        raise RuntimeError(f"{arguments[0]} returned invalid JSON: {completed.stdout!r}") from exc
    if completed.returncode != 0:
        raise RuntimeError(f"{arguments[0]} failed: {result}")
    return result


def smoke(home: Path) -> dict[str, Any]:
    doctor = _run(home, "doctor")
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
    started = _run(
        home,
        "start",
        "--request",
        "Deliver one checked member",
        "--spec",
        "-",
        data=spec,
    )
    task = started["task"]
    request = _run(
        home,
        "submit",
        task,
        data={"op": "request", "purpose": "Produce the member"},
    )
    report = _run(
        home,
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
    _run(
        home,
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
    checked = _run(home, "submit", task, data={"op": "check"})
    verdicts = [item["result"].get("verdict") for item in checked["checks"]]
    if verdicts != ["pass"]:
        raise RuntimeError(f"mechanical check did not pass: {checked}")
    closed = _run(home, "submit", task, data={"op": "close", "outcome": "complete"})
    delivery = closed.get("delivery", {})
    if delivery.get("state") != "validated":
        raise RuntimeError(f"close did not validate the export: {closed}")
    import bagit  # type: ignore[import-untyped]  # noqa: PLC0415 - native smoke verification.

    if not bagit.Bag(delivery["bag_path"]).validate():
        raise RuntimeError("the native BagIt export did not pass upstream validation")
    packet = _run(home, "next", task)
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
    arguments = parser.parse_args(argv)
    directory = ROOT / ".test-runs"
    directory.mkdir(exist_ok=True)
    if arguments.home is not None:
        result = smoke(arguments.home)
    else:
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            result = smoke(Path(temporary) / "state")
    print("Native task smoke passed:", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
