from __future__ import annotations

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


class WorkshopTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "state"
        self.workshop = Workshop(self.home)
        self.addCleanup(self.workshop.store.close)

    def produce(self, task: str, text: str = "A useful result", *, publish: bool = True) -> str:
        request = self.workshop.submit(task, {"op": "request", "purpose": "Produce useful content"})
        output = self.workshop.submit(task, {"op": "report", "call": request["call"], "text": text})
        if publish:
            self.workshop.submit(task, {"op": "publish", "ref": output["ref"]})
        return str(output["ref"])

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
        self.workshop.submit(task, {"op": "check"})
        self.semantic(task, criterion)
        return self.workshop.submit(task, {"op": "close", "outcome": "complete"})

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
