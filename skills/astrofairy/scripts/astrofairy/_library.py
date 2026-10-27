from __future__ import annotations

from typing import TYPE_CHECKING, Any

from astrofairy._contracts import (
    NAME,
    canonical,
    criteria_value,
    digest,
    object_value,
    parse_json,
    strings,
    text_value,
)
from astrofairy._errors import FairyError
from astrofairy._kernel import replay

if TYPE_CHECKING:
    from astrofairy._store import Store

KINDS = {"workflow", "guide", "profile", "case", "constraint", "tool-spec"}


def validation_criteria() -> list[dict[str, Any]]:
    return criteria_value(
        [
            {
                "id": "package-json",
                "description": "Package parses as strict JSON",
                "checker": "json",
                "origin": "policy",
                "basis": "Workshop asset adoption policy",
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
            },
        ]
    )


class Library:
    def __init__(self, store: Store) -> None:
        self.store = store

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

    def propose(self, value: dict[str, Any]) -> str:
        allowed = {"name", "scope", "kind", "summary", "tags", "content", "evidence"}
        if set(value) != allowed:
            raise FairyError("invalid", "Asset fields must match the proposal contract")
        name = text_value(value["name"], "asset name")
        scope = text_value(value["scope"], "asset scope")
        kind = text_value(value["kind"], "asset kind")
        if not NAME.fullmatch(name) or scope not in {"personal", "team"} or kind not in KINDS:
            raise FairyError("invalid", "Invalid asset identity, scope or kind")
        summary = text_value(value["summary"], "asset summary", 1000)
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
            text_value(value["content"], "asset content", 1024 * 1024)
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
        with self.store.transaction():
            package = self.get(ref)
            state = replay(task, self.store.events(task))
            if (
                state.outcome != "complete"
                or not state.complete()
                or not state.artifact
                or state.artifact["ref"] != ref
            ):
                raise FairyError("not_ready", "Adoption requires completed validation of this exact package")
            actual = {item["id"]: item for item in state.spec["criteria"]}
            if any(actual.get(item["id"]) != item for item in validation_criteria()):
                raise FairyError("not_ready", "Validation must retain the required adoption policy unchanged")
            head = self.head(package["scope"], package["name"])
            if head != package["base"] and head != ref:
                raise FairyError("conflict", "Asset base changed; rebase and validate the new candidate")
            self._event(ref, status, task)

    def retire(self, ref: str) -> None:
        with self.store.transaction():
            self.get(ref)
            self._event(ref, "retired", None)

    def search(self, query: str, limit: int = 3, scope: str | None = None) -> list[dict[str, Any]]:
        if not 1 <= limit <= 10:
            raise FairyError("limit", "Asset search limit must be between 1 and 10")
        words = query.casefold().split()[:16]
        score = (
            " + ".join(["(instr(lower(name || ' ' || summary || ' ' || tags), ?) > 0)"] * len(words)) or "0"
        )
        statement = (
            "WITH active AS (SELECT a.*, e.seq AS adoption, "  # noqa: S608 - only trusted placeholder syntax is interpolated.
            "ROW_NUMBER() OVER (PARTITION BY a.scope, a.name ORDER BY e.seq DESC) AS rank "
            "FROM assets a JOIN asset_events e ON a.ref = e.ref "
            "WHERE e.status IN ('trial', 'stable') "
            "AND e.seq = (SELECT MAX(x.seq) FROM asset_events x WHERE x.ref = a.ref)), "
            f"scored AS (SELECT *, {score} AS score FROM active WHERE rank = 1) "
            "SELECT ref, name, scope, kind, summary, version, score FROM scored "
            "WHERE (? IS NULL OR scope = ?) AND (? = 0 OR score > 0) ORDER BY score DESC, name LIMIT ?"
        )
        rows = self.store.connection.execute(statement, (*words, scope, scope, len(words), limit)).fetchall()
        return [dict(row) for row in rows]

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
