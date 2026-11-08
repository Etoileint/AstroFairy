from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import unicodedata
from dataclasses import asdict, dataclass, fields
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from importlib.resources import files
from itertools import islice
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import unquote, urljoin

from astrofairy._errors import FairyError
from astrofairy._limits import LIMITS

if TYPE_CHECKING:
    from collections.abc import Callable

    from jsonschema.protocols import Validator
    from referencing import Registry, Specification

PROTOCOL_VERSION = 11
STAGE_PACKET_VERSION = 2
RECEIPT_PROJECTION_FORMAT = 2
MODEL_CAPABILITY = "host.model"
EFFECTS = frozenset({"reason", "read", "write"})
MAX_BLOB_BYTES = LIMITS.blob_bytes
MAX_CONTENT_BYTES = LIMITS.content_bytes
MAX_TASK_CAPTURE_BYTES = LIMITS.task_capture_bytes
STREAM_CHUNK_BYTES = LIMITS.stream_chunk_bytes
MAX_CONTEXT_BYTES = LIMITS.response_bytes
MAX_PATH_BYTES = LIMITS.path_bytes
MAX_PATH_SEGMENT_BYTES = LIMITS.path_segment_bytes
MAX_MEDIA_TYPE_BYTES = LIMITS.media_type_bytes
NAME = re.compile(rf"[a-z][a-z0-9_.-]{{0,{LIMITS.machine_id_chars - 1}}}\Z")
CONTENT_REF = re.compile(r"[a-f0-9]{64}\Z")
CAPABILITY_NAME = re.compile(rf"[A-Za-z0-9_.-]{{1,{LIMITS.capability_name_chars}}}\Z")
SCOPES = frozenset({"content", "member", "collection"})

# This table is both the parser's field authority and the schema command's source.
COMMANDS: dict[str, tuple[set[str], set[str]]] = {
    "revise": (
        {"goal", "criteria", "reason"},
        {"assumptions", "user_basis", "required_roles", "governance", "governance_scope"},
    ),
    "request": ({"purpose"}, {"refs"}),
    "report": ({"call", "text"}, {"path", "media_type"}),
    "invoke": ({"capability", "parameters"}, set()),
    "publish": ({"members"}, set()),
    "review": ({"criterion", "verdict", "basis"}, {"target", "revision", "replaces", "evidence"}),
    "check": (set(), {"criterion"}),
    "ask": ({"question", "recommendation"}, {"options"}),
    "answer": ({"text"}, set()),
    "feedback": ({"text"}, {"kind"}),
    "close": ({"outcome"}, {"note"}),
    "learn": (set(), {"decision", "note", "basis"}),
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


def text_value(value: Any, label: str, limit: int = LIMITS.text_field_bytes) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > limit:
        raise FairyError("invalid", f"Invalid {label}")
    return value


def _pathvalidate() -> tuple[Callable[..., None], type[ValueError]]:
    try:
        from pathvalidate import ValidationError, validate_filename  # noqa: PLC0415 - readiness must work before imports.
    except Exception as exc:
        raise FairyError("runtime_setup_required", "Prepare the locked path validation dependency") from exc
    return validate_filename, ValidationError


def relative_path(value: Any, label: str = "member path") -> str:
    if not isinstance(value, str) or not value:
        raise FairyError("invalid", f"Invalid {label}")
    try:
        encoded = value.encode("utf-8")
    except UnicodeError as exc:
        raise FairyError("invalid", f"Invalid {label} encoding") from exc
    if len(encoded) > MAX_PATH_BYTES:
        raise FairyError("limit", f"{label} exceeds its byte budget")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise FairyError("invalid", f"{label} contains control characters")
    if value != unicodedata.normalize("NFC", value):
        raise FairyError(
            "invalid",
            f"{label} is not NFC; use the normalized form",
            details={"suggested": unicodedata.normalize("NFC", value)},
        )
    if value.startswith("/") or value.endswith("/") or "\\" in value:
        raise FairyError("invalid", f"{label} must be a canonical relative path")
    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise FairyError("invalid", f"{label} contains an empty or traversal segment")
    validate_filename, validation_error = _pathvalidate()
    for segment in segments:
        if len(segment.encode("utf-8")) > MAX_PATH_SEGMENT_BYTES:
            raise FairyError("limit", f"{label} segment exceeds its byte budget")
        try:
            validate_filename(segment, platform="universal")
        except validation_error as exc:
            raise FairyError(
                "invalid",
                f"{label} contains a non-portable segment",
                details={"segment": segment, "reason": str(exc)},
            ) from exc
        except (TypeError, ValueError) as exc:
            raise FairyError("invalid", f"{label} contains a non-portable segment") from exc
    return value


def content_ref(value: Any, label: str = "content reference") -> str:
    if not isinstance(value, str) or not CONTENT_REF.fullmatch(value):
        raise FairyError("invalid", f"Invalid {label}")
    return value


def media_type_value(value: Any) -> str:
    media_type = text_value(value, "media type", MAX_MEDIA_TYPE_BYTES)
    if any(ord(char) < 32 or ord(char) == 127 for char in media_type):
        raise FairyError("invalid", "Media type contains control characters")
    return media_type


def role_value(value: Any) -> str:
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise FairyError("invalid", "Member role must be a stable machine id")
    return value


def output_value(value: Any) -> dict[str, Any]:
    output = object_value(value)
    if set(output) != {"ref", "path", "media_type"}:
        raise FairyError("invalid", "Output descriptors need ref, path and media_type")
    return {
        "ref": content_ref(output["ref"], "output reference"),
        "path": relative_path(output["path"], "output path"),
        "media_type": media_type_value(output["media_type"]),
    }


def outputs_value(value: Any, *, allow_empty: bool = True) -> list[dict[str, Any]]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise FairyError("invalid", "Invalid output list")
    result = [output_value(item) for item in value]
    _require_portable_set([item["path"] for item in result])
    return result


def member_value(value: Any) -> dict[str, Any]:
    member = object_value(value)
    if set(member) != {"ref", "path", "bytes", "media_type", "role"}:
        raise FairyError("invalid", "Members need ref, path, bytes, media_type and role")
    return {
        "ref": content_ref(member["ref"], "member reference"),
        "path": relative_path(member["path"]),
        "bytes": integer(member["bytes"], "member byte count"),
        "media_type": media_type_value(member["media_type"]),
        "role": role_value(member["role"]),
    }


def _require_portable_set(paths: list[str]) -> None:
    folded = [path.casefold() for path in paths]
    if len(set(folded)) != len(folded):
        raise FairyError("invalid", "Member paths collide on a case-insensitive filesystem")
    known = set(folded)
    for path in paths:
        parts = path.split("/")
        for index in range(1, len(parts)):
            if "/".join(parts[:index]).casefold() in known:
                raise FairyError("invalid", "Member paths contain a file/directory conflict")


def delivery_plan_value(value: Any) -> dict[str, Any]:
    definition = object_value(value)
    if set(definition) != {"members"}:
        raise FairyError("invalid", "A delivery plan needs exactly a members list")
    raw = definition["members"]
    if not isinstance(raw, list) or not raw:
        raise FairyError("invalid", "A delivery plan needs at least one member")
    members = []
    paths = set()
    for item in raw:
        entry = object_value(item)
        if set(entry) - {"path", "role", "media_type"}:
            raise FairyError("invalid", "Unknown delivery plan member field")
        path = relative_path(text_value(entry.get("path"), "member path"))
        role = role_value(entry.get("role"))
        if path in paths:
            raise FairyError("invalid", "Delivery plan member paths must be unique")
        paths.add(path)
        media_type = media_type_value(
            entry.get("media_type", mimetypes.guess_type(path)[0] or "application/octet-stream")
        )
        members.append({"path": path, "role": role, "media_type": media_type})
    _require_portable_set([item["path"] for item in members])
    return {"format": 1, "members": members}


def members_value(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise FairyError("invalid", "A published snapshot needs at least one member")
    result = [member_value(item) for item in value]
    if len({item["path"] for item in result}) != len(result):
        raise FairyError("invalid", "Member paths must be unique")
    _require_portable_set([item["path"] for item in result])
    return sorted(result, key=lambda item: item["path"])


def snapshot_value(value: Any) -> dict[str, Any]:
    members = members_value(value)
    body = {"format": 1, "members": members}
    return {**body, "ref": digest(canonical(body))}


def required_roles_value(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise FairyError("invalid", "Invalid required role list")
    roles = [role_value(item) for item in value]
    if len(set(roles)) != len(roles):
        raise FairyError("invalid", "Required roles must be unique")
    return roles


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


@dataclass(frozen=True)
class ResourcePolicy:
    work_calls: int = LIMITS.work_call_limit
    warning_calls: int = LIMITS.work_call_warning

    def __post_init__(self) -> None:
        integer(self.work_calls, "work call limit", 1)
        integer(self.warning_calls, "work call warning", 1)
        if self.warning_calls > self.work_calls:
            raise FairyError("invalid", "Work call warning must not exceed the final limit")

    def snapshot(self) -> dict[str, Any]:
        policy = {"format": 1, **asdict(self)}
        return {"policy": policy, "fingerprint": digest(canonical(policy))}

    @classmethod
    def parse(cls, value: Any) -> ResourcePolicy:
        options = object_value(value)
        if set(options) - {item.name for item in fields(cls)}:
            raise FairyError("invalid", "Unknown resource policy field")
        defaults = cls()
        limit = integer(options.get("work_calls", defaults.work_calls), "work call limit", 1)
        warning = options.get("warning_calls", min(defaults.warning_calls, limit))
        return cls(limit, integer(warning, "work call warning", 1))

    @classmethod
    def restore(cls, value: Any) -> ResourcePolicy:
        snapshot = object_value(value)
        if set(snapshot) != {"policy", "fingerprint"}:
            raise FairyError("integrity", "Invalid recorded resource policy")
        policy = object_value(snapshot["policy"])
        if type(policy.get("format")) is not int or policy["format"] != 1:
            raise FairyError("version", "Unsupported resource policy format")
        if set(policy) != {"format", *(item.name for item in fields(cls))}:
            raise FairyError("integrity", "Incomplete recorded resource policy")
        result = cls.parse({key: item for key, item in policy.items() if key != "format"})
        if canonical(result.snapshot()) != canonical(snapshot):
            raise FairyError("integrity", "Recorded resource policy fingerprint does not match")
        return result


def _criterion_target(scope: str, value: Any) -> Any:
    if value is None:
        return None
    if scope == "content":
        if isinstance(value, str):
            return content_ref(value, "criterion content target")
        if isinstance(value, list) and value:
            return sorted({content_ref(item, "criterion content target") for item in value})
        raise FairyError("invalid", "Content criterion targets must be references")
    if scope == "member":
        return relative_path(value, "criterion member target")
    if not isinstance(value, list) or not value:
        raise FairyError("invalid", "Collection criterion targets must be member paths")
    paths = [relative_path(item, "criterion member target") for item in value]
    if len(set(paths)) != len(paths):
        raise FairyError("invalid", "Collection criterion targets must be unique")
    _require_portable_set(paths)
    return sorted(paths)


def criterion_fingerprint(criterion: dict[str, Any]) -> str:
    return digest(canonical(criterion))


def criteria_value(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise FairyError("invalid", "At least one criterion is required")
    result = []
    identities: set[str] = set()
    for item in value:
        criterion = object_value(item)
        allowed = {
            "id",
            "description",
            "checker",
            "parameters",
            "origin",
            "required",
            "basis",
            "scope",
            "target",
        }
        if set(criterion) - allowed:
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
        checker = text_value(criterion.get("checker", "semantic"), "checker")
        scope = criterion.get("scope", "collection" if checker == "semantic" else "content")
        if not isinstance(scope, str) or scope not in SCOPES:
            raise FairyError("invalid", "Invalid criterion scope")
        result.append(
            {
                "id": identity,
                "description": text_value(criterion.get("description"), "criterion description"),
                "checker": checker,
                "parameters": object_value(criterion.get("parameters", {})),
                "origin": origin,
                "required": required,
                "basis": text_value(
                    criterion.get("basis", "Provisional interpretation of the task request"),
                    "criterion basis",
                ),
                "scope": scope,
                "target": _criterion_target(scope, criterion.get("target")),
            }
        )
    if not any(item["required"] for item in result):
        raise FairyError("invalid", "At least one necessary criterion is required")
    return result


def task_spec_value(
    request: Any,
    spec: Any = None,
    resources: ResourcePolicy | None = None,
    effects: Any = None,
) -> dict[str, Any]:
    if resources is not None and not isinstance(resources, ResourcePolicy):
        raise FairyError("invalid", "Resources must be a validated ResourcePolicy")
    options = {} if spec is None else object_value(spec)
    if set(options) - {
        "goal",
        "criteria",
        "assumptions",
        "required_roles",
        "governance",
        "governance_scope",
    }:
        raise FairyError("invalid", "Unknown start specification field")
    request = text_value(request, "task request")
    default = [
        {
            "id": "goal",
            "description": "Respond to the stated goal with usable content",
            "checker": "semantic",
            "scope": "collection",
        },
        {
            "id": "usable",
            "description": "Deliver nonempty content",
            "checker": "nonempty",
            "scope": "collection",
        },
    ]
    governance_scopes = options.get("governance_scope", [])
    if not isinstance(governance_scopes, list) or any(
        not isinstance(scope, str) or scope not in {"personal", "team"} for scope in governance_scopes
    ):
        raise FairyError("invalid", "Governance scope must be personal or team")
    result = {
        "request": request,
        "goal": text_value(options.get("goal", request), "goal"),
        "criteria": criteria_value(options.get("criteria", default)),
        "assumptions": strings(options.get("assumptions", []), "assumptions"),
        "required_roles": required_roles_value(options.get("required_roles", [])),
        "governance": [
            content_ref(item, "governance asset reference") for item in options.get("governance", [])
        ],
        "governance_scope": governance_scopes,
        "provisional": "criteria" not in options,
        "resources": (ResourcePolicy() if resources is None else resources).snapshot(),
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
        "stage_packet_version": STAGE_PACKET_VERSION,
        "receipt_projection_format": RECEIPT_PROJECTION_FORMAT,
        "response_bytes": LIMITS.response_bytes,
        "resource_limits": LIMITS.manifest(),
        "resource_policy": {
            "defaults": ResourcePolicy().snapshot(),
            "fields": [item.name for item in fields(ResourcePolicy)],
            "units": "registered work invocations; not tokens, currency or elapsed time",
            "configuration": "start --resources FILE; fixed at task creation",
        },
        "snapshot_format": 1,
        "scopes": sorted(SCOPES),
        "member_path": {
            "max_bytes": MAX_PATH_BYTES,
            "max_segment_bytes": MAX_PATH_SEGMENT_BYTES,
            "encoding": "NFC",
            "separator": "/",
        },
        "effects": sorted(EFFECTS),
        "commands": {
            name: {"required": sorted(required), "optional": sorted(optional | {"expected_seq"})}
            for name, (required, optional) in COMMANDS.items()
        },
        "review_verdicts": ["pass", "fail", "unknown"],
        "outcomes": ["complete", "partial", "failed", "cancelled"],
    }


@cache
def dependency_manifest() -> dict[str, Any]:
    manifest = object_value(
        parse_json(files("astrofairy").joinpath("_dependency_manifest.json").read_text(encoding="utf-8"))
    )
    if manifest.get("format") != 2:
        raise FairyError("integrity", "Unsupported dependency manifest format")
    object_value(manifest.get("profiles"))
    return manifest


def _profile_requirements(profile: str) -> list[dict[str, Any]]:
    profiles = object_value(dependency_manifest()["profiles"])
    entry = profiles.get(profile)
    if not isinstance(entry, dict):
        raise FairyError("invalid", "Unknown dependency profile")
    requirements = entry.get("requirements")
    if not isinstance(requirements, list):
        raise FairyError("integrity", "Dependency profile has no requirement list")
    return [object_value(item) for item in requirements]


def _active_requirements(profile: str) -> list[dict[str, Any]]:
    requirements = _profile_requirements(profile)
    try:
        from packaging.markers import Marker  # noqa: PLC0415 - readiness must work before dependency imports.
    except ImportError:
        return requirements
    active = []
    for item in requirements:
        marker = item.get("marker")
        if marker is None or Marker(str(marker)).evaluate():
            active.append(item)
    return active


def dependency_observations(profile: str = "core") -> list[dict[str, Any]]:
    observations = []
    for item in _active_requirements(profile):
        name = str(item["name"])
        try:
            installed = version(name)
        except PackageNotFoundError:
            installed = None
        observations.append(
            {
                "name": name,
                "required": str(item["version"]),
                "installed": installed,
                "marker": item.get("marker"),
            }
        )
    return sorted(observations, key=lambda item: item["name"])


def dependency_issues(profile: str = "core") -> dict[str, Any]:
    return {
        item["name"]: {"required": item["required"], "installed": item["installed"]}
        for item in dependency_observations(profile)
        if item["installed"] != item["required"]
    }


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
        if len(self._bytes) > LIMITS.schema_bytes:
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
                if len(seen) > LIMITS.schema_states:
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
