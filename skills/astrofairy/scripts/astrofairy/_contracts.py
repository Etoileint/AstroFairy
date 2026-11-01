from __future__ import annotations

import hashlib
import json
import re
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from importlib.resources import files
from itertools import islice
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import unquote, urljoin

from astrofairy._errors import FairyError

if TYPE_CHECKING:
    from jsonschema.protocols import Validator
    from referencing import Registry, Specification

PROTOCOL_VERSION = 7
MODEL_CAPABILITY = "host.model"
EFFECTS = frozenset({"reason", "read", "write"})
MAX_BLOB_BYTES = 16 * 1024 * 1024
MAX_CONTEXT_BYTES = 24 * 1024
DEFAULT_CALL_BUDGET = 16
MAX_QUESTIONS = 3
NAME = re.compile(r"[a-z][a-z0-9_.-]{0,79}\Z")
CAPABILITY_NAME = re.compile(r"[A-Za-z0-9_.-]{1,128}\Z")

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
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
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
    except (ValueError, UnicodeError, RecursionError) as exc:
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


def effect_value(value: Any) -> str:
    if not isinstance(value, str) or value not in EFFECTS:
        raise FairyError("invalid", "Effect must be reason, read or write")
    return value


def effects_value(value: Any) -> list[str]:
    return [effect_value(item) for item in strings(value, "effects")]


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


def task_spec_value(
    request: Any,
    spec: Any = None,
    budget: Any = DEFAULT_CALL_BUDGET,
    effects: Any = None,
) -> dict[str, Any]:
    options = {} if spec is None else object_value(spec)
    if set(options) - {"goal", "criteria", "assumptions"}:
        raise FairyError("invalid", "Unknown start specification field")
    request = text_value(request, "task request")
    default = [
        {
            "id": "goal",
            "description": "Respond to the stated goal with usable content",
            "checker": "semantic",
        },
        {"id": "usable", "description": "Deliver nonempty content", "checker": "nonempty"},
    ]
    result = {
        "request": request,
        "goal": text_value(options.get("goal", request), "goal"),
        "criteria": criteria_value(options.get("criteria", default)),
        "assumptions": strings(options.get("assumptions", []), "assumptions"),
        "budget": integer(budget, "invocation budget", 1),
        "effects": effects_value(sorted(EFFECTS) if effects is None else effects),
    }
    return object_value(parse_json(canonical(result).decode("utf-8")))


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
        "response_bytes": MAX_CONTEXT_BYTES,
        "effects": sorted(EFFECTS),
        "commands": {
            name: {"required": sorted(required), "optional": sorted(optional | {"expected_seq"})}
            for name, (required, optional) in COMMANDS.items()
        },
        "review_verdicts": ["pass", "fail", "unknown"],
        "outcomes": ["complete", "partial", "failed", "cancelled"],
    }


def dependency_issues() -> dict[str, Any]:
    pins = object_value(
        parse_json(files("astrofairy").joinpath("_runtime_dependencies.json").read_text(encoding="utf-8"))
    )
    issues = {}
    for name, required in pins.items():
        try:
            installed = version(name)
        except PackageNotFoundError:
            installed = None
        if installed != required:
            issues[name] = {"required": required, "installed": installed}
    return issues


@cache
def _schema_tools() -> tuple[type[Validator], type[Registry[Any]], Specification[Any], Registry[Any]]:
    issues = dependency_issues()
    if issues:
        raise FairyError(
            "runtime_setup_required",
            "Prepare the locked runtime dependencies in a virtual environment",
            details={"dependencies": issues},
        )
    try:
        import filelock  # noqa: F401, PLC0415 - readiness import probe.
        import jsonpointer  # type: ignore[import-untyped]  # noqa: F401, PLC0415 - readiness import probe.
        from jsonschema import Draft202012Validator  # noqa: PLC0415 - diagnosis must work before dependency imports.
        from jsonschema_specifications import REGISTRY  # type: ignore[import-untyped]  # noqa: PLC0415 - upstream ships no typing marker.
        from referencing import Registry  # noqa: PLC0415
        from referencing.jsonschema import DRAFT202012  # noqa: PLC0415
    except Exception as exc:
        raise FairyError(
            "runtime_setup_required", "Runtime dependency imports failed; recreate the prepared environment"
        ) from exc
    return Draft202012Validator, Registry, DRAFT202012, REGISTRY


def runtime_status() -> dict[str, Any]:
    try:
        _schema_tools()
    except FairyError as exc:
        return {"ready": False, **exc.as_dict()}
    return {"ready": True}


class SchemaContract:
    def __init__(self, schema: dict[str, Any]) -> None:
        validator, registry_type, specification, standards = _schema_tools()
        from jsonschema.exceptions import SchemaError  # noqa: PLC0415
        from referencing.exceptions import Unresolvable  # noqa: PLC0415

        self._bytes = canonical(object_value(schema))
        if len(self._bytes) > MAX_CONTEXT_BYTES:
            raise FairyError("invalid_contract", "Schema exceeds its detail budget")
        body = object_value(parse_json(self._bytes.decode("utf-8")))
        meta = validator.META_SCHEMA
        if body.get("$schema") != meta["$id"] or body.get("type") != "object":
            raise FairyError(
                "invalid_contract", "Tool schemas require explicit 2020-12 dialect and object root"
            )
        if not {"additionalProperties", "unevaluatedProperties"} & body.keys():
            raise FairyError("invalid_contract", "Tool schemas must declare their object openness policy")
        allowed = {key for key, value in meta.get("properties", {}).items() if not value.get("deprecated")}
        for item in meta["allOf"]:
            allowed.update(standards.contents(urljoin(meta["$id"], item["$ref"])).get("properties", {}))
        allowed -= {"$dynamicRef", "$dynamicAnchor"}
        root = specification.create_resource(body)
        pending = [(root, registry_type().resolver_with_root(root))]
        seen = set()
        try:
            while pending:
                resource, resolver = pending.pop()
                node = resource.contents
                key = (id(node), id(resolver.lookup("#").contents))
                if key in seen:
                    continue
                seen.add(key)
                if len(seen) > 4096:
                    raise FairyError("invalid_contract", "Schema reference graph exceeds its analysis budget")
                if isinstance(node, dict):
                    if set(node) - allowed:
                        raise FairyError(
                            "invalid_contract", "Schema contains unsupported or unknown keywords"
                        )
                    if node.get("$schema", meta["$id"]) != meta["$id"]:
                        raise FairyError("invalid_contract", "Nested dialect changes are unsupported")
                    if "$vocabulary" in node and node["$vocabulary"] != meta["$vocabulary"]:
                        raise FairyError("invalid_contract", "Custom vocabularies are unsupported")
                validator.check_schema(node)
                if isinstance(node, dict) and "$ref" in node:
                    if not node["$ref"].startswith("#"):
                        raise FairyError("invalid_contract", "Only local fragment references are supported")
                    fragment = unquote(node["$ref"][1:], errors="strict")
                    if re.search(r"%(?![0-9A-Fa-f]{2})", node["$ref"]):
                        raise FairyError("invalid_contract", "Invalid reference fragment encoding")
                    if fragment.startswith("/"):
                        for token in fragment[1:].split("/"):
                            if re.search(r"~(?![01])", token):
                                raise FairyError("invalid_contract", "Invalid reference token escaping")
                            decoded = token.replace("~1", "/").replace("~0", "~")
                            if re.fullmatch(r"[+-]?\d(?:_?\d)*", decoded.strip()) and not re.fullmatch(
                                r"0|[1-9][0-9]*", decoded
                            ):
                                raise FairyError("invalid_contract", "Noncanonical numeric reference token")
                    target = resolver.lookup(node["$ref"])
                    pending.append((specification.create_resource(target.contents), target.resolver))
                pending.extend((child, resolver.in_subresource(child)) for child in resource.subresources())
        except (SchemaError, Unresolvable, RecursionError, ValueError, TypeError, IndexError) as exc:
            raise FairyError(
                "invalid_contract", "Schema is invalid or contains an unresolved reference"
            ) from exc
        self._validator = validator(body, registry=registry_type())

    @property
    def schema(self) -> dict[str, Any]:
        return object_value(parse_json(self._bytes.decode("utf-8")))

    def validate(self, value: Any) -> None:
        from referencing.exceptions import Unresolvable  # noqa: PLC0415

        try:
            problems = [
                {
                    "rule": error.validator,
                    "schema_pointer": "/"
                    + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in error.schema_path),
                }
                for error in islice(self._validator.iter_errors(value), 4)
            ]
        except (Unresolvable, RecursionError, ValueError, TypeError, IndexError) as exc:
            raise FairyError("invalid_contract", "Declared schema could not be evaluated safely") from exc
        if problems:
            raise FairyError(
                "invalid",
                "Value does not satisfy the declared schema; inspect the tool definition",
                details={"issues": problems},
            )
