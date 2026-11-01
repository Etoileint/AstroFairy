from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import time
from datetime import UTC, datetime
from functools import cache
from typing import TYPE_CHECKING, Any

from astrofairy._capabilities import atomic_write, validate_confirmation
from astrofairy._contracts import MODEL_CAPABILITY, SchemaContract, canonical, object_value, parse_json
from astrofairy._documents import audit_archive, select
from astrofairy._errors import FairyError
from astrofairy._kernel import reconciliation_for, replay
from astrofairy._library import ASSET_STATES, validation_criteria
from astrofairy._store import STORE_VERSION, Store

if TYPE_CHECKING:
    from pathlib import Path
    from typing import NoReturn

    from astrofairy._kernel import State

_FILES = ("workshop.sqlite3", "documents.sqlite3")
_EXCLUDES = [
    "uncaptured_workspace_files",
    "exported_deliveries",
    "uncaptured_environment_and_credentials",
    "external_service_state",
]
_EVENT_KINDS = {
    "created",
    "invoked",
    "observed",
    "published",
    "reviewed",
    "asset_used",
    "revised",
    "asked",
    "answered",
    "feedback",
    "closed",
}


def _invalid() -> NoReturn:
    raise FairyError("integrity", "Recorded state or backup does not satisfy its integrity contract")


def _require(condition: bool) -> None:  # noqa: FBT001 - validates a predicate, not a behavior switch.
    if not condition:
        _invalid()


def _regular(path: Path) -> None:
    _require(path.is_file() and not path.is_symlink())


class _ReadOnly(Store):
    def __init__(self, home: Path) -> None:
        self.home = home.resolve()
        path = self.home / _FILES[0]
        _regular(path)
        self.connection = sqlite3.connect(
            path.as_uri() + "?mode=ro", uri=True, isolation_level=None, timeout=10
        )
        self.connection.row_factory = sqlite3.Row
        try:
            self.connection.execute("PRAGMA query_only=ON")
            self.connection.execute("BEGIN")
            self._require_version()
        except BaseException:
            self.connection.close()
            raise


@cache
def _manifest_schema() -> SchemaContract:
    return SchemaContract(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["format", "store", "created", "files", "excludes"],
            "additionalProperties": False,
            "properties": {
                "format": {"const": 1, "type": "integer"},
                "store": {"const": STORE_VERSION, "type": "integer"},
                "created": {"type": "string", "minLength": 1},
                "excludes": {"const": _EXCLUDES},
                "files": {
                    "type": "object",
                    "required": [_FILES[0]],
                    "additionalProperties": False,
                    "properties": {name: {"$ref": "#/$defs/file"} for name in _FILES},
                },
            },
            "$defs": {
                "file": {
                    "type": "object",
                    "required": ["bytes", "sha256"],
                    "additionalProperties": False,
                    "properties": {
                        "bytes": {"type": "integer", "minimum": 0},
                        "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                    },
                }
            },
        }
    )


def _fingerprint(path: Path) -> dict[str, Any]:
    _regular(path)
    with path.open("rb") as stream:
        size = os.fstat(stream.fileno()).st_size
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"bytes": size, "sha256": digest}


def _refs(store: Store, event: dict[str, Any], state: State, assets: set[str]) -> None:
    payload, kind = event["payload"], event["kind"]
    _require(kind in _EVENT_KINDS)
    refs: list[str] = []
    if kind == "created":
        for item in payload["inputs"]:
            refs.append(item["ref"])
            if "source_document" in item:
                locator = item["source_document"]
                _require(
                    isinstance(locator, dict)
                    and set(locator) in ({"document", "task", "bytes"}, {"document", "task", "bytes", "seq"})
                )
                _require(
                    isinstance(locator["task"], str) and bool(re.fullmatch(r"[a-f0-9]{32}", locator["task"]))
                )
                _require(type(locator["bytes"]) is int and locator["bytes"] >= 0)
                _require("seq" not in locator or (type(locator["seq"]) is int and locator["seq"] >= 0))
                _require(canonical(parse_json(store.get(item["ref"]).decode("utf-8"))) == canonical(locator))
                with select(store.home, locator["document"], task=locator["task"]) as (_node, audited):
                    _require(canonical({key: audited[key] for key in locator}) == canonical(locator))
    elif kind == "invoked":
        if payload["capability"] == MODEL_CAPABILITY:
            refs.extend(payload["refs"])
        else:
            refs.append(payload["contract_ref"])
            if payload.get("reconciler") is not None:
                refs.append(payload["reconciler"]["contract_ref"])
    elif kind == "observed":
        refs.extend(item["ref"] for item in payload["outputs"])
        if payload["origin"] == "tool" and payload["status"] == "ok":
            _require(canonical(payload["result"]["outputs"]) == canonical(payload["outputs"]))
            proof = reconciliation_for(state, payload["call"], payload)
            if proof is not None:
                target = state.calls[proof["target"]["call"]]
                definition = object_value(parse_json(store.get(target["contract_ref"]).decode("utf-8")))
                validate_confirmation(proof, payload["result"], definition)
                refs.extend(item["ref"] for item in proof["result"]["outputs"])
    elif kind in {"published", "reviewed", "asset_used"}:
        refs.append(payload["ref"])
        if kind == "reviewed":
            refs.extend(payload["evidence"])
        if kind == "asset_used":
            _require(payload["ref"] in assets)
    for ref in refs:
        store.get(ref)


def _assets(store: Store, states: dict[str, State]) -> set[str]:
    packages = {}
    for row in store.connection.execute("SELECT * FROM assets"):
        package = object_value(parse_json(store.get(row["ref"]).decode("utf-8")))
        actual = {key: row[key] for key in ("scope", "name", "version", "kind", "summary", "base")}
        actual["tags"] = parse_json(row["tags"])
        _require(canonical(actual) == canonical({key: package[key] for key in actual}))
        packages[row["ref"]] = package
    for package in packages.values():
        if package["base"] is not None:
            base = packages.get(package["base"])
            if base is None:
                _invalid()
            _require(
                base["scope"] == package["scope"]
                and base["name"] == package["name"]
                and base["version"] < package["version"]
            )
    seen = set()
    for row in store.connection.execute("SELECT * FROM asset_events"):
        _require(row["ref"] in packages and row["status"] in ASSET_STATES)
        seen.add(row["ref"])
        if row["status"] in {"trial", "stable"}:
            state = states.get(row["validation_task"])
            if state is None:
                _invalid()
            _require(
                state.outcome == "complete"
                and state.artifact is not None
                and state.artifact["ref"] == row["ref"]
            )
            _require(any(item["ref"] == row["ref"] for item in state.inputs))
            criteria = {item["id"]: item for item in state.spec["criteria"]}
            _require(
                all(canonical(criteria.get(item["id"])) == canonical(item) for item in validation_criteria())
            )
        else:
            _require(row["validation_task"] is None)
    _require(seen == set(packages))
    return set(packages)


def audit_state(home: Path) -> dict[str, Any]:
    _manifest_schema()
    store = _ReadOnly(home)
    try:
        _require([tuple(row) for row in store.connection.execute("PRAGMA integrity_check")] == [("ok",)])
        _require(not store.connection.execute("PRAGMA foreign_key_check").fetchall())
        blobs = 0
        for row in store.connection.execute("SELECT ref FROM blobs"):
            store.get(row["ref"])
            blobs += 1
        states = {}
        events = 0
        for task in store.tasks():
            _require(bool(re.fullmatch(r"[a-f0-9]{32}", task)))
            history = store.events(task)
            states[task] = replay(task, history)
            events += len(history)
        assets = _assets(store, states)
        for task, state in states.items():
            for event in store.events(task):
                _refs(store, event, state, assets)
        document_counts = {"document_nodes": 0, "documents": 0}
        path = store.home / _FILES[1]
        if os.path.lexists(path):
            _regular(path)
            document_counts = audit_archive(store.home)
        return {
            "store": STORE_VERSION,
            "tasks": len(states),
            "events": events,
            "blobs": blobs,
            "assets": len(assets),
            **document_counts,
        }
    finally:
        store.close()


def _new_directory(path: Path, source: Path) -> Path:
    target = path.absolute()
    _require(not target.is_symlink())
    target = target.resolve()
    source = source.resolve()
    _require(not target.is_relative_to(source) and not source.is_relative_to(target))
    target.mkdir(mode=0o700, parents=False)
    return target


def _copy_database(source: Path, target: Path) -> None:
    _regular(source)
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    incoming = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, isolation_level=None, timeout=1)
    try:
        outgoing = sqlite3.connect(target, isolation_level=None, timeout=1)
        try:
            deadline = time.monotonic() + 60

            def progress(_status: int, _remaining: int, _total: int) -> None:
                if time.monotonic() > deadline:
                    raise FairyError(
                        "storage_busy", "Backup exceeded its time budget; preserve the partial directory"
                    )

            incoming.backup(outgoing, pages=128, progress=progress, sleep=0.05)
            _require(outgoing.execute("PRAGMA journal_mode=DELETE").fetchone() == ("delete",))
        finally:
            outgoing.close()
    finally:
        incoming.close()
    with target.open("r+b") as stream:
        os.fsync(stream.fileno())


def backup_state(home: Path, target: Path) -> dict[str, Any]:
    _manifest_schema()
    _require(not os.path.lexists(home.resolve() / "restore.pending"))
    admitted = _ReadOnly(home)
    admitted.close()
    destination = _new_directory(target, home)
    files = {}
    for name in _FILES:
        source = home.resolve() / name
        if name == _FILES[0] or os.path.lexists(source):
            _copy_database(source, destination / name)
            files[name] = _fingerprint(destination / name)
    counts = audit_state(destination)
    manifest = {
        "format": 1,
        "store": STORE_VERSION,
        "created": datetime.now(UTC).isoformat(),
        "files": files,
        "excludes": _EXCLUDES,
    }
    _manifest_schema().validate(manifest)
    atomic_write(destination / "manifest.json", canonical(manifest))
    return {"backup": str(destination), "verified": True, "counts": counts, "excludes": _EXCLUDES}


def _manifest(directory: Path) -> dict[str, Any]:
    _require(directory.is_dir() and not directory.is_symlink())
    path = directory / "manifest.json"
    _regular(path)
    with path.open("rb") as stream:
        data = stream.read(16385)
    _require(len(data) <= 16384)
    manifest = object_value(parse_json(data.decode("utf-8")))
    _manifest_schema().validate(manifest)
    _require(canonical(manifest) == data and datetime.fromisoformat(manifest["created"]).tzinfo is not None)
    return manifest


def verify_backup(directory: Path) -> dict[str, Any]:
    manifest = _manifest(directory)
    for name, expected in manifest["files"].items():
        _require(_fingerprint(directory / name) == expected)
    _require({p.name for p in directory.iterdir()} == {"manifest.json", *manifest["files"]})
    counts = audit_state(directory)
    for name, expected in manifest["files"].items():
        _require(_fingerprint(directory / name) == expected)
    return {"verified": True, "counts": counts, "excludes": _EXCLUDES}


def restore_state(directory: Path, target: Path) -> dict[str, Any]:
    verify_backup(directory)
    manifest = _manifest(directory)
    destination = _new_directory(target, directory)
    marker = destination / "restore.pending"
    atomic_write(marker, b"Restore incomplete; preserve this directory until investigated.\n")
    for name, expected in manifest["files"].items():
        with (directory / name).open("rb") as incoming, (destination / name).open("xb") as outgoing:
            (destination / name).chmod(0o600)
            digest = hashlib.sha256()
            size = 0
            while chunk := incoming.read(1024 * 1024):
                outgoing.write(chunk)
                digest.update(chunk)
                size += len(chunk)
            outgoing.flush()
            os.fsync(outgoing.fileno())
        _require({"bytes": size, "sha256": digest.hexdigest()} == expected)
    counts = audit_state(destination)
    store = _ReadOnly(destination)
    try:
        for task in store.tasks():
            (destination / "workspaces" / task).mkdir(parents=True, mode=0o700)
    finally:
        store.close()
    marker.unlink()
    return {"home": str(destination), "restored": True, "counts": counts, "excludes": _EXCLUDES}
