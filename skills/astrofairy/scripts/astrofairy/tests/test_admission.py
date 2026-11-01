from __future__ import annotations

import sqlite3
from typing import Any
from unittest.mock import patch

from astrofairy import FairyError, Workshop
from astrofairy._capabilities import Context, builtins
from astrofairy._contracts import canonical, parse_json
from astrofairy.tests._support import WorkshopTest, mock_capability


class AdmissionTests(WorkshopTest):
    def test_stale_commands_share_admission_without_new_effects(self) -> None:
        for operation in ("feedback", "invoke", "check", "learn"):
            with self.subTest(operation=operation):
                task = self.workshop.start("Work")
                self.produce(task)
                if operation == "learn":
                    self.workshop.submit(task, {"op": "close", "outcome": "partial"})
                old = self.workshop.state(task).seq
                self.workshop.submit(task, {"op": "feedback", "text": "New information"})
                commands = {
                    "feedback": {"op": "feedback", "text": "Old request"},
                    "invoke": {
                        "op": "invoke",
                        "capability": "content.read",
                        "parameters": {"ref": self.workshop.state(task).artifact["ref"]},
                    },
                    "check": {"op": "check"},
                    "learn": {"op": "learn"},
                }
                before = canonical(self.workshop.inspect(task, history=True))
                tasks = self.workshop.store.tasks()
                for expected in (old, 0):
                    with self.assertRaises(FairyError) as caught:
                        self.workshop.submit(task, {**commands[operation], "expected_seq": expected})
                    self.assertEqual(caught.exception.code, "conflict")
                self.assertEqual(self.workshop.store.tasks(), tasks)
                self.assertEqual(canonical(self.workshop.inspect(task, history=True)), before)

    def test_first_check_invocation_rechecks_sequence_at_its_write_boundary(self) -> None:
        task = self.workshop.start("Work")
        self.produce(task)
        expected = self.workshop.state(task).seq
        invoke = self.workshop.invoke

        def interleave(
            identity: str, name: str, parameters: dict[str, Any], expected_seq: int | None = None
        ) -> dict[str, Any]:
            with Workshop(self.home) as other:
                other.submit(task, {"op": "answer", "text": "Changed context"})
            return invoke(identity, name, parameters, expected_seq)

        with (
            patch.object(self.workshop, "invoke", side_effect=interleave),
            self.assertRaises(FairyError) as caught,
        ):
            self.workshop.submit(task, {"op": "check", "expected_seq": expected})
        self.assertEqual(caught.exception.code, "conflict")
        self.assertEqual(len(self.workshop.state(task).calls), 1)
        self.assertEqual(self.workshop.state(task).reviews, [])

    def test_check_target_is_not_reselected_between_criteria(self) -> None:
        task = self.workshop.start(
            "Work",
            spec={
                "criteria": [
                    {"id": "bytes", "description": "Nonempty", "checker": "nonempty"},
                    {"id": "syntax", "description": "JSON", "checker": "json"},
                ]
            },
        )
        self.produce(task, "{}")
        invoke = self.workshop.invoke
        count = 0

        def interleave(
            identity: str, name: str, parameters: dict[str, Any], expected_seq: int | None = None
        ) -> dict[str, Any]:
            nonlocal count
            count += 1
            if count == 2:
                with Workshop(self.home) as other:
                    other.submit(task, {"op": "answer", "text": "New agreement"})
            return invoke(identity, name, parameters, expected_seq)

        with patch.object(self.workshop, "invoke", side_effect=interleave), self.assertRaises(FairyError):
            self.workshop.check(task)
        state = self.workshop.state(task)
        self.assertEqual(len(state.calls), 2)
        self.assertEqual(len(state.reviews), 1)
        self.assertEqual(state.active_reviews(), [])

    def test_non_target_feedback_during_handler_is_allowed_without_holding_transaction(self) -> None:
        task = self.workshop.start("Work")
        self.produce(task)
        original = builtins()["content.check"]

        def feedback(context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
            self.assertFalse(context.store.connection.in_transaction)
            with Workshop(self.home) as other:
                other.submit(task, {"op": "feedback", "text": "Keep the evidence"})
            return original.handler(context, parameters)

        self.workshop.register("content.check", mock_capability("read", feedback, original), replace=True)
        self.workshop.check(task)
        self.assertEqual(self.workshop.state(task).active_reviews()[0]["verdict"], "pass")

    def test_empty_check_set_still_checks_sequence(self) -> None:
        task = self.workshop.start("Work", spec={"criteria": [{"id": "goal", "description": "Relevant"}]})
        self.produce(task)
        seq = self.workshop.state(task).seq
        with self.assertRaises(FairyError):
            self.workshop.submit(task, {"op": "check", "expected_seq": seq - 1})
        self.assertEqual(self.workshop.submit(task, {"op": "check", "expected_seq": seq})["checks"], [])
        self.assertEqual(self.workshop.state(task).seq, seq)

    def test_learning_snapshot_and_child_share_one_transaction_without_mutating_source(self) -> None:
        task = self.workshop.start("Work")
        self.produce(task)
        self.workshop.submit(task, {"op": "close", "outcome": "partial"})
        seq = self.workshop.state(task).seq
        inspect = self.workshop.inspect
        with Workshop(self.home) as other:
            other.store.connection.execute("PRAGMA busy_timeout = 0")

            def inspect_with_writer(identity: str, *, history: bool = False) -> dict[str, Any]:
                with self.assertRaises(sqlite3.OperationalError):
                    other.submit(task, {"op": "feedback", "text": "Concurrent update"})
                return inspect(identity, history=history)

            with patch.object(self.workshop, "inspect", side_effect=inspect_with_writer):
                child = self.workshop.submit(task, {"op": "learn", "expected_seq": seq})["learning_task"]
        summary = parse_json(self.workshop.store.get(self.workshop.state(child).inputs[0]["ref"]).decode())
        self.assertEqual((summary["task"], summary["seq"]), (task, seq))
        self.assertEqual(self.workshop.state(task).seq, seq)
        repeated = self.workshop.submit(task, {"op": "learn", "expected_seq": seq})["learning_task"]
        self.assertNotEqual(child, repeated)

    def test_child_failure_rolls_back_summary_blob_and_events(self) -> None:
        task = self.workshop.start("Work")
        self.workshop.submit(task, {"op": "close", "outcome": "cancelled"})
        tasks = self.workshop.store.tasks()
        blobs = self.workshop.store.connection.execute("SELECT count(*) FROM blobs").fetchone()[0]
        with (
            patch.object(self.workshop, "_start", side_effect=OSError("fixture failure")),
            self.assertRaises(OSError),
        ):
            self.workshop.learning_task(task)
        self.assertEqual(self.workshop.store.tasks(), tasks)
        self.assertEqual(
            self.workshop.store.connection.execute("SELECT count(*) FROM blobs").fetchone()[0], blobs
        )
