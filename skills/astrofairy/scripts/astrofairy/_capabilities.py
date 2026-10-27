from __future__ import annotations

import mimetypes
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from astrofairy._contracts import (
    MAX_BLOB_BYTES,
    MAX_CONTEXT_BYTES,
    integer,
    object_value,
    parse_json,
    text_value,
)
from astrofairy._errors import FairyError
from astrofairy._library import Library

if TYPE_CHECKING:
    from collections.abc import Callable

    from astrofairy._kernel import State
    from astrofairy._store import Store


@dataclass(frozen=True)
class Context:
    store: Store
    state: State

    def path(self, relative: str) -> Path:
        root = (self.store.home / "workspaces" / self.state.task).resolve()
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or path == root:
            raise FairyError("permission", "File path must stay inside the task workspace")
        return path

    def content(self, ref: str) -> bytes:
        known = {item["ref"] for item in self.state.inputs + self.state.artifacts}
        known.update(self.state.assets)
        for call in self.state.calls.values():
            known.update(item["ref"] for item in call["outputs"])
        if ref not in known:
            raise FairyError("permission", "Content is not an input, output or pinned asset of this task")
        return self.store.get(ref)


@dataclass(frozen=True)
class Capability:
    effect: str
    handler: Callable[[Context, dict[str, Any]], dict[str, Any]]
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".fairy-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        Path(temporary).replace(path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _write(context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
    path = context.path(text_value(parameters.get("path"), "output path"))
    text = text_value(parameters.get("text"), "output text", MAX_BLOB_BYTES)
    data = text.encode("utf-8")
    atomic_write(path, data)
    ref = context.store.put(data)
    return {"outputs": [{"ref": ref, "name": path.name, "media_type": "text/plain"}], "path": str(path)}


def _capture(context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
    path = context.path(text_value(parameters.get("path"), "capture path"))
    with path.open("rb") as stream:
        data = stream.read(MAX_BLOB_BYTES + 1)
    ref = context.store.put(data)
    return {
        "outputs": [
            {
                "ref": ref,
                "name": path.name,
                "media_type": text_value(
                    parameters.get(
                        "media_type", mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                    ),
                    "media type",
                ),
            }
        ]
    }


def _read(context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
    data = context.content(text_value(parameters.get("ref"), "content reference"))
    offset = integer(parameters.get("offset", 0), "character offset")
    limit = min(
        integer(parameters.get("limit", MAX_CONTEXT_BYTES // 4), "character limit", 1), MAX_CONTEXT_BYTES // 4
    )
    text = data.decode("utf-8")
    fragment = text[offset : offset + limit]
    return {"outputs": [], "text": fragment, "next_offset": offset + len(fragment), "characters": len(text)}


def _search(context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
    query = parameters.get("query", "")
    if not isinstance(query, str):
        raise FairyError("invalid", "Search query must be text")
    limit = integer(parameters.get("limit", 3), "search limit", 1)
    return {"outputs": [], "matches": Library(context.store).search(query, limit)}


def _asset(context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
    ref = text_value(parameters.get("ref"), "asset reference")
    library = Library(context.store)
    if ref not in context.state.assets and library.status(ref) not in {"trial", "stable"}:
        raise FairyError("not_ready", "Only validated assets can be used in ordinary tasks")
    package = library.get(ref)
    if len(context.store.get(ref)) > MAX_CONTEXT_BYTES:
        return {
            "outputs": [],
            "asset_ref": ref,
            "name": package["name"],
            "summary": package["summary"],
            "read_with": "content.read",
        }
    return {"outputs": [], "asset": package, "asset_ref": ref}


def check_content(checker: str, data: bytes, parameters: dict[str, Any]) -> tuple[str, str]:
    if checker == "nonempty":
        return ("pass", "Content contains bytes") if data.strip() else ("fail", "Content is empty")
    if checker == "json":
        try:
            parse_json(data.decode("utf-8"))
        except (FairyError, UnicodeError):
            return "fail", "Content is not valid UTF-8 JSON"
        return "pass", "Content parses as strict UTF-8 JSON"
    if checker == "contains":
        needle = text_value(parameters.get("text"), "required text")
        return (
            ("pass", "Required text is present")
            if needle in data.decode("utf-8")
            else ("fail", "Required text is absent")
        )
    raise FairyError("missing", "No mechanical checker registered for this criterion")


def _check(context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
    ref = text_value(parameters.get("ref"), "checked content")
    verdict, basis = check_content(
        text_value(parameters.get("checker"), "checker"),
        context.content(ref),
        object_value(parameters.get("parameters", {})),
    )
    return {"outputs": [], "verdict": verdict, "basis": basis, "checked_ref": ref}


def builtins() -> dict[str, Capability]:
    return {
        "text.write": Capability("write", _write, ("path", "text")),
        "file.capture": Capability("read", _capture, ("path",), ("media_type",)),
        "content.read": Capability("read", _read, ("ref",), ("offset", "limit")),
        "asset.search": Capability("read", _search, (), ("query", "limit")),
        "asset.read": Capability("read", _asset, ("ref",)),
        "content.check": Capability("read", _check, ("ref", "checker"), ("parameters",)),
    }
