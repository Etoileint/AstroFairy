from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from typing import Any
from unittest.mock import patch

from astrofairy import Capability, Context, FairyError, Workshop
from astrofairy._capabilities import atomic_write
from astrofairy._contracts import canonical, parse_json
from astrofairy.tests._support import WorkshopTest


def object_schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


class ReconciliationTests(WorkshopTest):
    def setUp(self) -> None:
        super().setUp()
        self.ready, self.release = Event(), Event()
        self.mode = "unknown"
        self.proof_mode = "valid"
        self.authority = self.home.parent / "authority"
        self.executions = 0
        self.writer = Capability(
            "write",
            self.write_receipt,
            description="Create an attempt-correlated receipt",
            input_schema=object_schema({"text": {"type": "string"}}, ["text"]),
            output_schema=object_schema(
                {"outputs": {"type": "array"}, "receipt_id": {"type": "string"}}, ["outputs", "receipt_id"]
            ),
            reconciler="receipt.verify",
        )
        self.verifier = Capability(
            "read",
            self.verify_receipt,
            description="Inspect the authoritative attempt receipt",
            input_schema=object_schema({"call": {"type": "string", "pattern": "^[a-f0-9]{32}$"}}, ["call"]),
        )
        self.workshop.register("receipt.write", self.writer)
        self.workshop.register("receipt.verify", self.verifier)

    def result(self, context: Context, data: bytes) -> dict[str, Any]:
        body = parse_json(data.decode("utf-8"))
        return {
            "outputs": [
                {"ref": context.store.put(data), "name": "artifact.json", "media_type": "application/json"}
            ],
            "receipt_id": body["call"],
        }

    def write_receipt(self, context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
        self.executions += 1
        self.assertIsNotNone(context.call_id)
        self.assertFalse(context.store.connection.in_transaction)
        with sqlite3.connect(context.store.home / "workshop.sqlite3") as connection:
            rows = connection.execute(
                "SELECT payload FROM events WHERE task=? AND kind='invoked' ORDER BY seq DESC",
                (context.state.task,),
            ).fetchall()
        attempt = next(json.loads(row[0]) for row in rows if json.loads(row[0])["id"] == context.call_id)
        data = canonical(
            {
                "call": context.call_id,
                "text": parameters["text"],
                "operation": attempt["operation"],
                "contract_ref": attempt["contract_ref"],
            }
        )
        atomic_write(self.authority / str(context.call_id), data)
        self.ready.set()
        if self.mode.startswith("late") and not self.release.wait(5):
            raise RuntimeError("Fixture release timed out")
        if self.mode in {"unknown", "late_unknown"}:
            raise RuntimeError("Fixture observation lost after actual effect")
        if self.mode == "pending":
            raise KeyboardInterrupt
        result = self.result(context, data)
        if self.mode == "late_conflict":
            result["receipt_id"] = "different-positive-result"
        return result

    def verify_receipt(self, context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
        target_id = parameters["call"]
        target = context.state.calls[target_id]
        if self.proof_mode == "nonfinal":
            return {"outputs": [], "reconciliation": {"final": False}}
        if self.proof_mode == "exception":
            raise RuntimeError("SYNTHETIC_SECRET")
        data = (self.authority / target_id).read_bytes()
        body = parse_json(data.decode("utf-8"))
        self.assertEqual(body["call"], target_id)
        self.assertEqual(body["operation"], target["operation"])
        self.assertEqual(body["contract_ref"], target["contract_ref"])
        restored = self.result(context, data)
        if self.proof_mode == "conflict":
            restored["receipt_id"] = "different-positive-result"
        proof = {
            "target": {
                "call": target_id,
                "operation": target["operation"],
                "contract_ref": target["contract_ref"],
            },
            "final": True,
            "result": restored,
            "basis": "Atomic authority object matches the original attempt and parameters",
        }
        if self.proof_mode == "wrong_target":
            proof["target"]["call"] = "0" * 32
        if self.proof_mode == "bad_result":
            del restored["receipt_id"]
        if self.proof_mode == "mutate_input":
            parameters["call"] = "0" * 32
        if self.proof_mode == "mutate_context":
            context.state.calls[target_id]["operation"] = "mutated"
        return {"outputs": restored["outputs"], "reconciliation": proof}

    def uncertain(self, task: str) -> str:
        if self.mode == "pending":
            with self.assertRaises(KeyboardInterrupt):
                self.workshop.invoke(task, "receipt.write", {"text": "agreed"})
        else:
            self.assertEqual(
                self.workshop.invoke(task, "receipt.write", {"text": "agreed"})["status"], "unknown"
            )
        return next(
            call["id"]
            for call in self.workshop.state(task).calls.values()
            if call["capability"] == "receipt.write"
        )

    def confirm(self, task: str, identity: str) -> dict[str, Any]:
        return self.workshop.invoke(task, "receipt.verify", {"call": identity})

    def test_unknown_and_pending_confirm_without_rewriting_original_observation(self) -> None:
        for mode in ("unknown", "pending"):
            with self.subTest(mode=mode):
                self.mode = mode
                task = self.workshop.start("Produce a correlated receipt")
                identity = self.uncertain(task)
                before = dict(self.workshop.state(task).calls[identity])
                result = self.confirm(task, identity)
                state = self.workshop.state(task)
                self.assertEqual(state.calls[identity]["status"], before["status"])
                self.assertEqual(state.calls[identity].get("result"), before.get("result"))
                self.assertTrue(state.execution_settled())
                self.assertEqual(self.workshop.next(task)["pending"], [])
                with self.assertRaises(FairyError):
                    self.workshop.invoke(task, "receipt.write", {"text": "agreed"})
                self.workshop.submit(task, {"op": "publish", "ref": result["outputs"][0]["ref"]})
                self.finish(task)
                with Workshop(self.home) as reopened:
                    self.assertTrue(reopened.state(task).complete())
                    frozen = state.calls[identity]["reconciler"]["contract_ref"]
                    self.assertTrue(Context(reopened.store, reopened.state(task)).content(frozen))
                    self.assertEqual(
                        reopened.inspect_contract(task, frozen)["definition"]["name"], "receipt.verify"
                    )

    def test_nonfinal_exception_wrong_proof_and_frozen_output_schema_do_not_settle(self) -> None:
        for mode in ("nonfinal", "exception", "wrong_target", "bad_result"):
            with self.subTest(mode=mode):
                task = self.workshop.start("Produce a correlated receipt")
                identity = self.uncertain(task)
                self.proof_mode = mode
                result = self.confirm(task, identity)
                self.assertEqual(result["status"], "ok" if mode == "nonfinal" else "failed")
                self.assertNotIn("SYNTHETIC_SECRET", json.dumps(result))
                self.assertFalse(self.workshop.state(task).execution_settled())
                self.proof_mode = "valid"

    def test_callback_mutation_cannot_change_the_committed_target(self) -> None:
        for mode in ("mutate_input", "mutate_context"):
            with self.subTest(mode=mode):
                task = self.workshop.start("Produce a correlated receipt")
                identity = self.uncertain(task)
                self.proof_mode = mode
                self.assertEqual(self.confirm(task, identity)["status"], "ok")
                self.assertTrue(self.workshop.state(task).execution_settled())
                self.proof_mode = "valid"

    def test_changed_verifier_extra_parameters_and_model_reports_cannot_confirm(self) -> None:
        task = self.workshop.start("Produce a correlated receipt")
        identity = self.uncertain(task)
        before = self.workshop.state(task).seq
        with self.assertRaises(FairyError):
            self.workshop.invoke(task, "receipt.verify", {"call": identity, "extra": True})
        with self.assertRaises(FairyError):
            self.workshop.submit(task, {"op": "report", "call": identity, "text": "It succeeded"})
        changed = Capability(
            "read",
            self.verify_receipt,
            description="Changed verification declaration",
            input_schema=self.verifier.input_schema,
        )
        self.workshop.register("receipt.verify", changed, replace=True)
        with self.assertRaises(FairyError):
            self.confirm(task, identity)
        self.assertEqual(self.workshop.state(task).seq, before)

    def test_positive_conflict_stays_after_matching_and_nonfinal_evidence(self) -> None:
        task = self.workshop.start("Produce a correlated receipt")
        identity = self.uncertain(task)
        self.confirm(task, identity)
        self.proof_mode = "conflict"
        self.confirm(task, identity)
        self.proof_mode = "valid"
        self.confirm(task, identity)
        self.proof_mode = "nonfinal"
        self.confirm(task, identity)
        state = self.workshop.state(task)
        self.assertTrue(state.execution_conflicts())
        self.assertFalse(state.execution_settled())
        self.assertEqual(state.next_action(), "inspect_conflict")
        with self.assertRaises(FairyError):
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})

    def test_late_native_conflict_refreshes_closed_receipt_and_survives_export_failure(self) -> None:
        self.mode = "late_conflict"
        task = self.workshop.start("Produce a correlated receipt")
        pool = ThreadPoolExecutor(max_workers=1)
        self.addCleanup(pool.shutdown)
        self.addCleanup(self.release.set)

        def running() -> dict[str, Any]:
            with Workshop(
                self.home, {"receipt.write": self.writer, "receipt.verify": self.verifier}
            ) as worker:
                return worker.invoke(task, "receipt.write", {"text": "agreed"})

        future = pool.submit(running)
        self.assertTrue(self.ready.wait(5))
        identity = next(iter(self.workshop.state(task).calls))
        confirmed = self.confirm(task, identity)
        self.workshop.submit(task, {"op": "publish", "ref": confirmed["outputs"][0]["ref"]})
        closed = self.finish(task)
        with patch("astrofairy._runtime.atomic_write", side_effect=OSError("Fixture export failure")):
            self.release.set()
            with self.assertRaises(OSError):
                future.result(timeout=5)
        state = self.workshop.state(task)
        self.assertEqual(state.outcome, "complete")
        self.assertTrue(state.execution_conflicts())
        self.assertFalse(state.complete())
        self.assertEqual(self.workshop.next(task)["action"], "inspect_conflict")
        refreshed = self.workshop.deliver(task)
        self.assertTrue(refreshed["execution_conflicts"])
        receipt = parse_json(Path(closed["receipt_path"]).read_text(encoding="utf-8"))
        self.assertEqual(receipt["seq"], state.seq)
        self.assertFalse(receipt["execution_settled"])
        self.assertTrue(receipt["execution_conflicts"])
