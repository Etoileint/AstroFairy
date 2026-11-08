from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from astrofairy import _documents
from astrofairy._contracts import canonical, integer
from astrofairy._errors import FairyError
from astrofairy._limits import LIMITS

if TYPE_CHECKING:
    from pathlib import Path

_REF = re.compile(r"[a-f0-9]{64}\Z")
_TASK = re.compile(r"[a-f0-9]{32}\Z")
_IDENTITIES = {"task", "call", "learning_task", "validation_task"}
_SCALARS = {
    "seq",
    "revision",
    "action",
    "status",
    "outcome",
    "committed",
    "committed_seq",
    "budget_left",
    "execution_settled",
    "ready",
    "resource_warning",
    "provisional",
}
_DELIVERY_SCALARS = {"state", "task", "seq", "target", "committed", "committed_seq", "selected_seq"}


def _delivery_control(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    summary = {
        key: item
        for key, item in value.items()
        if key in _DELIVERY_SCALARS
        and (
            type(item) in {int, bool, type(None)}
            or (isinstance(item, str) and len(item.encode("utf-8")) <= LIMITS.control_scalar_bytes)
        )
    }
    error = value.get("error")
    if isinstance(error, dict) and isinstance(error.get("error"), str):
        summary["error"] = error["error"]
    recovery = value.get("recovery")
    if isinstance(recovery, dict) and isinstance(recovery.get("command"), str):
        summary["recovery"] = recovery["command"]
    return summary


def controls(value: dict[str, Any], task: str | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        key: item
        for key, item in value.items()
        if key in _IDENTITIES and isinstance(item, str) and _TASK.fullmatch(item)
    }
    if task is not None and _TASK.fullmatch(task):
        result.setdefault("task", task)
    result.update(
        (key, item)
        for key, item in value.items()
        if key in _SCALARS
        and (
            type(item) in {int, bool, type(None)}
            or (isinstance(item, str) and len(item.encode("utf-8")) <= LIMITS.control_scalar_bytes)
        )
    )
    delivery = _delivery_control(value.get("delivery"))
    if delivery:
        result["delivery"] = delivery
    return result


def encode_response(home: Path, value: dict[str, Any], *, task: str | None = None) -> bytes:
    encoded = canonical(value) + b"\n"
    if len(encoded) <= LIMITS.response_bytes:
        return encoded
    safe = controls(value, task)
    descriptor = _documents.freeze(home, value, task=safe.get("task"))
    summary: dict[str, Any] = {
        "deferred": True,
        **descriptor,
        "control": safe,
        "counts": {key: len(item) for key, item in value.items() if isinstance(item, list)},
        "read_via": "read DOCUMENT [--task TASK] --pointer /FIELD",
    }
    for key in ("pending", "execution_conflicts"):
        items = value.get(key)
        if isinstance(items, list) and items and isinstance(items[0], dict):
            candidate = items[0].get("id" if key == "pending" else "call")
            if isinstance(candidate, str) and _TASK.fullmatch(candidate):
                summary[key + "_first_call"] = candidate
    for key in ("snapshot", "publish_candidate"):
        item = value.get(key)
        if isinstance(item, dict) and isinstance(item.get("ref"), str) and _REF.fullmatch(item["ref"]):
            summary[key + "_ref"] = item["ref"]
    result = canonical(summary) + b"\n"
    if len(result) > LIMITS.response_bytes:
        raise FairyError("limit", "Document control envelope exceeds the response budget")
    return result


def read_document(
    home: Path,
    ref: str,
    *,
    task: str | None = None,
    pointer: str = "",
    offset: int = 0,
    limit: int = LIMITS.document_read_characters,
) -> dict[str, Any]:
    integer(offset, "document offset")
    integer(limit, "document fragment limit", 1)
    if limit > LIMITS.document_read_characters:
        raise FairyError("limit", "Document fragment limit exceeds the context budget")
    with _documents.select(home, ref, task=task, pointer=pointer) as (node, metadata):
        if offset > node.characters:
            raise FairyError("invalid", "Document offset exceeds the selected value")
        text = node.archive.fragment(node, offset, min(limit, node.characters - offset))
        result = {**metadata, "offset": offset}
        low, high = 0, len(text)
        while low < high:
            count = (low + high + 1) // 2
            result.update(
                text=text[:count],
                next_offset=offset + count if offset + count < node.characters else None,
            )
            if len(canonical(result)) + 1 <= LIMITS.response_bytes:
                low = count
            else:
                high = count - 1
        if low == 0 and offset < node.characters:
            raise FairyError("limit", "Document metadata leaves no fragment capacity")
        result.update(text=text[:low], next_offset=offset + low if offset + low < node.characters else None)
        return result
