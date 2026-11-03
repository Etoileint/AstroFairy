from __future__ import annotations

import mimetypes
import os
import tempfile
from collections import Counter
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from astrofairy._contracts import (
    CAPABILITY_NAME,
    MAX_PATH_BYTES,
    MODEL_CAPABILITY,
    SchemaContract,
    canonical,
    content_ref,
    effect_value,
    object_value,
    output_value,
    parse_json,
    relative_path,
    snapshot_value,
    text_value,
)
from astrofairy._errors import FairyError
from astrofairy._library import KINDS, Library
from astrofairy._limits import LIMITS

if TYPE_CHECKING:
    from collections.abc import Callable

    from astrofairy._kernel import State
    from astrofairy._store import Store


@dataclass(frozen=True)
class Context:
    store: Store
    state: State
    call_id: str | None = None
    search: Any | None = None

    def path(self, relative: str) -> Path:
        root = (self.store.home / "workspaces" / self.state.task).resolve()
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or path == root:
            raise FairyError("permission", "File path must stay inside the task workspace")
        return path

    def content(self, ref: str) -> bytes:
        known = {item["ref"] for item in self.state.inputs}
        known.update(snapshot["ref"] for snapshot in self.state.snapshots)
        known.update(item["ref"] for item in self.state.outputs)
        known.update(self.state.assets)
        known.update(
            call["contract_ref"]
            for call in self.state.calls.values()
            if call["capability"] != MODEL_CAPABILITY
        )
        known.update(
            call["reconciler"]["contract_ref"] for call in self.state.calls.values() if call.get("reconciler")
        )
        if ref not in known:
            raise FairyError("permission", "Content is not an input, output or pinned asset of this task")
        return self.store.get(ref)

    def captured_refs(self) -> set[str]:
        refs = {item["ref"] for item in self.state.inputs}
        refs.update(item["ref"] for item in self.state.outputs)
        for snapshot in self.state.snapshots:
            refs.update(member["ref"] for member in snapshot["members"])
        return refs

    def check_capture_limit(self, ref: str, size: int) -> None:
        if size > LIMITS.content_bytes:
            raise FairyError("limit", "Content exceeds its byte budget")
        refs = self.captured_refs()
        total = sum(self.store.length(item) for item in refs)
        if ref not in refs:
            total += size
        if total > LIMITS.task_capture_bytes:
            raise FairyError("limit", "Task capture exceeds its aggregate byte budget")


@dataclass(frozen=True, init=False)
class Capability:
    effect: str
    handler: Callable[[Context, dict[str, Any]], dict[str, Any]]
    description: str
    prepare: Callable[[Context, dict[str, Any]], None] | None
    reconciler: str | None
    counted: bool
    _input: SchemaContract
    _output: SchemaContract | None

    def __init__(
        self,
        effect: str,
        handler: Callable[[Context, dict[str, Any]], dict[str, Any]],
        *,
        description: str,
        input_schema: dict[str, Any],
        output_schema: dict[str, Any] | None = None,
        prepare: Callable[[Context, dict[str, Any]], None] | None = None,
        reconciler: str | None = None,
        counted: bool = True,
    ) -> None:
        if not callable(handler) or (prepare is not None and not callable(prepare)):
            raise FairyError("invalid_contract", "Capability handlers and preflight must be callable")
        if reconciler is not None and (
            effect != "write" or not isinstance(reconciler, str) or not CAPABILITY_NAME.fullmatch(reconciler)
        ):
            raise FairyError("invalid_contract", "Only write capabilities may declare a named reconciler")
        object.__setattr__(self, "effect", effect_value(effect))
        object.__setattr__(self, "handler", handler)
        object.__setattr__(
            self,
            "description",
            text_value(description, "tool description", LIMITS.capability_description_bytes),
        )
        object.__setattr__(self, "prepare", prepare)
        object.__setattr__(self, "reconciler", reconciler)
        object.__setattr__(self, "counted", counted)
        object.__setattr__(self, "_input", SchemaContract(input_schema))
        object.__setattr__(
            self, "_output", SchemaContract(output_schema) if output_schema is not None else None
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return self._input.schema

    def definition(self, name: str) -> dict[str, Any]:
        result = {
            "name": name,
            "effect": self.effect,
            "description": self.description,
            "inputSchema": self.input_schema,
        }
        if self._output is not None:
            result["outputSchema"] = self._output.schema
        if self.reconciler is not None:
            result["reconciler"] = self.reconciler
        if len(canonical(result)) > LIMITS.tool_definition_bytes:
            raise FairyError("invalid_contract", "Tool definition exceeds its detail budget")
        return result

    def validate_input(self, parameters: dict[str, Any]) -> None:
        self._input.validate(parameters)

    def validate_result(self, result: dict[str, Any]) -> None:
        _validate_result(result, self._output)


def _validate_result(result: dict[str, Any], schema: SchemaContract | None) -> None:
    canonical(result)
    _result_contract().validate(result)
    for item in result["outputs"]:
        output_value(item)
    if schema is not None:
        schema.validate(result)


def validate_confirmation(
    proof: dict[str, Any], observed: dict[str, Any], definition: dict[str, Any]
) -> None:
    recovered = object_value(proof["result"])
    schema = definition.get("outputSchema")
    _validate_result(recovered, SchemaContract(schema) if schema is not None else None)
    if not Counter(canonical(item) for item in recovered["outputs"]) <= Counter(
        canonical(item) for item in observed["outputs"]
    ):
        raise FairyError("invalid", "Confirmed outputs must be captured by the verifier")


def _object_schema(properties: dict[str, Any], required: tuple[str, ...] = ()) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


_STRING = {"type": "string", "minLength": 1, "pattern": r"\S"}
_REF = {"type": "string", "minLength": 64, "maxLength": 64, "pattern": "^[a-f0-9]{64}$"}
_PATH = {
    "type": "string",
    "minLength": 1,
    "maxLength": MAX_PATH_BYTES,
    "pattern": r"^[^\x00-\x1f\x7f\\]+$",
    "description": "Canonical relative path inside the task workspace",
}


@cache
def _result_contract() -> SchemaContract:
    item = _object_schema(
        {"ref": _REF, "path": _PATH, "media_type": _STRING},
        ("ref", "path", "media_type"),
    )
    schema = _object_schema({"outputs": {"type": "array", "items": item}}, ("outputs",))
    schema["additionalProperties"] = True
    return SchemaContract(schema)


def _prepare_path(context: Context, parameters: dict[str, Any]) -> None:
    relative_path(text_value(parameters["path"], "workspace path"))
    context.path(parameters["path"])
    if "media_type" in parameters:
        text_value(parameters["media_type"], "media type")


def _prepare_write(context: Context, parameters: dict[str, Any]) -> None:
    _prepare_path(context, parameters)
    text_value(parameters["text"], "output text", LIMITS.blob_bytes)


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
    relative = relative_path(text_value(parameters.get("path"), "output path"))
    path = context.path(relative)
    text = text_value(parameters.get("text"), "output text", LIMITS.blob_bytes)
    data = text.encode("utf-8")
    atomic_write(path, data)
    ref = context.store.put(data)
    context.check_capture_limit(ref, len(data))
    return {
        "outputs": [{"ref": ref, "path": relative, "media_type": "text/plain"}],
        "path": str(path),
    }


def _capture(context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
    relative = relative_path(text_value(parameters.get("path"), "capture path"))
    path = context.path(relative)
    ref, size = context.store.put_file(path, limit=LIMITS.content_bytes)
    context.check_capture_limit(ref, size)
    return {
        "outputs": [
            {
                "ref": ref,
                "path": relative,
                "media_type": text_value(
                    parameters.get(
                        "media_type", mimetypes.guess_type(relative)[0] or "application/octet-stream"
                    ),
                    "media type",
                ),
            }
        ]
    }


def _read(context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
    data = context.content(content_ref(parameters.get("ref")))
    offset = int(parameters.get("offset", 0))
    limit = min(
        int(parameters.get("limit", LIMITS.content_read_characters)),
        LIMITS.content_read_characters,
    )
    text = data.decode("utf-8")
    fragment = text[offset : offset + limit]
    return {"outputs": [], "text": fragment, "next_offset": offset + len(fragment), "characters": len(text)}


def _search(context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
    query = parameters.get("query", "")
    if not isinstance(query, str):
        raise FairyError("invalid", "Search query must be text")
    limit = int(parameters.get("limit", LIMITS.search_default_limit))
    scope = parameters.get("scope")
    kind = parameters.get("kind")
    cursor = parameters.get("cursor")
    library = Library(context.store, search=context.search)
    page = library.search_page(
        query,
        limit,
        scope if isinstance(scope, str) else None,
        kind if isinstance(kind, str) else None,
        cursor if isinstance(cursor, str) else None,
    )
    return {"outputs": [], **page}


def _asset(context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
    ref = text_value(parameters.get("ref"), "asset reference")
    library = Library(context.store)
    if ref not in context.state.assets and library.status(ref) not in {"trial", "stable"}:
        raise FairyError("not_ready", "Only validated assets can be used in ordinary tasks")
    return {"outputs": [], "asset": library.get(ref), "asset_ref": ref}


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
    ref = content_ref(parameters.get("ref"), "checked content")
    checker = text_value(parameters.get("checker"), "checker")
    options = object_value(parameters.get("parameters", {}))
    verdict, basis = check_content(checker, context.content(ref), options)
    return {
        "outputs": [],
        "verdict": verdict,
        "basis": basis,
        "checked": {"ref": ref, "checker": checker, "parameters": options},
    }


def _snapshot_check(context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
    snapshot_ref = content_ref(parameters.get("snapshot"), "checked snapshot")
    checker = text_value(parameters.get("checker"), "checker")
    options = object_value(parameters.get("parameters", {}))
    raw_paths = parameters.get("paths")
    if not isinstance(raw_paths, list) or not raw_paths:
        raise FairyError("invalid", "Snapshot checks need explicit member paths")
    paths = [relative_path(item, "snapshot check path") for item in raw_paths]
    if paths != sorted(set(paths)):
        raise FairyError("invalid", "Snapshot check paths must be canonical and unique")
    body = object_value(parse_json(context.content(snapshot_ref).decode("utf-8")))
    if set(body) != {"format", "members"} or body.get("format") != 1:
        raise FairyError("integrity", "Checked snapshot object is invalid")
    snapshot = snapshot_value(body["members"])
    if snapshot["ref"] != snapshot_ref:
        raise FairyError("integrity", "Checked snapshot identity does not match its members")
    by_path = {member["path"]: member for member in snapshot["members"]}
    if any(path not in by_path for path in paths):
        raise FairyError("not_ready", "Snapshot member target is missing")
    if checker != "nonempty":
        raise FairyError("missing", "No mechanical checker registered for this criterion")
    checked = {"snapshot": snapshot_ref, "paths": paths, "checker": checker, "parameters": options}
    if any(not context.store.get(by_path[path]["ref"]).strip() for path in paths):
        return {"outputs": [], "verdict": "fail", "basis": "A checked member is empty", "checked": checked}
    return {
        "outputs": [],
        "verdict": "pass",
        "basis": "All checked members contain bytes",
        "checked": checked,
    }


def builtins() -> dict[str, Capability]:
    checked = _object_schema(
        {
            "ref": _REF,
            "checker": {"enum": ["nonempty", "json", "contains"]},
            "parameters": {"type": "object"},
        },
        ("ref", "checker"),
    )
    checked["allOf"] = [
        {
            "if": {"properties": {"checker": {"const": "contains"}}},
            "then": {
                "required": ["parameters"],
                "properties": {
                    "parameters": {
                        "type": "object",
                        "properties": {"text": _STRING},
                        "required": ["text"],
                        "additionalProperties": False,
                    }
                },
            },
        }
    ]
    return {
        "text.write": Capability(
            "write",
            _write,
            description="Write UTF-8 text inside the task workspace",
            input_schema=_object_schema(
                {
                    "path": _PATH,
                    "text": {
                        **_STRING,
                        "maxLength": LIMITS.blob_bytes,
                        "description": f"Nonblank text, at most {LIMITS.blob_bytes} UTF-8 bytes",
                    },
                },
                ("path", "text"),
            ),
            prepare=_prepare_write,
        ),
        "file.capture": Capability(
            "read",
            _capture,
            description="Capture workspace file bytes without changing the source",
            input_schema=_object_schema({"path": _PATH, "media_type": _STRING}, ("path",)),
            prepare=_prepare_path,
        ),
        "content.read": Capability(
            "read",
            _read,
            description="Read a bounded UTF-8 fragment of known task content; free",
            input_schema=_object_schema(
                {
                    "ref": _REF,
                    "offset": {"type": "integer", "minimum": 0},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": LIMITS.content_read_characters,
                    },
                },
                ("ref",),
            ),
            counted=False,
        ),
        "asset.search": Capability(
            "read",
            _search,
            description=(
                "Hybrid BM25/ICU and vector search over adopted asset heads; "
                f"default {LIMITS.search_default_limit}, pages up to {LIMITS.search_max_results}"
            ),
            input_schema=_object_schema(
                {
                    "query": {"type": "string"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": LIMITS.search_max_results,
                    },
                    "scope": {"enum": ["personal", "team"]},
                    "kind": {"enum": sorted(KINDS)},
                    "cursor": _STRING,
                }
            ),
        ),
        "asset.read": Capability(
            "read",
            _asset,
            description="Read and pin an approved asset or an already pinned version; free",
            input_schema=_object_schema({"ref": _REF}, ("ref",)),
            counted=False,
        ),
        "content.check": Capability(
            "read",
            _check,
            description="Check known content with nonempty, json or contains",
            input_schema=checked,
        ),
        "snapshot.check": Capability(
            "read",
            _snapshot_check,
            description="Check a published snapshot's selected members with nonempty",
            input_schema=_object_schema(
                {
                    "snapshot": _REF,
                    "checker": {"enum": ["nonempty"]},
                    "paths": {
                        "type": "array",
                        "minItems": 1,
                        "uniqueItems": True,
                        "items": _PATH,
                    },
                    "parameters": {"type": "object"},
                },
                ("snapshot", "checker", "paths"),
            ),
        ),
    }
