from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import patch

from astrofairy import FairyError, Workshop
from astrofairy.tests._support import WorkshopTest, mock_capability

if TYPE_CHECKING:
    from astrofairy._capabilities import Context


class AvailableActionTests(WorkshopTest):
    def test_next_uses_one_coherent_event_snapshot(self) -> None:
        task = self.workshop.start("Work")
        self.produce(task)
        expected = self.workshop.state(task).seq
        events = self.workshop.store.events
        count = 0

        def interleave(identity: str) -> list[dict[str, Any]]:
            nonlocal count
            result = events(identity)
            count += 1
            if count == 1:
                with Workshop(self.home) as other:
                    other.submit(task, {"op": "answer", "text": "Later steering"})
            return result

        with patch.object(self.workshop.store, "events", side_effect=interleave):
            packet = self.workshop.next(task)
        self.assertEqual(packet["seq"], expected)
        self.assertEqual(packet["revision"], 1)
        self.assertEqual(packet["user_updates"], [])
        self.assertEqual(count, 1)
        self.assertEqual(self.workshop.state(task).revision, 2)

    def test_last_call_can_report_publish_review_and_complete_without_new_budget(self) -> None:
        task = self.workshop.start(
            "Work", budget=1, spec={"criteria": [{"id": "goal", "description": "Relevant"}]}
        )
        call = self.workshop.submit(task, {"op": "request", "purpose": "Produce result"})["call"]
        self.assertEqual(self.workshop.next(task)["action"], "resolve_pending")
        result = self.workshop.submit(task, {"op": "report", "call": call, "text": "Useful content"})
        seq = self.workshop.state(task).seq
        for _ in range(2):
            packet = self.workshop.next(task)
            self.assertEqual(packet["action"], "publish")
            self.assertEqual(packet["publish_candidate"]["ref"], result["ref"])
        self.assertEqual(self.workshop.state(task).seq, seq)
        self.workshop.submit(task, {"op": "publish", "ref": result["ref"]})
        self.assertEqual(self.workshop.next(task)["action"], "review")
        self.semantic(task)
        self.assertEqual(self.workshop.next(task)["action"], "close")
        self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.assertEqual(self.workshop.next(task)["action"], "delivered")
        self.assertEqual(len(self.workshop.state(task).calls), 1)

    def test_answer_and_explicit_reassessment_remain_available_at_zero_budget(self) -> None:
        task = self.workshop.start(
            "Work", budget=1, spec={"criteria": [{"id": "goal", "description": "Relevant"}]}
        )
        self.produce(task)
        self.workshop.submit(task, {"op": "ask", "question": "Audience?", "recommendation": "Internal"})
        self.assertEqual(self.workshop.next(task)["action"], "wait_for_answer")
        self.workshop.submit(task, {"op": "answer", "text": "Internal"})
        self.assertEqual(self.workshop.next(task)["action"], "review")
        self.semantic(task, verdict="fail")
        failure = self.workshop.state(task).reviews[-1]["id"]
        self.assertEqual(self.workshop.next(task)["action"], "review")
        self.semantic(task)
        self.assertFalse(self.workshop.state(task).complete())
        self.semantic(task, replaces=[failure])
        self.assertEqual(self.workshop.next(task)["action"], "close")

    def test_mechanical_deficit_still_requires_budget_and_optional_issue_does_not(self) -> None:
        task = self.workshop.start("Work", budget=1)
        self.produce(task)
        self.assertEqual(self.workshop.next(task)["action"], "close_partial")
        with self.assertRaises(FairyError):
            self.workshop.check(task)
        self.assertFalse(self.workshop.state(task).complete())
        optional = self.workshop.start(
            "Work",
            budget=1,
            spec={
                "criteria": [
                    {"id": "goal", "description": "Relevant"},
                    {"id": "extra", "description": "Optional JSON", "checker": "json", "required": False},
                ]
            },
        )
        self.produce(optional)
        self.semantic(optional)
        self.assertEqual(self.workshop.next(optional)["action"], "close")

    def test_unknown_call_remains_visible_at_zero_budget_and_can_be_cancelled(self) -> None:
        def uncertain(_context: Context, _parameters: dict[str, object]) -> dict[str, object]:
            raise OSError("Uncertain fixture effect")

        task = self.workshop.start("Work", budget=1)
        self.workshop.register("uncertain", mock_capability("write", uncertain))
        self.workshop.invoke(task, "uncertain", {})
        packet = self.workshop.next(task)
        self.assertEqual(packet["action"], "resolve_pending")
        self.assertEqual(packet["pending"][0]["status"], "unknown")
        with self.assertRaises(FairyError):
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.workshop.submit(task, {"op": "close", "outcome": "cancelled"})

    def test_no_output_and_no_budget_can_honestly_end_failed(self) -> None:
        task = self.workshop.start("Work", budget=1)
        self.workshop.invoke(task, "content.read", {"ref": "0" * 64})
        self.assertEqual(self.workshop.next(task)["action"], "close_failed")
