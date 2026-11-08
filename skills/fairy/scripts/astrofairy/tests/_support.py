from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from typing import Any

from astrofairy import Workshop
from astrofairy._capabilities import Capability


def mock_capability(effect: str, handler: Any, template: Capability | None = None) -> Capability:
    return Capability(
        effect,
        handler,
        description="Controlled fixture capability",
        input_schema=template.input_schema
        if template
        else {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    )


ROOT = next(path for path in Path(__file__).resolve().parents if (path / "governance.toml").is_file())


class LiteralSearch:
    def __init__(self, home: Path) -> None:
        self.home = home

    def page(
        self,
        query: str,
        limit: int = 8,
        scope: str | None = None,
        kind: str | None = None,
        *,
        cursor: str | None = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        del refresh
        connection = sqlite3.connect(self.home / "workshop.sqlite3")
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                "WITH active AS ("
                " SELECT a.ref, a.scope, a.name, a.version, a.kind, a.summary, a.tags,"
                " e.seq AS adoption, e.status"
                " FROM assets a JOIN asset_events e ON e.ref = a.ref"
                " WHERE e.status IN ('trial', 'stable')"
                " AND e.seq = (SELECT MAX(x.seq) FROM asset_events x WHERE x.ref = a.ref)),"
                " ranked AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY scope, name"
                " ORDER BY adoption DESC) AS rank FROM active)"
                " SELECT ref, scope, name, version, kind, summary, tags"
                " FROM ranked WHERE rank = 1 ORDER BY scope, name"
            ).fetchall()
        finally:
            connection.close()
        words = query.casefold().split()
        result = []
        for row in rows:
            if scope is not None and row["scope"] != scope:
                continue
            if kind is not None and row["kind"] != kind:
                continue
            tags = json.loads(row["tags"])
            text = " ".join([row["name"], row["summary"], *tags]).casefold()
            score = sum(word in text for word in words)
            if words and score == 0:
                continue
            result.append(
                {
                    "ref": row["ref"],
                    "name": row["name"],
                    "scope": row["scope"],
                    "kind": row["kind"],
                    "summary": row["summary"],
                    "version": row["version"],
                    "score": score,
                }
            )
        result.sort(key=lambda item: (-item["score"], item["name"], item["scope"]))
        offset = 0
        if cursor is not None:
            from astrofairy._pagination import decode_cursor  # noqa: PLC0415 - test fixture.

            offset = decode_cursor(cursor)["offset"]
        page = result[offset : offset + limit]
        response: dict[str, Any] = {"matches": page, "total": len(result)}
        if offset + len(page) < len(result):
            from astrofairy._pagination import encode_cursor  # noqa: PLC0415 - test fixture.

            response["next_cursor"] = encode_cursor({"offset": offset + len(page)})
        return response

    def search(
        self,
        query: str,
        limit: int = 8,
        scope: str | None = None,
        kind: str | None = None,
        *,
        refresh: bool = False,
    ) -> list[dict[str, Any]]:
        return self.page(query, limit, scope, kind, refresh=refresh)["matches"]


class WorkshopTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "state"
        self.workshop = Workshop(self.home, search=LiteralSearch(self.home))
        self.addCleanup(self.workshop.store.close)

    def produce(
        self,
        task: str,
        text: str = "A useful result",
        *,
        publish: bool = True,
        path: str = "result.md",
        role: str = "main",
    ) -> dict[str, Any]:
        request = self.workshop.submit(task, {"op": "request", "purpose": "Produce useful content"})
        output = self.workshop.submit(
            task, {"op": "report", "call": request["call"], "text": text, "path": path}
        )
        if publish:
            self.publish(task, [output], roles=[role])
        return output

    def publish(
        self, task: str, outputs: list[dict[str, Any]], roles: list[str] | None = None
    ) -> dict[str, Any]:
        members = []
        for index, output in enumerate(outputs):
            members.append(
                {
                    "ref": output["ref"],
                    "path": output["path"],
                    "bytes": output["bytes"],
                    "media_type": output["media_type"],
                    "role": roles[index] if roles is not None else "main",
                }
            )
        return self.workshop.submit(task, {"op": "publish", "members": members})

    def refine(self, task: str) -> None:
        packet = self.workshop.next(task)
        if packet["provisional"]:
            self.workshop.submit(
                task,
                {
                    "op": "revise",
                    "goal": packet["goal"],
                    "criteria": packet["criteria"],
                    "reason": "Refine the provisional agreement for the actual task",
                },
            )

    def semantic(self, task: str, criterion: str = "goal", verdict: str = "pass", **extra: Any) -> None:
        self.workshop.submit(
            task,
            {
                "op": "review",
                "criterion": criterion,
                "verdict": verdict,
                "basis": "Compared the actual content with the stated criterion",
                **extra,
            },
        )

    def finish(self, task: str, criterion: str = "goal") -> dict[str, Any]:
        self.refine(task)
        self.workshop.submit(task, {"op": "check"})
        self.semantic(task, criterion)
        response = self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        delivery = response.get("delivery")
        if not isinstance(delivery, dict) or delivery.get("state") != "validated":
            raise AssertionError(f"close did not validate its delivery: {response}")
        return delivery

    def proposal(self, content: str = "Use concrete evidence and state applicability") -> dict[str, Any]:
        return {
            "name": "evidence-guide",
            "scope": "personal",
            "kind": "guide",
            "summary": "Evidence-based summaries",
            "tags": ["summary", "evidence"],
            "content": content,
            "evidence": [{"source": "task:example", "note": "Reviewer found claims easier to inspect"}],
        }
