from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from astrofairy._contracts import (
    NAME,
    canonical,
    content_ref,
    criteria_value,
    criterion_fingerprint,
    digest,
    object_value,
    parse_json,
    strings,
    text_value,
)
from astrofairy._errors import FairyError
from astrofairy._kernel import replay
from astrofairy._limits import LIMITS
from astrofairy._search import SearchIndex

ASSET_STATES = frozenset({"candidate", "trial", "stable", "retired"})

if TYPE_CHECKING:
    from astrofairy._store import Store

KINDS = {"workflow", "guide", "profile", "case", "constraint", "tool-spec"}
MAX_SEARCH_RESULTS = LIMITS.search_max_results


def validation_criteria(candidate_ref: str | None = None) -> list[dict[str, Any]]:
    return criteria_value(
        [
            {
                "id": "package-json",
                "description": "Package parses as strict JSON",
                "checker": "json",
                "origin": "policy",
                "basis": "Workshop asset adoption policy",
                "scope": "content",
                "target": candidate_ref,
            },
            {
                "id": "asset-fitness",
                "description": (
                    "Evidence supports the claimed benefit and scope; instructions, inputs, "
                    "dependencies and completion conditions are usable"
                ),
                "checker": "semantic",
                "origin": "policy",
                "basis": "Workshop asset adoption policy",
                "scope": "member",
                "target": "candidate.json",
            },
        ]
    )


class Library:
    def __init__(self, store: Store, search: Any | None = None) -> None:
        self.store = store
        self.search_index: Any = SearchIndex(store) if search is None else search

    def status(self, ref: str) -> str:
        row = self.store.connection.execute(
            "SELECT status FROM asset_events WHERE ref = ? ORDER BY seq DESC LIMIT 1", (ref,)
        ).fetchone()
        if row is None:
            raise FairyError("missing", "Unknown asset")
        return str(row[0])

    def head(self, scope: str, name: str) -> str | None:
        row = self.store.connection.execute(
            "SELECT a.ref FROM assets a JOIN asset_events e ON e.ref = a.ref "
            "WHERE a.scope = ? AND a.name = ? AND e.status IN ('trial', 'stable') "
            "AND e.seq = (SELECT MAX(x.seq) FROM asset_events x WHERE x.ref = a.ref) "
            "ORDER BY e.seq DESC LIMIT 1",
            (scope, name),
        ).fetchone()
        return str(row[0]) if row else None

    def get(self, ref: str) -> dict[str, Any]:
        row = self.store.connection.execute("SELECT ref FROM assets WHERE ref = ?", (ref,)).fetchone()
        if row is None:
            raise FairyError("missing", "Unknown asset")
        return object_value(parse_json(self.store.get(ref).decode("utf-8")))

    def governance(self, scope: str | None = None, kind: str | None = "constraint") -> list[dict[str, Any]]:
        if scope is not None and scope not in {"personal", "team"}:
            raise FairyError("invalid", "Governance scope must be personal or team")
        if kind is not None and kind not in KINDS:
            raise FairyError("invalid", "Unknown governance kind")
        rows = self.store.connection.execute(
            "WITH active AS ("
            " SELECT a.ref, a.scope, a.name, a.kind, a.summary,"
            " e.seq AS adoption, e.status"
            " FROM assets a JOIN asset_events e ON e.ref = a.ref"
            " WHERE e.status IN ('trial', 'stable')"
            " AND e.seq = (SELECT MAX(x.seq) FROM asset_events x WHERE x.ref = a.ref)),"
            " ranked AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY scope, name"
            " ORDER BY adoption DESC) AS rank FROM active)"
            " SELECT ref, scope, name, kind, summary FROM ranked WHERE rank = 1"
        ).fetchall()
        result = []
        for row in rows:
            if scope is not None and row["scope"] != scope:
                continue
            if kind is not None and row["kind"] != kind:
                continue
            package = object_value(parse_json(self.store.get(row["ref"]).decode("utf-8")))
            result.append(
                {
                    "ref": row["ref"],
                    "scope": row["scope"],
                    "name": row["name"],
                    "kind": row["kind"],
                    "summary": row["summary"],
                    "applicability": package.get("applicability"),
                    "dependencies": package.get("dependencies"),
                    "invalidation": package.get("invalidation"),
                    "requires_host_judgment": not bool(package.get("applicability")),
                }
            )
        return sorted(result, key=lambda item: (item["scope"], item["name"]))

    def propose(self, value: dict[str, Any]) -> str:
        required = {"name", "scope", "kind", "summary", "tags", "content", "evidence"}
        optional = {"applicability", "dependencies", "invalidation"}
        if set(value) - required - optional or required - set(value):
            raise FairyError("invalid", "Asset fields must match the proposal contract")
        normalized = {key: value[key] for key in required}
        if "applicability" in value:
            applicability = object_value(value["applicability"])
            if set(applicability) - {"use_when", "avoid_when"}:
                raise FairyError("invalid", "Unknown applicability field")
            normalized["applicability"] = {
                key: strings(applicability.get(key, []), f"applicability {key}")
                for key in ("use_when", "avoid_when")
                if applicability.get(key, [])
            }
            if not normalized["applicability"]:
                raise FairyError("invalid", "Applicability needs at least one condition")
        for key in ("dependencies", "invalidation"):
            if key in value:
                normalized[key] = strings(value[key], f"asset {key}")
        value = normalized
        name = text_value(value["name"], "asset name")
        scope = text_value(value["scope"], "asset scope")
        kind = text_value(value["kind"], "asset kind")
        if not NAME.fullmatch(name) or scope not in {"personal", "team"} or kind not in KINDS:
            raise FairyError("invalid", "Invalid asset identity, scope or kind")
        summary = text_value(value["summary"], "asset summary", LIMITS.asset_summary_bytes)
        tags = strings(value["tags"], "asset tags")
        if not isinstance(value["evidence"], list) or not value["evidence"]:
            raise FairyError("invalid", "An asset needs provenance evidence")
        for evidence in value["evidence"]:
            item = object_value(evidence)
            if set(item) != {"source", "note"}:
                raise FairyError("invalid", "Evidence needs source and note")
            text_value(item["source"], "evidence source")
            text_value(item["note"], "evidence note")
        if value["kind"] == "workflow":
            workflow = object_value(value["content"])
            steps = workflow.get("steps")
            if not isinstance(steps, list) or not steps:
                raise FairyError("invalid", "A workflow needs steps")
            for step in steps:
                entry = object_value(step)
                text_value(entry.get("instruction"), "workflow instruction")
                text_value(entry.get("done"), "workflow completion condition")
        else:
            text_value(value["content"], "asset content", LIMITS.asset_content_bytes)
        with self.store.transaction():
            row = self.store.connection.execute(
                "SELECT MAX(version) FROM assets WHERE scope = ? AND name = ?", (value["scope"], name)
            ).fetchone()
            version = (row[0] or 0) + 1
            base = self.head(value["scope"], name)
            package = {**value, "version": version, "base": base, "format": 1}
            ref = self.store.put(canonical(package))
            self.store.connection.execute(
                "INSERT INTO assets VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ref,
                    value["scope"],
                    name,
                    version,
                    value["kind"],
                    summary,
                    canonical(tags).decode("utf-8"),
                    base,
                ),
            )
            self._event(ref, "candidate", None)
        return ref

    def _event(self, ref: str, status: str, task: str | None) -> None:
        self.store.connection.execute(
            "INSERT INTO asset_events(ref, status, validation_task, created) "
            "VALUES (?, ?, ?, datetime('now'))",
            (ref, status, task),
        )

    def adopt(self, ref: str, task: str, status: str = "trial") -> None:
        if status not in {"trial", "stable"}:
            raise FairyError("invalid", "Adoption status must be trial or stable")
        content_ref(ref, "candidate reference")
        with self.store.transaction():
            package = self.get(ref)
            state = replay(task, self.store.events(task))
            from astrofairy._capabilities import builtins  # noqa: PLC0415 - avoid a module cycle.

            capabilities = builtins()
            state.checker_contracts = {
                name: digest(canonical(capabilities[name].definition(name)))
                for name in ("content.check", "snapshot.check")
            }
            if state.outcome != "complete" or not state.complete() or state.snapshot is None:
                raise FairyError("not_ready", "Adoption requires completed validation of this exact package")
            candidate = next(
                (
                    member
                    for member in state.snapshot["members"]
                    if member["path"] == "candidate.json" and member["ref"] == ref
                ),
                None,
            )
            if candidate is None or candidate["role"] != "candidate":
                raise FairyError(
                    "not_ready", "The validated snapshot must contain the exact candidate member"
                )
            if "candidate" not in state.spec.get("required_roles", []):
                raise FairyError("not_ready", "Validation must retain the candidate delivery role")
            required = validation_criteria(ref)
            actual = {item["id"]: item for item in state.spec["criteria"]}
            if any(actual.get(item["id"]) != item for item in required):
                raise FairyError("not_ready", "Validation must retain the required adoption policy unchanged")
            active = state.active_reviews()
            for criterion in required:
                matches = [
                    review
                    for review in active
                    if review["criterion"] == criterion["id"]
                    and review["criterion_fingerprint"] == criterion_fingerprint(criterion)
                    and review["verdict"] == "pass"
                    and (
                        review["target"] == {"scope": "content", "ref": ref}
                        if criterion["id"] == "package-json"
                        else review["target"] == {"scope": "member", "member": candidate}
                    )
                ]
                if not matches:
                    raise FairyError(
                        "not_ready", "Policy checks must bind the exact candidate content and member"
                    )
            policy_ids = {item["id"] for item in required}
            if any(
                failure["criterion"] in policy_ids and failure["criterion_required"]
                for failure in state.unresolved_failures()
            ):
                raise FairyError("not_ready", "Policy failures remain unresolved for this candidate")
            head = self.head(package["scope"], package["name"])
            if head != package["base"] and head != ref:
                raise FairyError("conflict", "Asset base changed; rebase and validate the new candidate")
            self._event(ref, status, task)

    def retire(self, ref: str) -> None:
        with self.store.transaction():
            self.get(ref)
            self._event(ref, "retired", None)

    def search_page(
        self,
        query: str,
        limit: int = LIMITS.search_default_limit,
        scope: str | None = None,
        kind: str | None = None,
        cursor: str | None = None,
        *,
        refresh: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(query, str):
            raise FairyError("invalid", "Asset search query must be text")
        if type(limit) is not int or not 1 <= limit <= MAX_SEARCH_RESULTS:
            raise FairyError("limit", f"Asset search limit must be between 1 and {MAX_SEARCH_RESULTS}")
        if scope is not None and scope not in {"personal", "team"}:
            raise FairyError("invalid", "Asset search scope must be personal or team")
        if kind is not None and kind not in KINDS:
            raise FairyError("invalid", "Unknown asset kind")
        if cursor is not None and refresh:
            raise FairyError("invalid", "A cursor cannot be combined with an explicit refresh")
        return cast(
            "dict[str, Any]",
            self.search_index.page(
                query,
                limit=limit,
                scope=scope,
                kind=kind,
                cursor=cursor,
                refresh=refresh,
            ),
        )

    def search(
        self,
        query: str,
        limit: int = LIMITS.search_default_limit,
        scope: str | None = None,
        kind: str | None = None,
        *,
        refresh: bool = False,
    ) -> list[dict[str, Any]]:
        return cast(
            "list[dict[str, Any]]",
            self.search_page(query, limit, scope, kind, refresh=refresh)["matches"],
        )

    def export(self, ref: str) -> bytes:
        return canonical({"format": 1, "ref": ref, "package": self.get(ref)})

    def import_bundle(self, data: bytes) -> str:
        bundle = object_value(parse_json(data.decode("utf-8")))
        if set(bundle) != {"format", "ref", "package"} or bundle["format"] != 1:
            raise FairyError("invalid", "Invalid asset bundle")
        package = object_value(bundle["package"])
        if digest(canonical(package)) != bundle["ref"]:
            raise FairyError("integrity", "Bundle digest does not match")
        if package.get("format") != 1:
            raise FairyError("version", "Unsupported asset format")
        proposal = {key: package[key] for key in ("name", "scope", "kind", "summary", "tags", "content")}
        for key in ("applicability", "dependencies", "invalidation"):
            if key in package:
                proposal[key] = package[key]
        proposal["evidence"] = [
            {"source": "bundle:" + str(bundle["ref"]), "note": "Imported; validate locally before use"}
        ]
        evidence = package.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise FairyError("invalid", "Imported package lacks provenance notes")
        for index, item in enumerate(evidence):
            declared = object_value(item)
            proposal["evidence"].append(
                {
                    "source": "bundle:" + str(bundle["ref"]) + "#evidence/" + str(index),
                    "note": text_value(declared.get("note"), "sender-declared evidence"),
                }
            )
        return self.propose(proposal)
