from __future__ import annotations

import hashlib
import json
import ntpath
import os
import shutil
import stat
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, cast

from astrofairy._capabilities import atomic_write
from astrofairy._contracts import canonical, object_value, relative_path
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


def _link_reason(path: Path) -> str | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise FairyError(
            "unsafe_delivery",
            "A delivery path cannot be inspected; it was left untouched",
            details={"path": path.name, "reason": "unreadable"},
        ) from exc
    if stat.S_ISLNK(info.st_mode):
        return "symbolic_link"
    if path.is_junction():
        return "junction"
    attributes = getattr(info, "st_file_attributes", 0)
    if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
        return "reparse_point"
    return None


def _refuse_redirect(path: Path, reason: str) -> None:
    raise FairyError(
        "unsafe_delivery",
        "A delivery path redirects outside the approved home; "
        "move the redirect aside instead of following it",
        details={"path": path.name, "reason": reason},
    )


def _require_plain_directory(path: Path, *, create: bool) -> None:
    reason = _link_reason(path)
    if reason is not None:
        _refuse_redirect(path, reason)
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        reason = _link_reason(path)
        if reason is not None:
            _refuse_redirect(path, reason)
    if not path.is_dir():
        raise FairyError(
            "unsafe_delivery",
            "A delivery path is not a plain directory",
            details={"path": path.name},
        )


def _delivery_root(home: Path, task: str, *, create: bool) -> Path:
    if not home.is_dir():
        raise FairyError("unsafe_delivery", "The approved home is not a directory")
    deliveries = home / "deliveries"
    _require_plain_directory(deliveries, create=create)
    root = deliveries / task
    _require_plain_directory(root, create=create)
    return root


def _assert_plain_tree(root: Path) -> None:
    reason = _link_reason(root)
    if reason is not None:
        _refuse_redirect(root, reason)
    errors: list[OSError] = []
    for current, directories, files in os.walk(root, followlinks=False, onerror=errors.append):
        for name in [*directories, *files]:
            path = Path(current) / name
            reason = _link_reason(path)
            if reason is not None:
                _refuse_redirect(path, reason)
    if errors:
        raise FairyError(
            "unsafe_delivery",
            "A delivery subtree cannot be inspected; it was left untouched",
            details={"path": root.name, "reason": "unreadable_subtree"},
        )


def _manifest_identity(raw: str, root: Path) -> str:
    if not isinstance(raw, str) or not raw:
        raise FairyError("integrity", "BagIt manifests expose an empty path")
    windows_flavor = "\\" in raw or bool(ntpath.splitdrive(raw)[0])
    if windows_flavor:
        if raw.startswith(("\\\\", "//")):
            raise FairyError("integrity", "BagIt manifests expose a UNC path")
        drive, _rest = ntpath.splitdrive(raw)
        if drive:
            if os.name != "nt":
                raise FairyError("integrity", "BagIt manifests expose a foreign absolute path")
            try:
                normalized = ntpath.relpath(raw, str(root))
            except ValueError as exc:
                raise FairyError("integrity", "BagIt manifest path is outside the bag root") from exc
            if ntpath.isabs(normalized) or normalized == ".." or normalized.startswith(".." + os.sep):
                raise FairyError("integrity", "BagIt manifest path is outside the bag root")
        else:
            normalized = ntpath.normpath(raw)
            if normalized in {"", "."} or normalized.split("\\")[0] == "..":
                raise FairyError("integrity", "BagIt manifest path escapes the bag root")
        candidate = normalized.replace("\\", "/")
    else:
        normalized = PurePosixPath(raw).as_posix()
        if normalized.startswith("/"):
            try:
                candidate = PurePosixPath(normalized).relative_to(root.as_posix()).as_posix()
            except ValueError as exc:
                raise FairyError("integrity", "BagIt manifest path is outside the bag root") from exc
        else:
            candidate = normalized
        if candidate in {"", "."} or any(part in {"", ".", ".."} for part in candidate.split("/")):
            raise FairyError("integrity", "BagIt manifest path escapes the bag root")
    try:
        return relative_path(candidate, "BagIt manifest path")
    except FairyError as exc:
        raise FairyError(
            "integrity",
            "BagIt manifest path is not a canonical bag member",
            details={"path": candidate[:200]},
        ) from exc


def _manifest_identities(keys: Any, root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in keys:
        identity = _manifest_identity(raw, root)
        first = result.get(identity)
        if first is not None and first != raw:
            raise FairyError(
                "integrity",
                "BagIt manifests expose distinct paths that collide after conversion",
                details={"path": identity},
            )
        result[identity] = raw
    return result


def _private_tree(root: Path) -> None:
    _assert_plain_tree(root)
    root.chmod(0o700)
    for path in sorted(root.rglob("*"), reverse=True):
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
        _assert_plain_tree(root)
        if _bag_version(root) != "1.0":
            raise FairyError("integrity", "BagIt delivery is not the promised 1.0 format")
        with _BAGIT_PROCESS_LOCK:
            bag = bag_type(str(root))
            if not bag.validate():
                raise FairyError("integrity", "BagIt delivery did not pass full validation")
        payload = {
            relative_path(path.relative_to(root).as_posix())
            for path in (root / "data").rglob("*")
            if path.is_file()
        }
        tags = {
            relative_path(path.relative_to(root).as_posix())
            for path in root.rglob("*")
            if path.is_file() and not path.is_relative_to(root / "data")
        }
        expected_payload = set(_manifest_identities(bag.payload_entries(), root))
        entries = _manifest_identities(bag.entries, root)
        expected_tags = {identity for identity in entries if not identity.startswith("data/")}
        expected_tags |= set(_manifest_identities(bag.tagmanifest_files(), root))
        if payload != expected_payload or tags != expected_tags:
            raise FairyError("integrity", "BagIt delivery file set differs from its manifests")
        if state is None:
            return
        if store is None or inspection is None:
            raise FairyError("integrity", "Delivery authority check needs the recorded store and projection")
        receipt = object_value(json.loads((root / "receipt.json").read_text(encoding="utf-8")))
        if receipt.get("format") != 2:
            raise FairyError(
                "version",
                "This delivery uses an unsupported receipt projection; rebuild it explicitly",
                details={"receipt_format": receipt.get("format"), "supported": 2},
            )
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
        "state": "validated",
        "task": state.task,
        "revision": state.revision,
        "seq": state.seq,
        "outcome": state.outcome,
        "snapshot": snapshot,
        "bag_path": str(root),
        "receipt_path": str(root / "receipt.json"),
        "instructions_path": str(root / "README.txt"),
        "files": files,
        "artifact_path": next(iter(files.values())) if len(files) == 1 else None,
        "validation": {"depth": "full", "at": datetime.now(UTC).isoformat(), "receipt_projection": 2},
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
        "format": 2,
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


def observe(home: Path, task: str, seq: int) -> dict[str, Any]:
    target = home / "deliveries" / task / str(seq)
    observation: dict[str, Any] = {
        "state": "absent",
        "task": task,
        "seq": seq,
        "target": str(target),
        "validation": "not_checked",
    }
    try:
        for path in (home / "deliveries", home / "deliveries" / task, target):
            reason = _link_reason(path)
            if reason is not None:
                return {**observation, "state": "unsafe", "reason": reason}
        if not home.is_dir() or not target.exists():
            return observation
        if not target.is_dir():
            return {**observation, "state": "unsafe", "reason": "not_a_directory"}
        return {**observation, "state": "unverified"}
    except FairyError:
        return {**observation, "state": "unsafe", "reason": "unreadable"}


def _repair_hint(state: State, target: Path) -> dict[str, Any]:
    return {
        "target": target.name,
        "repair_command": f"deliver {state.task} --repair --expected-seq {state.seq}",
    }


def _validated_or_refuse(
    final: Path,
    state: State,
    store: Store,
    inspection: dict[str, Any],
    *,
    repair: bool,
) -> dict[str, Any] | None:
    try:
        _verify(final, state, store, inspection)
        return _links(final, state)
    except FairyError as exc:
        if exc.code == "unsafe_delivery":
            raise
        if not repair:
            if exc.code in {"integrity", "version"}:
                raise FairyError(
                    exc.code,
                    exc.message,
                    details={**(exc.details or {}), **_repair_hint(state, final)},
                ) from exc
            raise
        if exc.code not in {"integrity", "version"}:
            raise
        return None


def _publish_repair(root: Path, final: Path, staging: Path, task: str) -> str:
    quarantine = root / f".quarantine-{final.name}-{uuid.uuid4().hex}"
    if _link_reason(quarantine) is not None or quarantine.exists():
        raise FairyError(
            "integrity", "The repair quarantine target already exists; inspect it before retrying"
        )
    _assert_plain_tree(final)
    final.rename(quarantine)
    try:
        staging.rename(final)
    except BaseException as exc:
        raise FairyError(
            "storage_failed",
            "Repair quarantined the invalid export but could not publish the replacement",
            details={
                "task": task,
                "quarantined": quarantine.name,
                "published": False,
                "completed": ["staging_validated", "quarantine"],
                "recovery": f"deliver {task}",
            },
        ) from exc
    return quarantine.name


def _progress_failure(exc: BaseException, *, task: str, progress: dict[str, Any]) -> FairyError:
    details = dict(exc.details or {}) if isinstance(exc, FairyError) else {}
    details.setdefault("task", task)
    details.setdefault("published", progress["published"])
    details.setdefault("completed", list(progress["completed"]))
    details.setdefault("recovery", f"deliver {task}")
    if progress["quarantine"] is not None:
        details.setdefault("quarantined", progress["quarantine"])
    if isinstance(exc, FairyError):
        return FairyError(exc.code, exc.message, details=details)
    details["exception"] = type(exc).__name__
    return FairyError(
        "storage_failed",
        "Delivery failed after it had begun; inspect the target before retrying",
        details=details,
    )


def _deliver_locked(
    home: Path,
    state: State,
    store: Store,
    inspection: dict[str, Any],
    *,
    repair: bool,
    progress: dict[str, Any],
) -> dict[str, Any]:
    root = _delivery_root(home, state.task, create=False)
    final = root / str(state.seq)
    reason = _link_reason(final)
    if reason is not None:
        _refuse_redirect(final, reason)
    target_exists = final.exists()
    if target_exists and final.is_dir():
        validated = _validated_or_refuse(final, state, store, inspection, repair=repair)
        if validated is not None:
            return validated
    elif target_exists and not repair:
        raise FairyError(
            "integrity",
            "The delivery target is not a directory; use an explicit repair after inspection",
            details=_repair_hint(state, final),
        )
    for stale in root.glob(".staging-*"):
        if _link_reason(stale) is None and stale.is_dir():
            shutil.rmtree(stale)
    staging = root / (".staging-" + uuid.uuid4().hex)
    try:
        _require_plain_directory(staging, create=True)
        _build_staging(staging, state, store, inspection)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    progress["completed"] = ["staging_validated"]
    try:
        reason = _link_reason(final)
        if reason is not None:
            _refuse_redirect(final, reason)
        if final.exists() and not repair:
            validated = _validated_or_refuse(final, state, store, inspection, repair=False)
            if validated is not None:
                shutil.rmtree(staging)
                return validated
        if final.exists():
            quarantine = _publish_repair(root, final, staging, state.task)
            progress["quarantine"] = quarantine
            progress["completed"].append("quarantine")
        else:
            staging.rename(final)
        progress["published"] = True
        progress["completed"].append("publication")
        reason = _link_reason(final)
        if reason is not None:
            _refuse_redirect(final, reason)
        _verify(final, state, store, inspection)
        return _links(final, state)
    except BaseException:
        try:
            removable = _link_reason(final) is None and not final.exists()
        except FairyError:
            removable = False
        if removable:
            shutil.rmtree(staging, ignore_errors=True)
        raise


def deliver(
    home: Path,
    state: State,
    store: Store,
    inspection: dict[str, Any],
    *,
    repair: bool = False,
) -> dict[str, Any]:
    if state.outcome is None:
        raise FairyError("not_ready", "Close the task before exporting delivery")
    home = home.resolve()
    root = _delivery_root(home, state.task, create=True)
    reason = _link_reason(root / ".delivery.lock")
    if reason is not None:
        _refuse_redirect(root / ".delivery.lock", reason)
    lock = _file_lock(root / ".delivery.lock")
    progress: dict[str, Any] = {"completed": [], "published": False, "quarantine": None}
    failure: BaseException | None = None
    result: dict[str, Any] | None = None
    try:
        result = _deliver_locked(home, state, store, inspection, repair=repair, progress=progress)
    except BaseException as exc:  # noqa: BLE001 - every failure must still release the lock.
        failure = exc
    release_failure: BaseException | None = None
    try:
        lock.release()
    except BaseException as exc:  # noqa: BLE001 - release failure must not mask the delivery error.
        release_failure = exc
    if failure is not None:
        if release_failure is not None and isinstance(failure, FairyError):
            details = dict(failure.details or {})
            details.setdefault("lock_release", "failed")
            failure.details = details
        if progress["completed"]:
            raise _progress_failure(failure, task=state.task, progress=progress) from failure
        raise failure
    if release_failure is not None:
        raise _progress_failure(release_failure, task=state.task, progress=progress) from release_failure
    return cast("dict[str, Any]", result)


def status() -> dict[str, Any]:
    try:
        _bag_type, _validation_error, _make_bag = _bagit()
    except FairyError as exc:
        return {"ready": False, **exc.as_dict()}
    return {"ready": True, "version": "1.9.0", "bag": "bagit"}
