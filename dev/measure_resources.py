from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from astrofairy import FairyError, Workshop
from astrofairy._contracts import SchemaContract, canonical
from astrofairy._limits import LIMITS
from astrofairy._maintenance import backup_state

MiB = 1024 * 1024


def _file(path: Path, size: int, seed: int = 0) -> None:
    chunk = bytes(range(32)) * (MiB // 32)
    if seed:
        chunk = chunk[: seed % len(chunk)] + b"\xff" + chunk[seed % len(chunk) + 1 :]
    with path.open("wb") as stream:
        remaining = size
        while remaining:
            part = min(remaining, len(chunk))
            stream.write(chunk[:part])
            remaining -= part


def _peak_kb() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def _database_bytes(home: Path) -> int:
    paths = (home / "workshop.sqlite3", home / "documents.sqlite3")
    return sum(item.stat().st_size for item in paths if item.is_file())


def _result(elapsed_seconds: float, home: Path, **extra: Any) -> dict[str, Any]:
    return {
        "elapsed_seconds": round(elapsed_seconds, 3),
        "peak_rss_kb": _peak_kb(),
        "database_bytes": _database_bytes(home),
        **extra,
    }


def _capture(root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        home = Path(temporary) / "state"
        size = int(os.environ["FAIRY_MEASURE_BYTES"])
        with Workshop(home) as workshop:
            task = workshop.start("Measure one streamed capture")
            workspace = Path(workshop.next(task)["workspace"])
            _file(workspace / "payload.bin", size)
            started = time.perf_counter()
            observed = workshop.invoke(task, "file.capture", {"path": "payload.bin"})
            elapsed = time.perf_counter() - started
            if observed["status"] != "ok":
                raise RuntimeError(observed)
            return _result(
                elapsed,
                home,
                requested_bytes=size,
                captured_bytes=observed["outputs"][0]["bytes"],
            )


def _aggregate(root: Path) -> dict[str, Any]:
    sizes = [32 * MiB, 128 * MiB, 256 * MiB]
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        home = Path(temporary) / "state"
        with Workshop(home) as workshop:
            task = workshop.start("Measure aggregate streamed capture")
            workspace = Path(workshop.next(task)["workspace"])
            timings = []
            total = 0
            for index, size in enumerate(sizes):
                source = workspace / f"payload-{index}.bin"
                _file(source, size)
                started = time.perf_counter()
                observed = workshop.invoke(task, "file.capture", {"path": source.name})
                elapsed = time.perf_counter() - started
                if observed["status"] != "ok":
                    raise RuntimeError(observed)
                total += observed["outputs"][0]["bytes"]
                timings.append({"bytes": size, "capture_seconds": round(elapsed, 3)})
            resource_status = workshop.next(task)["resources"]
            return _result(
                sum(item["capture_seconds"] for item in timings),
                home,
                files=timings,
                captured_bytes=total,
                used_calls=resource_status["used_calls"],
                free_calls=resource_status["free_calls"],
            )


def _full_aggregate(root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        home = Path(temporary) / "state"
        with Workshop(home) as workshop:
            task = workshop.start("Measure the full task aggregate boundary")
            workspace = Path(workshop.next(task)["workspace"])
            timings = []
            total = 0
            for index in range(8):
                source = workspace / f"payload-{index}.bin"
                _file(source, 256 * MiB, index + 1)
                started = time.perf_counter()
                observed = workshop.invoke(task, "file.capture", {"path": source.name})
                elapsed = time.perf_counter() - started
                if observed["status"] != "ok":
                    raise RuntimeError(observed)
                total += observed["outputs"][0]["bytes"]
                timings.append({"bytes": 256 * MiB, "capture_seconds": round(elapsed, 3)})
            over = workspace / "one-byte-over.bin"
            over.write_bytes(b"z")
            rejected = workshop.invoke(task, "file.capture", {"path": over.name})
            return _result(
                sum(item["capture_seconds"] for item in timings),
                home,
                files=timings,
                captured_bytes=total,
                aggregate_limit_bytes=LIMITS.task_capture_bytes,
                over_limit={"status": rejected["status"], "error": rejected["result"].get("error")},
            )


def _normal_calls(root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        home = Path(temporary) / "state"
        with Workshop(home) as workshop:
            task = workshop.start("Measure ordinary repeated work and free reads")
            started = time.perf_counter()
            first = workshop.invoke(task, "text.write", {"path": "note-0.md", "text": "note"})
            for index in range(1, 24):
                observed = workshop.invoke(task, "text.write", {"path": f"note-{index}.md", "text": "note"})
                if observed["status"] != "ok":
                    raise RuntimeError(observed)
            for index in range(40):
                observed = workshop.invoke(
                    task,
                    "content.read",
                    {"ref": first["outputs"][0]["ref"], "offset": index, "limit": 1},
                )
                if observed["status"] != "ok":
                    raise RuntimeError(observed)
            elapsed = time.perf_counter() - started
            status = workshop.next(task)["resources"]
            return _result(
                elapsed,
                home,
                counted_work_calls=status["used_calls"],
                free_context_reads=status["free_calls"],
                warning=status["warning"],
            )


def _schema(root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        home = Path(temporary) / "state"
        base = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
        }
        started = time.perf_counter()
        accepted = SchemaContract({**base, "description": "x" * (LIMITS.schema_bytes - 4096)})
        accepted_bytes = len(canonical(accepted.schema))
        elapsed = time.perf_counter() - started
        started = time.perf_counter()
        try:
            SchemaContract({**base, "description": "x" * LIMITS.schema_bytes})
        except FairyError as exc:
            rejected = {"code": exc.code}
        else:
            rejected = {"code": None}
        return {
            "accepted_bytes": accepted_bytes,
            "accepted_seconds": round(elapsed, 3),
            "rejected": rejected,
            "rejection_seconds": round(time.perf_counter() - started, 3),
            "home": str(home),
        }


def _lock(root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        home = Path(temporary) / "state"
        with Workshop(home) as workshop:
            database = str(workshop.store.home / "workshop.sqlite3")
        first = sqlite3.connect(
            database,
            isolation_level=None,
            timeout=LIMITS.sqlite_busy_seconds,
            check_same_thread=False,
        )
        second = sqlite3.connect(database, isolation_level=None, timeout=LIMITS.sqlite_busy_seconds)
        try:
            first.execute("BEGIN IMMEDIATE")

            def release() -> None:
                time.sleep(0.25)
                first.execute("COMMIT")

            worker = threading.Thread(target=release)
            worker.start()
            time.sleep(0.05)
            started = time.perf_counter()
            second.execute("CREATE TABLE IF NOT EXISTS lock_probe(value INTEGER)")
            waited = time.perf_counter() - started
            worker.join()
            second.execute("DROP TABLE IF EXISTS lock_probe")
            return {
                "wait_seconds": round(waited, 3),
                "busy_timeout_seconds": LIMITS.sqlite_busy_seconds,
                "succeeded": True,
            }
        finally:
            first.close()
            second.close()


def _backup(root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        home = Path(temporary) / "state"
        payload = "x" * (8 * MiB)
        with Workshop(home) as workshop:
            for index in range(3):
                task = workshop.start(f"Measure backup growth {index}")
                observed = workshop.invoke(task, "text.write", {"path": "body.md", "text": payload})
                if observed["status"] != "ok":
                    raise RuntimeError(observed)
        target = Path(temporary) / "backup"
        started = time.perf_counter()
        result = backup_state(home, target)
        elapsed = time.perf_counter() - started
        backup_bytes = sum(item.stat().st_size for item in target.iterdir() if item.is_file())
        return {
            "elapsed_seconds": round(elapsed, 3),
            "database_bytes": _database_bytes(home),
            "backup_bytes": backup_bytes,
            "counts": result["counts"],
        }


def _worker(name: str, root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    if name == "capture":
        return _capture(root)
    if name == "aggregate":
        return _aggregate(root)
    if name == "full-aggregate":
        return _full_aggregate(root)
    if name == "normal":
        return _normal_calls(root)
    if name == "schema":
        return _schema(root)
    if name == "lock":
        return _lock(root)
    if name == "backup":
        return _backup(root)
    raise ValueError(name)


def _host() -> dict[str, Any]:
    meminfo = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        key, value = line.split(":", 1)
        meminfo[key] = value.strip()
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "sqlite": sqlite3.sqlite_version,
        "cpu_count": os.cpu_count(),
        "memory_total": meminfo.get("MemTotal"),
        "disk_free_bytes": os.statvfs(".").f_bavail * os.statvfs(".").f_frsize,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure the frozen AstroFairy resource policy")
    parser.add_argument(
        "--worker",
        choices=["capture", "aggregate", "full-aggregate", "normal", "schema", "lock", "backup"],
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(".evaluation/optimization-implementation/normal-work"),
    )
    parser.add_argument("--out", type=Path)
    parser.add_argument("--size", type=int)
    arguments = parser.parse_args(argv)
    if arguments.worker is not None:
        if arguments.size is not None:
            os.environ["FAIRY_MEASURE_BYTES"] = str(arguments.size)
        print(json.dumps(_worker(arguments.worker, arguments.root), ensure_ascii=False))
        return 0
    root = arguments.root
    root.mkdir(parents=True, exist_ok=True)
    workloads: dict[str, Any] = {}
    for size in (32 * MiB, 128 * MiB, 256 * MiB):
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(__file__).resolve()),
                "--worker",
                "capture",
                "--root",
                str(root),
                "--size",
                str(size),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=600,
        )
        workloads[f"capture_{size // MiB}MiB"] = json.loads(completed.stdout)
    for name in ("aggregate", "full-aggregate", "normal", "schema", "lock", "backup"):
        completed = subprocess.run(
            [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", name, "--root", str(root)],
            capture_output=True,
            text=True,
            check=True,
            timeout=600,
        )
        workloads[name] = json.loads(completed.stdout)
    result = {
        "format": 1,
        "measured_at": datetime.now(UTC).isoformat(),
        "limits": LIMITS.manifest(),
        "host": _host(),
        "workloads": workloads,
        "unknown": {
            "host_tokens": "Host-managed; not exposed by this local runner measurement.",
            "currency_cost": "Host-managed; no provider billing access in this run.",
            "whole_task_wall_time": "Measured workloads only; no real host conversation was executed.",
            "two_gib_aggregate_capture": (
                "The full 2 GiB aggregate and one-byte-over rejection were executed; see full-aggregate."
            ),
        },
    }
    if arguments.out is not None:
        arguments.out.parent.mkdir(parents=True, exist_ok=True)
        arguments.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
