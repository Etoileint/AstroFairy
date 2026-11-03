from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from astrofairy import Workshop
from astrofairy._maintenance import audit_state, backup_state, restore_state


def _produce(workshop: Workshop, task: str, text: str, path: str) -> dict[str, Any]:
    call = workshop.submit(task, {"op": "request", "purpose": f"Produce {path}"})
    return workshop.submit(task, {"op": "report", "call": call["call"], "text": text, "path": path})


def _member(output: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "ref": output["ref"],
        "path": output["path"],
        "bytes": output["bytes"],
        "media_type": output["media_type"],
        "role": role,
    }


def _complete(workshop: Workshop, task: str) -> dict[str, Any]:
    workshop.submit(task, {"op": "check"})
    workshop.submit(
        task,
        {
            "op": "review",
            "criterion": "goal",
            "verdict": "pass",
            "basis": "Recovery fixture content satisfies the stated task",
        },
    )
    return workshop.submit(task, {"op": "close", "outcome": "complete"})


def _build(source: Path) -> dict[str, Any]:
    workshop = Workshop(source)
    first = workshop.start(
        "Keep two historical snapshots",
        spec={
            "criteria": [
                {"id": "goal", "description": "Relevant", "checker": "semantic"},
                {"id": "usable", "description": "Nonempty", "checker": "nonempty", "scope": "collection"},
            ],
            "required_roles": ["report"],
        },
    )
    one = _produce(workshop, first, "First version", "report.md")
    workshop.submit(first, {"op": "publish", "members": [_member(one, "report")]})
    two = _produce(workshop, first, "Second version", "report.md")
    data = _produce(workshop, first, "a,1\nb,2\n", "data/table.csv")
    workshop.submit(first, {"op": "publish", "members": [_member(two, "report"), _member(data, "data")]})
    first_delivery = _complete(workshop, first)

    second = workshop.start(
        "Keep a nested delivery",
        spec={
            "criteria": [
                {"id": "goal", "description": "Relevant", "checker": "semantic"},
                {"id": "usable", "description": "Nonempty", "checker": "nonempty", "scope": "collection"},
            ],
            "required_roles": ["report"],
        },
    )
    nested = _produce(workshop, second, "Nested notes", "notes/summary.md")
    workshop.submit(second, {"op": "publish", "members": [_member(nested, "report")]})
    second_delivery = _complete(workshop, second)

    asset_package = {
        "name": "recovery-guide",
        "scope": "personal",
        "kind": "guide",
        "summary": "Recovery fixture guide",
        "tags": ["recovery"],
        "content": "Keep captured bytes and historical snapshots.",
        "evidence": [{"source": f"task:{first}", "note": "Recovery fixture"}],
    }
    asset = workshop.library.propose(asset_package)
    validation = workshop.validation_task(asset)
    workshop.submit(validation, {"op": "check"})
    workshop.submit(
        validation,
        {
            "op": "review",
            "criterion": "asset-fitness",
            "verdict": "pass",
            "basis": "Recovery fixture validated through the real adoption policy",
        },
    )
    workshop.submit(validation, {"op": "close", "outcome": "complete"})
    workshop.library.adopt(asset, validation, "stable")
    validation_delivery = workshop.deliver(validation)
    expected = {
        first: {
            "snapshots": [item["ref"] for item in workshop.state(first).snapshots],
            "files": {name: Path(path).read_bytes() for name, path in first_delivery["files"].items()},
        },
        second: {
            "snapshots": [item["ref"] for item in workshop.state(second).snapshots],
            "files": {name: Path(path).read_bytes() for name, path in second_delivery["files"].items()},
        },
        validation: {
            "snapshots": [item["ref"] for item in workshop.state(validation).snapshots],
            "files": {name: Path(path).read_bytes() for name, path in validation_delivery["files"].items()},
        },
    }
    result = {
        "tasks": [first, second, validation],
        "snapshots": [
            workshop.state(first).snapshots,
            workshop.state(second).snapshots,
            workshop.state(validation).snapshots,
        ],
        "deliveries": [first_delivery, second_delivery, validation_delivery],
        "asset": asset,
        "asset_status": workshop.library.status(asset),
        "expected": expected,
    }
    workshop.store.close()
    return result


def _verify(
    source: Path, backup: Path, restored: Path, expected: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    before = audit_state(source)
    backup_result = backup_state(source, backup)
    restored_result = restore_state(backup, restored)
    after = audit_state(restored)
    workshop = Workshop(restored)
    checked = []
    try:
        for task in _task_ids(workshop):
            state = workshop.state(task)
            delivery = workshop.deliver(task)
            files = {name: Path(path).read_bytes() for name, path in delivery["files"].items()}
            target = expected[task]
            if [snapshot["ref"] for snapshot in state.snapshots] != target["snapshots"]:
                raise RuntimeError(f"Snapshot identity changed after restore: {task}")
            if files != target["files"]:
                raise RuntimeError(f"Delivered bytes changed after restore: {task}")
            checked.append(
                {
                    "task": task,
                    "snapshots": target["snapshots"],
                    "delivery_seq": delivery["seq"],
                    "files": sorted(files),
                    "bytes": {name: len(data) for name, data in sorted(files.items())},
                }
            )
        return {
            "before": before,
            "backup": backup_result,
            "restored": restored_result,
            "after": after,
            "tasks": checked,
            "asset_status": workshop.library.status(_asset_ref(workshop)),
        }
    finally:
        workshop.store.close()


def _task_ids(workshop: Workshop) -> list[str]:
    rows = workshop.store.connection.execute("SELECT DISTINCT task FROM events ORDER BY task").fetchall()
    return [str(row[0]) for row in rows]


def _asset_ref(workshop: Workshop) -> str:
    row = workshop.store.connection.execute(
        "SELECT ref FROM assets WHERE name = 'recovery-guide' ORDER BY rowid DESC LIMIT 1"
    ).fetchone()
    if row is None:
        raise RuntimeError("Recovery asset is absent")
    return str(row[0])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Back up and restore all retained snapshots and an asset")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(".evaluation/optimization-implementation/recovery-w07"),
    )
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    root = arguments.root
    root.mkdir(parents=True, exist_ok=True)
    source = root / "source"
    backup = root / "backup"
    restored = root / "restored"
    for path in (source, backup, restored):
        if path.exists():
            shutil.rmtree(path)
    built = _build(source)
    result = {
        "format": 1,
        "source": str(source),
        "original": {key: built[key] for key in ("tasks", "asset", "asset_status")},
        "snapshot_counts": [len(item) for item in built["snapshots"]],
        "verified": _verify(source, backup, restored, built["expected"]),
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
