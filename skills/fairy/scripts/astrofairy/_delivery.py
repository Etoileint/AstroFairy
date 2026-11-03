from __future__ import annotations

import hashlib
import json
import shutil
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from astrofairy._capabilities import atomic_write
from astrofairy._contracts import canonical, object_value
from astrofairy._errors import FairyError
from astrofairy._limits import LIMITS

if TYPE_CHECKING:
    from astrofairy._kernel import State
    from astrofairy._store import Store

_DELIVERY_LOCK_TIMEOUT = LIMITS.delivery_lock_seconds
_BAGIT_PROCESS_LOCK = threading.RLock()


def _bagit() -> Any:
    try:
        import logging  # noqa: PLC0415 - lazy delivery readiness probe.
        from importlib.metadata import version  # noqa: PLC0415 - lazy delivery readiness probe.

        from bagit import (  # type: ignore[import-untyped]  # noqa: PLC0415 - lazy delivery import.
            Bag,
            BagValidationError,
            make_bag,
        )
    except Exception as exc:
        raise FairyError(
            "runtime_setup_required",
            "Prepare the vendored BagIt delivery wheel before exporting a bag",
        ) from exc
    logging.getLogger("bagit").setLevel(logging.CRITICAL)
    if version("bagit") != "1.9.0":
        raise FairyError(
            "runtime_setup_required", "The installed BagIt version does not match the vendored wheel"
        )
    return Bag, BagValidationError, make_bag


def _file_lock(path: Path) -> Any:
    try:
        from filelock import FileLock, Timeout  # noqa: PLC0415 - lazy native lock import.
    except Exception as exc:
        raise FairyError("runtime_setup_required", "Prepare the locked native file lock dependency") from exc
    try:
        lock = FileLock(
            str(path),
            timeout=_DELIVERY_LOCK_TIMEOUT,
            mode=0o600,
            fallback_to_soft=False,
            preserve_lock_file=True,
        )
        lock.acquire()
    except Timeout as exc:
        raise FairyError("storage_busy", "Delivery is busy; preserve state and retry later") from exc
    except Exception as exc:
        raise FairyError("runtime_setup_required", "Delivery requires a working native file lock") from exc
    return lock


def _private_tree(root: Path) -> None:
    root.chmod(0o700)
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_symlink():
            raise FairyError("integrity", "Delivery staging must not contain symbolic links")
        path.chmod(0o700 if path.is_dir() else 0o600)


def _bag_version(root: Path) -> str:
    text = (root / "bagit.txt").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("BagIt-Version:"):
            return line.split(":", 1)[1].strip()
    raise FairyError("integrity", "BagIt delivery has no version declaration")


def _write_bagit_1(root: Path) -> None:
    atomic_write(root / "bagit.txt", b"BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8\n")
    tag_files = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and not path.relative_to(root).as_posix().startswith("data/")
        and not path.name.startswith("tagmanifest-")
    ]
    lines = [
        hashlib.sha256(path.read_bytes()).hexdigest() + " " + path.relative_to(root).as_posix()
        for path in sorted(tag_files, key=lambda item: item.relative_to(root).as_posix())
    ]
    atomic_write(root / "tagmanifest-sha256.txt", ("\n".join(lines) + "\n").encode("utf-8"))


def _verify(
    root: Path,
    state: State | None = None,
    store: Store | None = None,
    inspection: dict[str, Any] | None = None,
) -> None:
    bag_type, _validation_error, _make_bag = _bagit()
    try:
        if any(path.is_symlink() for path in root.rglob("*")):
            raise FairyError("integrity", "BagIt delivery contains a symbolic link")
        if _bag_version(root) != "1.0":
            raise FairyError("integrity", "BagIt delivery is not the promised 1.0 format")
        with _BAGIT_PROCESS_LOCK:
            bag = bag_type(str(root))
            if not bag.validate():
                raise FairyError("integrity", "BagIt delivery did not pass full validation")
        payload = {path.relative_to(root).as_posix() for path in (root / "data").rglob("*") if path.is_file()}
        tags = {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and not path.is_relative_to(root / "data")
        }
        expected_payload = set(bag.payload_entries())
        expected_tags = {name for name in bag.entries if not name.startswith("data/")}
        for name in bag.tagmanifest_files():
            path = Path(name)
            expected_tags.add(path.relative_to(root).as_posix() if path.is_absolute() else path.as_posix())
        if payload != expected_payload or tags != expected_tags:
            raise FairyError("integrity", "BagIt delivery file set differs from its manifests")
        if state is None:
            return
        if store is None or inspection is None:
            raise FairyError("integrity", "Delivery authority check needs the recorded store and projection")
        receipt = object_value(json.loads((root / "receipt.json").read_text(encoding="utf-8")))
        snapshot = state.snapshot
        members = [] if snapshot is None else snapshot["members"]
        expected_files = {"data/" + member["path"]: member for member in members}
        if payload != set(expected_files):
            raise FairyError("integrity", "Delivered payload set differs from the authoritative snapshot")
        if canonical(receipt) != canonical(_receipt(state, inspection)):
            raise FairyError("integrity", "Delivery receipt differs from the authoritative projection")
        for name, member in expected_files.items():
            path = root / name
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if path.stat().st_size != member["bytes"] or digest != member["ref"]:
                raise FairyError("integrity", "Delivered member bytes do not match the snapshot")
            store.hash_ref(member["ref"])
    except FairyError:
        raise
    except Exception as exc:
        raise FairyError("integrity", "BagIt delivery did not pass full validation") from exc


def _links(root: Path, state: State) -> dict[str, Any]:
    snapshot = state.snapshot
    members = [] if snapshot is None else snapshot["members"]
    files = {member["path"]: str(root / "data" / member["path"]) for member in members}
    return {
        "task": state.task,
        "seq": state.seq,
        "outcome": state.outcome,
        "snapshot": snapshot,
        "bag_path": str(root),
        "receipt_path": str(root / "receipt.json"),
        "instructions_path": str(root / "README.txt"),
        "files": files,
        "artifact_path": next(iter(files.values())) if len(files) == 1 else None,
        "execution_settled": state.execution_settled(),
        "execution_conflicts": state.execution_conflicts(),
    }


def _receipt(state: State, inspection: dict[str, Any]) -> dict[str, Any]:
    snapshot = state.snapshot
    members = {
        "data/" + member["path"]: {
            "role": member["role"],
            "bytes": member["bytes"],
            "media_type": member["media_type"],
        }
        for member in ([] if snapshot is None else snapshot["members"])
    }
    return {
        **inspection,
        "bag": {
            "format": "bagit-1.0",
            "payload_manifest": "manifest-sha256.txt",
            "validation": "full",
        },
        "delivery_files": members,
    }


def _readme(state: State) -> bytes:
    snapshot = state.snapshot
    lines = [
        f"AstroFairy delivery for task {state.task}",
        f"Goal: {state.spec['goal']}",
        f"Assumptions: {', '.join(state.spec['assumptions']) or 'none recorded'}",
        f"Snapshot: {snapshot['ref'] if snapshot is not None else 'none'}",
        f"Outcome: {state.outcome}",
        "",
        "Formal members and required roles:",
        f"Required roles: {', '.join(state.spec.get('required_roles', [])) or 'none'}",
    ]
    if snapshot is None:
        lines.append("- none (the task closed without a published snapshot)")
    else:
        lines.extend(
            f"- data/{member['path']} "
            f"(role: {member['role']}, {member['bytes']} bytes, {member['media_type']})"
            for member in snapshot["members"]
        )
    lines.extend(
        [
            "",
            "Check range:",
            *[
                f"- {criterion['id']} [{criterion['scope']}]: {criterion['description']}"
                for criterion in state.spec["criteria"]
            ],
            "",
            "Receipt: receipt.json",
            "BagIt-Version: 1.0; the receipt and snapshot binding are in receipt.json.",
            "Validate the bag from this directory with:",
            "  python -c \"import bagit; bagit.Bag('.').validate()\"",
            "This validates local payload/tag bytes.",
            "It is not an external authenticity or semantic-quality proof.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _build_staging(staging: Path, state: State, store: Store, inspection: dict[str, Any]) -> None:
    snapshot = state.snapshot
    for member in [] if snapshot is None else snapshot["members"]:
        target = staging / member["path"]
        size = store.copy_to_file(member["ref"], target)
        if size != member["bytes"]:
            raise FairyError("integrity", "Delivered member byte count does not match the snapshot")
    _bag_type, _validation_error, make_bag = _bagit()
    try:
        with _BAGIT_PROCESS_LOCK:
            bag = make_bag(
                str(staging),
                checksums=["sha256"],
                bag_info={
                    "Source-Organization": "AstroFairy",
                    "External-Description": (
                        "Task " + state.task + " snapshot " + (snapshot["ref"] if snapshot else "none")
                    ),
                    "Bagging-Date": datetime.now(UTC).date().isoformat(),
                },
            )
            if not (staging / "manifest-sha256.txt").exists():
                atomic_write(staging / "manifest-sha256.txt", b"")
            atomic_write(staging / "receipt.json", canonical(_receipt(state, inspection)))
            atomic_write(staging / "README.txt", _readme(state))
            bag.save()
            _write_bagit_1(staging)
    except Exception as exc:
        raise FairyError("integrity", "BagIt generation failed; delivery was not published") from exc
    _private_tree(staging)
    _verify(staging, state, store, inspection)


def deliver(home: Path, state: State, store: Store, inspection: dict[str, Any]) -> dict[str, Any]:
    if state.outcome is None:
        raise FairyError("not_ready", "Close the task before exporting delivery")
    root = home / "deliveries" / state.task
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = _file_lock(root / ".delivery.lock")
    try:
        final = root / str(state.seq)
        if final.is_dir():
            _verify(final, state, store, inspection)
            return _links(final, state)
        for stale in root.glob(".staging-*"):
            if stale.is_dir() and not stale.is_symlink():
                shutil.rmtree(stale)
        staging = root / (".staging-" + uuid.uuid4().hex)
        staging.mkdir(mode=0o700)
        try:
            _build_staging(staging, state, store, inspection)
            if final.exists():
                _verify(final, state, store, inspection)
                shutil.rmtree(staging)
                return _links(final, state)
            staging.rename(final)
        except BaseException:
            if not final.exists():
                shutil.rmtree(staging, ignore_errors=True)
            raise
        _verify(final, state, store, inspection)
        return _links(final, state)
    finally:
        lock.release()


def status() -> dict[str, Any]:
    try:
        _bag_type, _validation_error, _make_bag = _bagit()
    except FairyError as exc:
        return {"ready": False, **exc.as_dict()}
    return {"ready": True, "version": "1.9.0", "bag": "bagit"}
