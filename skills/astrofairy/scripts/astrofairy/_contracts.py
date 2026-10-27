from __future__ import annotations

import hashlib
import json
import re
from typing import Any, cast

from astrofairy._errors import FairyError

PROTOCOL_VERSION = 1
MAX_BLOB_BYTES = 16 * 1024 * 1024
MAX_CONTEXT_BYTES = 24 * 1024
DEFAULT_CALL_BUDGET = 16
MAX_QUESTIONS = 3
NAME = re.compile(r"[a-z][a-z0-9_.-]{0,79}\Z")

# This table is both the parser's field authority and the schema command's source.
COMMANDS: dict[str, tuple[set[str], set[str]]] = {
    "revise": ({"goal", "criteria", "reason"}, {"assumptions", "user_basis"}),
    "request": ({"purpose"}, {"refs"}),
    "report": ({"call", "text"}, {"name", "media_type"}),
    "invoke": ({"capability", "parameters"}, set()),
    "publish": ({"ref"}, set()),
    "review": ({"criterion", "verdict", "basis"}, {"ref", "revision", "replaces", "evidence"}),
    "check": (set(), {"criterion"}),
    "ask": ({"question", "recommendation"}, {"options"}),
    "answer": ({"text"}, set()),
    "feedback": ({"text"}, {"kind"}),
    "close": ({"outcome"}, {"note"}),
    "learn": (set(), set()),
}


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise FairyError("invalid", "Value is not canonical UTF-8 JSON") from exc


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FairyError("invalid", "Duplicate JSON key")
        result[key] = value
    return result


def parse_json(text: str) -> Any:
    try:
        value = json.loads(text, object_pairs_hook=_pairs)
        canonical(value)
        return value
    except (ValueError, UnicodeError) as exc:
        raise FairyError("invalid", "Invalid JSON") from exc


def object_value(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise FairyError("invalid", "Expected a JSON object")
    return cast("dict[str, Any]", value)


def text_value(value: Any, label: str, limit: int = MAX_CONTEXT_BYTES) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > limit:
        raise FairyError("invalid", f"Invalid {label}")
    return value


def file_name(value: Any) -> str:
    name = text_value(value, "output file name", 200)
    if name in {".", "..", "receipt.json"} or any(char in "/\\" or ord(char) < 32 for char in name):
        raise FairyError("invalid", "Output name must be a single usable file name")
    return name


def strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise FairyError("invalid", f"Invalid {label}")
    return [text_value(item, label) for item in value]


def integer(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise FairyError("invalid", f"Invalid {label}")
    return value


def criteria_value(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise FairyError("invalid", "At least one criterion is required")
    result = []
    identities: set[str] = set()
    for item in value:
        criterion = object_value(item)
        if set(criterion) - {"id", "description", "checker", "parameters", "origin", "required", "basis"}:
            raise FairyError("invalid", "Unknown criterion field")
        identity = text_value(criterion.get("id"), "criterion id")
        if not NAME.fullmatch(identity) or identity in identities:
            raise FairyError("invalid", "Criterion ids must be valid and unique")
        identities.add(identity)
        required = criterion.get("required", True)
        if type(required) is not bool:
            raise FairyError("invalid", "Criterion required must be boolean")
        origin = criterion.get("origin", "derived")
        if not isinstance(origin, str) or origin not in {"user", "policy", "derived"}:
            raise FairyError("invalid", "Invalid criterion origin")
        result.append(
            {
                "id": identity,
                "description": text_value(criterion.get("description"), "criterion description"),
                "checker": text_value(criterion.get("checker", "semantic"), "checker"),
                "parameters": object_value(criterion.get("parameters", {})),
                "origin": origin,
                "required": required,
                "basis": text_value(
                    criterion.get("basis", "Provisional interpretation of the task request"),
                    "criterion basis",
                ),
            }
        )
    if not any(item["required"] for item in result):
        raise FairyError("invalid", "At least one necessary criterion is required")
    return result


def command_value(value: Any) -> dict[str, Any]:
    command = object_value(value)
    operation = command.get("op")
    if not isinstance(operation, str) or operation not in COMMANDS:
        raise FairyError("invalid", "Unknown command")
    required, optional = COMMANDS[operation]
    fields = set(command) - {"op", "expected_seq"}
    if not required <= fields or fields - required - optional:
        raise FairyError("invalid", "Missing or unknown command fields")
    if "expected_seq" in command:
        integer(command["expected_seq"], "expected sequence")
    canonical(command)
    return command


def schema() -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "commands": {
            name: {"required": sorted(required), "optional": sorted(optional | {"expected_seq"})}
            for name, (required, optional) in COMMANDS.items()
        },
        "review_verdicts": ["pass", "fail", "unknown"],
        "outcomes": ["complete", "partial", "failed", "cancelled"],
    }
