from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from astrofairy import FairyError, Workshop
from astrofairy._capabilities import Context, builtins
from astrofairy._contracts import canonical, parse_json
from astrofairy.tests._support import WorkshopTest, mock_capability


class TaskTests(WorkshopTest):
    def test_feedback_refreshes_closed_delivery_receipt(self) -> None:
        task = self.workshop.start("Work")
        self.produce(task)
        delivery = self.finish(task)
        self.workshop.submit(task, {"op": "feedback", "text": "Keep this useful method", "kind": "positive"})
        receipt = parse_json(Path(delivery["receipt_path"]).read_text(encoding="utf-8"))
        self.assertEqual(receipt["feedback"][0]["kind"], "positive")
        self.assertEqual(receipt["seq"], self.workshop.state(task).seq)

    def test_new_task_workspace_exists_for_host_tools(self) -> None:
        task = self.workshop.start("Work")
        self.assertTrue(Path(self.workshop.next(task)["workspace"]).is_dir())

    def test_capture_infers_media_type_without_claiming_content_validity(self) -> None:
        task = self.workshop.start("Work")
        path = Path(self.workshop.next(task)["workspace"]) / "note.json"
        path.write_bytes(b"{}")
        observed = self.workshop.invoke(task, "file.capture", {"path": "note.json"})
        self.assertEqual(observed["outputs"][0]["media_type"], "application/json")

    def test_unknown_capability_fields_reject_before_invocation(self) -> None:
        task = self.workshop.start("Work")
        with self.assertRaises(FairyError):
            self.workshop.invoke(task, "text.write", {"path": "x", "text": "x", "unsafe_typo": True})
        self.assertFalse(self.workshop.state(task).calls)

    def test_capability_discovery_does_not_load_whole_catalog(self) -> None:
        task = self.workshop.start("Work")
        for index in range(100):
            self.workshop.register(
                f"extra.tool{index}", mock_capability("read", lambda _context, _parameters: {"outputs": []})
            )
        packet = self.workshop.next(task)
        self.assertEqual(len(packet["capabilities"]), 8)
        self.assertGreater(packet["capability_count"], 100)
        self.assertEqual(len(self.workshop.catalog("tool99")["matches"]), 1)

    def test_bad_output_name_does_not_close_or_consume_request(self) -> None:
        task = self.workshop.start("Work")
        request = self.workshop.submit(task, {"op": "request", "purpose": "Produce result"})
        with self.assertRaises(FairyError):
            self.workshop.submit(
                task, {"op": "report", "call": request["call"], "text": "result", "name": "bad\x00name"}
            )
        self.assertEqual(self.workshop.state(task).calls[request["call"]]["status"], "pending")

    def test_complete_delivery_has_actual_bytes_and_provenance(self) -> None:
        task = self.workshop.start("整理一份简报")
        self.assertEqual(self.workshop.next(task)["action"], "produce")
        self.produce(task, "实际成果\n证据与建议")
        result = self.finish(task)
        self.assertNotIn("calls", result)
        self.assertNotIn("reviews", result)
        self.assertEqual(Path(result["artifact_path"]).read_text(encoding="utf-8"), "实际成果\n证据与建议")
        receipt = parse_json(Path(result["receipt_path"]).read_text(encoding="utf-8"))
        self.assertEqual(receipt["outcome"], "complete")
        self.assertEqual({item["producer"] for item in receipt["reviews"]}, {"model", "tool:nonempty"})
        self.assertEqual(receipt["calls"][0]["origin"], "model")
        if os.name == "posix":
            self.assertEqual(Path(result["artifact_path"]).stat().st_mode & 0o777, 0o600)
            self.assertEqual((self.home / "workshop.sqlite3").stat().st_mode & 0o777, 0o600)

    def test_real_file_tool_runs_and_capture_preserves_binary_bytes(self) -> None:
        task = self.workshop.start("Create a file")
        observation = self.workshop.submit(
            task,
            {
                "op": "invoke",
                "capability": "text.write",
                "parameters": {"path": "report.txt", "text": "actual bytes"},
            },
        )
        self.assertEqual(observation["origin"], "tool")
        self.assertEqual(Path(observation["result"]["path"]).read_bytes(), b"actual bytes")
        binary = self.home / "workspaces" / task / "raw.bin"
        binary.write_bytes(b"\xff\x00\r\n")
        capture = self.workshop.submit(
            task, {"op": "invoke", "capability": "file.capture", "parameters": {"path": "raw.bin"}}
        )
        self.assertEqual(self.workshop.store.get(capture["outputs"][0]["ref"]), b"\xff\x00\r\n")

    def test_read_only_scope_blocks_write_before_call_and_charge(self) -> None:
        task = self.workshop.start("Inspect", effects=["reason", "read"])
        with self.assertRaises(FairyError) as caught:
            self.workshop.submit(
                task, {"op": "invoke", "capability": "text.write", "parameters": {"path": "x", "text": "x"}}
            )
        self.assertEqual(caught.exception.code, "permission")
        self.assertFalse(self.workshop.state(task).calls)

    def test_path_traversal_does_not_write_outside_workspace(self) -> None:
        task = self.workshop.start("Write")
        with self.assertRaises(FairyError):
            self.workshop.invoke(task, "text.write", {"path": "../../escape", "text": "no"})
        self.assertFalse(self.workshop.state(task).calls)
        self.assertFalse((self.home / "escape").exists())

    def test_inputs_are_snapshots_and_reads_are_bounded(self) -> None:
        source = Path(self.temporary.name) / "source.txt"
        source.write_text("原始材料" * 10000, encoding="utf-8")
        task = self.workshop.start("Summarize", inputs=[source])
        ref = self.workshop.state(task).inputs[0]["ref"]
        source.write_text("changed", encoding="utf-8")
        result = self.workshop.invoke(task, "content.read", {"ref": ref, "offset": 0, "limit": 4})
        self.assertEqual(result["result"]["text"], "原始材料")
        self.assertGreater(result["result"]["characters"], 4)

    def test_model_cannot_forge_tool_review_or_observation(self) -> None:
        task = self.workshop.start("Work")
        self.produce(task)
        with self.assertRaises(FairyError):
            self.semantic(task, "usable")
        with self.assertRaises(FairyError):
            self.workshop.submit(task, {"op": "observed", "status": "ok"})

    def test_conflicting_pass_does_not_erase_fail(self) -> None:
        task = self.workshop.start("Work")
        self.produce(task)
        self.workshop.check(task)
        self.semantic(task, verdict="fail")
        failed = self.workshop.state(task).reviews[-1]["id"]
        self.semantic(task)
        with self.assertRaises(FairyError):
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.semantic(task, replaces=[failed])
        self.assertEqual(
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})["outcome"], "complete"
        )

    def test_repair_requires_new_checks(self) -> None:
        task = self.workshop.start("Work")
        self.produce(task, "first")
        self.workshop.check(task)
        self.semantic(task)
        self.produce(task, "repaired")
        self.assertFalse(self.workshop.state(task).complete())
        self.finish(task)

    def test_goal_revision_preserves_but_invalidates_checks(self) -> None:
        task = self.workshop.start("Work")
        self.produce(task)
        self.workshop.check(task)
        self.semantic(task)
        state = self.workshop.state(task)
        self.workshop.submit(
            task,
            {
                "op": "revise",
                "goal": "Changed goal",
                "criteria": state.spec["criteria"],
                "reason": "New information",
            },
        )
        self.assertFalse(self.workshop.state(task).complete())
        self.assertEqual(len(self.workshop.state(task).reviews), 2)

    def test_explicit_requirements_need_forwarded_user_change(self) -> None:
        task = self.workshop.start(
            "Work", spec={"criteria": [{"id": "goal", "description": "Original", "origin": "user"}]}
        )
        revised = [{"id": "goal", "description": "Changed", "origin": "user"}]
        command = {"op": "revise", "goal": "Changed", "criteria": revised, "reason": "Requested change"}
        with self.assertRaises(FairyError):
            self.workshop.submit(task, command)
        answer = self.workshop.submit(task, {"op": "answer", "text": "Use the changed requirement"})
        self.workshop.submit(task, {**command, "user_basis": answer["seq"]})
        self.assertEqual(self.workshop.state(task).spec["criteria"][0]["description"], "Changed")

    def test_unknown_write_is_not_blindly_retried(self) -> None:
        def uncertain(_context: Context, _parameters: dict[str, Any]) -> dict[str, Any]:
            raise OSError("an operation may have happened")

        self.workshop.register("uncertain", mock_capability("write", uncertain))
        task = self.workshop.start("Work")
        result = self.workshop.invoke(task, "uncertain", {})
        self.assertEqual(result["status"], "unknown")
        with self.assertRaises(FairyError) as caught:
            self.workshop.invoke(task, "uncertain", {})
        self.assertEqual(caught.exception.code, "unknown")

    def test_budget_exhaustion_allows_honest_partial_delivery(self) -> None:
        task = self.workshop.start("Work", budget=1)
        self.produce(task)
        self.assertEqual(self.workshop.next(task)["action"], "close_partial")
        with self.assertRaises(FairyError):
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.assertEqual(
            self.workshop.submit(task, {"op": "close", "outcome": "partial"})["outcome"], "partial"
        )

    def test_closed_task_retains_late_report_and_feedback(self) -> None:
        task = self.workshop.start("Work")
        request = self.workshop.submit(task, {"op": "request", "purpose": "Pending work"})
        self.workshop.submit(task, {"op": "close", "outcome": "cancelled"})
        self.workshop.submit(task, {"op": "report", "call": request["call"], "text": "Late result"})
        self.workshop.submit(task, {"op": "feedback", "text": "Good structure", "kind": "positive"})
        with self.assertRaises(FairyError):
            self.workshop.submit(task, {"op": "request", "purpose": "More work"})
        state = self.workshop.state(task)
        self.assertEqual(state.outcome, "cancelled")
        self.assertEqual(state.feedback[0]["kind"], "positive")

    def test_pending_work_survives_reopen(self) -> None:
        task = self.workshop.start("Work")
        request = self.workshop.submit(task, {"op": "request", "purpose": "Work packet"})
        with Workshop(self.home) as reopened:
            self.assertEqual(reopened.next(task)["action"], "resolve_pending")
            reopened.submit(task, {"op": "report", "call": request["call"], "text": "Recovered result"})
        self.assertEqual(self.workshop.state(task).calls[request["call"]]["status"], "ok")

    def test_stale_submission_rejects_without_mutation(self) -> None:
        task = self.workshop.start("Work")
        seq = self.workshop.state(task).seq
        with Workshop(self.home) as other:
            other.submit(task, {"op": "feedback", "text": "New context"})
        with self.assertRaises(FairyError) as caught:
            self.workshop.submit(task, {"op": "request", "purpose": "stale", "expected_seq": seq})
        self.assertEqual(caught.exception.code, "conflict")
        self.assertFalse(self.workshop.state(task).calls)

    def test_content_and_event_corruption_are_detected(self) -> None:
        task = self.workshop.start("Work")
        ref = self.produce(task)
        self.workshop.store.connection.execute("UPDATE blobs SET data = ? WHERE ref = ?", (b"corrupt", ref))
        with self.assertRaises(FairyError):
            self.workshop.store.get(ref)
        self.workshop.store.connection.execute(
            "UPDATE events SET payload = ? WHERE task = ? AND seq = 1", ("{}", task)
        )
        with self.assertRaises(FairyError):
            self.workshop.state(task)

    def test_duplicate_keys_nonfinite_and_unknown_fields_fail(self) -> None:
        for source in ('{"x":1,"x":2}', '{"x":NaN}'):
            with self.subTest(source=source), self.assertRaises(FairyError):
                parse_json(source)
        task = self.workshop.start("Work")
        before = canonical(self.workshop.inspect(task))
        with self.assertRaises(FairyError):
            self.workshop.submit(task, {"op": "request", "purpose": "x", "actor": "runner"})
        self.assertEqual(canonical(self.workshop.inspect(task)), before)

    def test_question_budget_and_spontaneous_steering(self) -> None:
        task = self.workshop.start("Work")
        for index in range(3):
            self.workshop.submit(
                task, {"op": "ask", "question": "Choose a direction", "recommendation": "Use A"}
            )
            self.workshop.submit(task, {"op": "answer", "text": f"Choice {index}"})
        with self.assertRaises(FairyError):
            self.workshop.submit(task, {"op": "ask", "question": "Again?", "recommendation": "A"})

    def test_new_capability_requires_no_kernel_change(self) -> None:
        self.workshop.register(
            "domain.compute",
            mock_capability("read", lambda _context, _parameters: {"outputs": [], "value": 42}),
        )
        task = self.workshop.start("Work")
        self.assertEqual(self.workshop.invoke(task, "domain.compute", {})["result"]["value"], 42)

    def test_check_cannot_approve_artifact_changed_during_call(self) -> None:
        task = self.workshop.start("Work")
        self.produce(task, "first")
        second = self.produce(task, "second", publish=False)
        original = builtins()["content.check"]

        def changing(context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
            with Workshop(self.home) as other:
                other.submit(task, {"op": "publish", "ref": second})
            return original.handler(context, parameters)

        self.workshop.register(
            "content.check", mock_capability(original.effect, changing, original), replace=True
        )
        with self.assertRaises(FairyError) as caught:
            self.workshop.check(task)
        self.assertEqual(caught.exception.code, "stale")
        self.assertFalse(self.workshop.state(task).reviews)
