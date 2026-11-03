from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from astrofairy._contracts import canonical, digest, object_value
from astrofairy._errors import FairyError

_CURSOR_BYTES = 4096


def encode_cursor(value: dict[str, Any]) -> str:
    body = canonical(value)
    envelope = canonical({"body": value, "check": digest(body)[:16]})
    return base64.urlsafe_b64encode(envelope).decode("ascii").rstrip("=")


def decode_cursor(value: Any) -> dict[str, Any]:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > _CURSOR_BYTES:
        raise FairyError("invalid", "Invalid pagination cursor")
    try:
        padded = value + "=" * (-len(value) % 4)
        envelope = object_value(json.loads(base64.urlsafe_b64decode(padded).decode("utf-8")))
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise FairyError("invalid", "Invalid pagination cursor") from exc
    if set(envelope) != {"body", "check"}:
        raise FairyError("invalid", "Invalid pagination cursor")
    body = object_value(envelope["body"])
    if envelope["check"] != digest(canonical(body))[:16]:
        raise FairyError("integrity", "Pagination cursor does not match its contents")
    return body


def offset_cursor(value: Any, *, fields: dict[str, Any]) -> int:
    cursor = decode_cursor(value)
    if set(cursor) != {"offset", *fields}:
        raise FairyError("invalid", "Pagination cursor does not match this query")
    offset = cursor["offset"]
    if type(offset) is not int or offset < 0:
        raise FairyError("invalid", "Invalid pagination offset")
    if any(cursor[key] != item for key, item in fields.items()):
        raise FairyError("conflict", "Search parameters changed; restart from the first page")
    return offset
