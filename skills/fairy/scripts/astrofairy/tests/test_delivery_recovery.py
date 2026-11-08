from __future__ import annotations

import hashlib
import json
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import patch

from astrofairy import FairyError, Workshop
from astrofairy._contracts import canonical, parse_json
from astrofairy._delivery import _verify
from astrofairy.tests._support import WorkshopTest


class DeliveryRecoveryTests(WorkshopTest):
    def ready(self) -> str:
        task = self.workshop.start("Deliver with recovery")
        self.produce(task)
        self.refine(task)
        self.workshop.submit(task, {"op": "check"})
        self.semantic(task)
        return task

    def complete(self, task: str) -> dict[str, Any]:
        self.refine(task)
        self.workshop.submit(task, {"op": "check"})
        self.semantic(task)
        response = self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        delivery = response["delivery"]
        self.assertEqual(delivery["state"], "validated")
        return delivery

    def test_close_export_failure_is_committed_and_recoverable(self) -> None:
        task = self.ready()
        with patch(
            "astrofairy._runtime.deliver_bag",
            side_effect=FairyError("integrity", "controlled export failure"),
        ):
            response = self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.assertEqual(response["seq"], self.workshop.state(task).seq)
        delivery = response["delivery"]
        self.assertEqual(delivery["state"], "failed")
        self.assertTrue(delivery["committed"])
        self.assertEqual(delivery["committed_seq"], response["seq"])
        self.assertEqual(delivery["error"]["error"], "integrity")
        self.assertEqual(delivery["recovery"]["command"], f"deliver {task}")
        self.assertFalse(delivery["recovery"]["repeats_effect"])
        self.assertEqual(self.workshop.state(task).outcome, "complete")
        with Workshop(self.home) as reopened:
            packet = reopened.next(task)
            self.assertEqual(packet["action"], "deliver")
            self.assertEqual(packet["delivery"]["state"], "absent")
            self.assertEqual(packet["deliver_command"], f"deliver {task}")
            recovered = reopened.deliver(task)
        self.assertEqual(recovered["state"], "validated")
        with self.assertRaises(FairyError) as caught:
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.assertEqual(caught.exception.code, "closed")

    def test_late_feedback_export_failure_keeps_fact_and_old_bag(self) -> None:
        task = self.workshop.start("Late feedback")
        self.produce(task)
        closed = self.complete(task)
        old_receipt = Path(closed["receipt_path"]).read_bytes()
        with patch(
            "astrofairy._runtime.deliver_bag",
            side_effect=FairyError("integrity", "late export failure"),
        ):
            response = self.workshop.submit(
                task, {"op": "feedback", "text": "Late observation", "kind": "observation"}
            )
        self.assertEqual(response["delivery"]["state"], "failed")
        self.assertTrue(response["delivery"]["committed"])
        self.assertEqual(self.workshop.state(task).feedback[-1]["text"], "Late observation")
        self.assertEqual(Path(closed["receipt_path"]).read_bytes(), old_receipt)
        packet = self.workshop.next(task)
        self.assertEqual(packet["action"], "deliver")
        self.assertEqual(packet["delivery"]["seq"], self.workshop.state(task).seq)
        recovered = self.workshop.deliver(task)
        self.assertNotEqual(recovered["receipt_path"], closed["receipt_path"])
        receipt = parse_json(Path(recovered["receipt_path"]).read_text(encoding="utf-8"))
        self.assertEqual(receipt["feedback"][0]["text"], "Late observation")
        self.assertEqual(receipt["seq"], self.workshop.state(task).seq)

    def test_late_tool_observation_export_failure_preserves_observed_status(self) -> None:
        task = self.workshop.start("Late observation")
        release = threading.Event()
        entered = threading.Event()

        def blocking(_context: Any, _parameters: dict[str, Any]) -> dict[str, Any]:
            entered.set()
            if not release.wait(10):
                raise AssertionError("fixture was not released")
            return {"outputs": []}

        from astrofairy.tests._support import LiteralSearch, mock_capability  # noqa: PLC0415

        def running() -> dict[str, Any]:
            worker = Workshop(self.home, search=LiteralSearch(self.home))
            try:
                worker.register("fixture.late", mock_capability("read", blocking))
                return worker.invoke(task, "fixture.late", {})
            finally:
                worker.store.close()

        pool = ThreadPoolExecutor(max_workers=1)
        self.addCleanup(pool.shutdown)
        future = pool.submit(running)
        self.assertTrue(entered.wait(5))
        self.workshop.submit(task, {"op": "close", "outcome": "cancelled"})
        with patch(
            "astrofairy._runtime.deliver_bag",
            side_effect=FairyError("integrity", "late tool export failure"),
        ):
            release.set()
            observation = future.result(timeout=10)
        self.assertEqual(observation["status"], "ok")
        self.assertEqual(observation["origin"], "tool")
        self.assertEqual(observation["delivery"]["state"], "failed")
        self.assertTrue(observation["delivery"]["committed"])
        call = self.workshop.state(task).calls[observation["call"]]
        self.assertEqual(call["status"], "ok")
        self.assertEqual(self.workshop.next(task)["action"], "deliver")

    def test_learn_export_failure_keeps_decision_and_child(self) -> None:
        task = self.workshop.start("Learn late")
        self.produce(task)
        self.complete(task)
        with patch(
            "astrofairy._runtime.deliver_bag",
            side_effect=FairyError("integrity", "learning export failure"),
        ):
            response = self.workshop.submit(task, {"op": "learn", "decision": "maintain"})
        child = response["learning_task"]
        self.assertEqual(response["delivery"]["state"], "failed")
        self.assertTrue(response["delivery"]["committed"])
        self.assertEqual(self.workshop.state(task).learning_decisions[-1]["learning_task"], child)
        self.assertIn(child, self.workshop.store.tasks())
        self.assertEqual(self.workshop.next(task)["action"], "deliver")
        recovered = self.workshop.deliver(task)
        receipt = parse_json(Path(recovered["receipt_path"]).read_text(encoding="utf-8"))
        self.assertEqual(receipt["learning_decisions"][-1]["learning_task"], child)
        self.assertEqual(self.workshop.state(task).learning_decisions[-1]["learning_task"], child)

    def test_next_probe_does_not_create_delivery_paths(self) -> None:
        task = self.ready()
        with patch(
            "astrofairy._runtime.deliver_bag",
            side_effect=FairyError("integrity", "no export"),
        ):
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.assertFalse((self.home / "deliveries").exists())
        packet = self.workshop.next(task)
        self.assertEqual(packet["action"], "deliver")
        self.assertFalse((self.home / "deliveries").exists())
        self.workshop.inspect(task)
        self.assertFalse((self.home / "deliveries").exists())

    def test_expected_sequence_and_export_identity_are_separate(self) -> None:
        task = self.ready()
        with self.assertRaises(FairyError) as caught:
            self.workshop.deliver(task)
        self.assertEqual(caught.exception.code, "not_ready")
        closed = self.complete(task)
        with self.assertRaises(FairyError) as caught:
            self.workshop.deliver(task, expected_seq=closed["seq"] - 1)
        self.assertEqual(caught.exception.code, "conflict")
        self.workshop.submit(task, {"op": "feedback", "text": "after close"})
        current = self.workshop.state(task).seq
        frozen = self.workshop.next(task)["delivery"]
        self.assertEqual(frozen["seq"], current)

    def test_post_commit_export_binds_frozen_snapshot_and_next_sees_later_seq(self) -> None:
        task = self.ready()
        from astrofairy import _runtime as runtime_module  # noqa: PLC0415

        real = runtime_module.deliver_bag
        frozen: dict[str, int] = {}

        def writer(
            home: Path, state: Any, store: Any, inspection: dict[str, Any], *, repair: bool = False
        ) -> Any:
            with store.transaction():
                store.append(
                    task,
                    "feedback",
                    {"text": "later writer", "kind": "observation", "origin": "user_report"},
                    state.seq,
                )
            frozen["seq"] = state.seq
            return real(home, state, store, inspection, repair=repair)

        with patch("astrofairy._runtime.deliver_bag", side_effect=writer):
            response = self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.assertEqual(response["seq"], response["delivery"]["committed_seq"])
        self.assertEqual(response["delivery"]["seq"], frozen["seq"])
        self.assertLess(response["delivery"]["seq"], self.workshop.state(task).seq)
        packet = self.workshop.next(task)
        self.assertEqual(packet["seq"], self.workshop.state(task).seq)
        self.assertEqual(packet["delivery"]["seq"], self.workshop.state(task).seq)
        self.assertEqual(packet["action"], "deliver")

    def test_repair_never_follows_a_redirect(self) -> None:
        task = self.ready()
        with patch(
            "astrofairy._runtime.deliver_bag",
            side_effect=FairyError("integrity", "no export"),
        ):
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        external = Path(self.temporary.name) / "outside"
        external.mkdir()
        (self.home / "deliveries").symlink_to(external, target_is_directory=True)
        with self.assertRaises(FairyError) as caught:
            self.workshop.deliver(task, repair=True)
        self.assertEqual(caught.exception.code, "unsafe_delivery")
        self.assertEqual(caught.exception.details["reason"], "symbolic_link")
        self.assertEqual(list(external.iterdir()), [])

    def test_self_consistent_replacement_is_not_accepted_as_current(self) -> None:
        task = self.workshop.start("Tamper")
        self.produce(task)
        closed = self.complete(task)
        bag = Path(closed["bag_path"])
        tampered = json.loads((bag / "receipt.json").read_text(encoding="utf-8"))
        tampered["outcome"] = "partial"
        (bag / "receipt.json").write_text(canonical(tampered).decode(), encoding="utf-8")
        before = (bag / "receipt.json").read_bytes()
        self.assertEqual(self.workshop.next(task)["action"], "verify_delivery")
        with self.assertRaises(FairyError) as caught:
            self.workshop.deliver(task)
        self.assertEqual(caught.exception.code, "integrity")
        self.assertIn("repair_command", caught.exception.details)
        self.assertEqual((bag / "receipt.json").read_bytes(), before)

    def test_repair_quarantines_invalid_export_and_preserves_facts(self) -> None:
        task = self.workshop.start("Repair")
        self.produce(task)
        closed = self.complete(task)
        bag = Path(closed["bag_path"])
        from astrofairy._delivery import _write_bagit_1  # noqa: PLC0415

        receipt = json.loads((bag / "receipt.json").read_text(encoding="utf-8"))
        receipt.pop("format", None)
        (bag / "receipt.json").write_text(canonical(receipt).decode(), encoding="utf-8")
        _write_bagit_1(bag)
        events = canonical(self.workshop.store.events(task))
        with self.assertRaises(FairyError) as caught:
            self.workshop.deliver(task)
        self.assertEqual(caught.exception.code, "version")
        repaired = self.workshop.deliver(task, repair=True)
        self.assertEqual(repaired["state"], "validated")
        self.assertEqual(canonical(self.workshop.store.events(task)), events)
        quarantines = sorted((self.home / "deliveries" / task).glob(".quarantine-*"))
        self.assertEqual(len(quarantines), 1)
        self.assertTrue((quarantines[0] / "receipt.json").is_file())
        rewritten = parse_json(Path(repaired["receipt_path"]).read_text(encoding="utf-8"))
        self.assertEqual(rewritten["format"], 2)
        again = self.workshop.deliver(task, repair=True)
        self.assertEqual(again["bag_path"], repaired["bag_path"])
        self.assertEqual(len(sorted((self.home / "deliveries" / task).glob(".quarantine-*"))), 1)

    def test_repair_interruption_keeps_old_object_and_recovery(self) -> None:
        task = self.workshop.start("Repair interruption")
        self.produce(task)
        closed = self.complete(task)
        bag = Path(closed["bag_path"])
        (bag / "receipt.json").write_text("{}", encoding="utf-8")
        original_rename = Path.rename
        calls = {"count": 0}

        def failing_rename(self_path: Path, target: Path) -> Path:
            calls["count"] += 1
            if calls["count"] == 2:
                raise OSError("fixture publish interruption")
            return original_rename(self_path, target)

        with patch.object(Path, "rename", failing_rename), self.assertRaises(FairyError) as caught:
            self.workshop.deliver(task, repair=True)
        details = caught.exception.details
        self.assertEqual(details["completed"], ["staging_validated", "quarantine"])
        self.assertFalse(bag.exists())
        quarantines = sorted((self.home / "deliveries" / task).glob(".quarantine-*"))
        self.assertEqual(len(quarantines), 1)
        self.assertEqual((quarantines[0] / "receipt.json").read_text(encoding="utf-8"), "{}")
        self.assertEqual(self.workshop.state(task).outcome, "complete")
        recovered = self.workshop.deliver(task)
        self.assertEqual(recovered["state"], "validated")
        self.assertTrue(bag.exists())

    def test_valid_bag_is_reused_not_replaced_by_repair(self) -> None:
        task = self.workshop.start("Valid repair")
        self.produce(task)
        closed = self.complete(task)
        digest = hashlib.sha256((Path(closed["bag_path"]) / "receipt.json").read_bytes()).hexdigest()
        again = self.workshop.deliver(task, repair=True)
        self.assertEqual(again["bag_path"], closed["bag_path"])
        self.assertEqual(
            hashlib.sha256((Path(again["bag_path"]) / "receipt.json").read_bytes()).hexdigest(), digest
        )
        self.assertEqual(list((self.home / "deliveries" / task).glob(".quarantine-*")), [])

    def test_checker_registry_change_keeps_receipt_and_updates_assessment(self) -> None:
        task = self.workshop.start("Receipt stability")
        self.produce(task)
        closed = self.complete(task)
        receipt = Path(closed["receipt_path"]).read_bytes()
        from astrofairy._capabilities import Capability  # noqa: PLC0415

        with Workshop(self.home) as other:
            shared = other.capabilities["snapshot.check"]
            other.register(
                "snapshot.check",
                Capability(
                    shared.effect,
                    shared.handler,
                    description="Changed checker definition",
                    input_schema=shared.input_schema,
                ),
                replace=True,
            )
            packet = other.next(task)
            self.assertEqual(packet["action"], "verify_delivery")
            self.assertNotEqual(
                packet["acceptance"]["assessment"]["checker_contracts"]["snapshot.check"],
                self.workshop._checker_contracts()["snapshot.check"],
            )
            validated = other.deliver(task)
            self.assertEqual(validated["bag_path"], closed["bag_path"])
            self.assertEqual(Path(validated["receipt_path"]).read_bytes(), receipt)

    def test_precommit_failure_is_not_reported_as_committed(self) -> None:
        task = self.workshop.start(
            "Pre-commit",
            spec={"criteria": [{"id": "goal", "description": "Relevant", "checker": "semantic"}]},
        )
        with self.assertRaises(FairyError) as caught:
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.assertNotIn("committed", caught.exception.as_dict())
        self.assertIsNone(self.workshop.state(task).outcome)

    def test_deferred_control_retains_delivery_identity(self) -> None:
        from astrofairy._presentation import encode_response  # noqa: PLC0415

        task = self.workshop.start("Deferred")
        packet = {
            "action": "deliver",
            "task": task,
            "seq": 4,
            "acceptance": {"complete": True},
            "delivery": {
                "state": "failed",
                "task": task,
                "seq": 4,
                "committed": True,
                "committed_seq": 4,
                "target": str(self.home / "deliveries" / task / "4"),
                "error": {"error": "integrity", "message": "fixture"},
                "recovery": {"command": f"deliver {task}", "repeats_effect": False},
            },
            "padding": "x" * 30000,
        }
        decoded = json.loads(encode_response(self.home, packet, task=task))
        self.assertTrue(decoded["deferred"])
        control = decoded["control"]
        self.assertEqual(control["delivery"]["state"], "failed")
        self.assertTrue(control["delivery"]["committed"])
        self.assertEqual(control["delivery"]["error"], "integrity")
        self.assertEqual(control["delivery"]["recovery"], f"deliver {task}")
        self.assertEqual(control["delivery"]["seq"], 4)

    def test_concurrent_delivery_after_deletion_serializes(self) -> None:
        task = self.workshop.start("Concurrent")
        self.produce(task)
        closed = self.complete(task)
        shutil.rmtree(closed["bag_path"])

        def run() -> dict[str, Any]:
            with Workshop(self.home) as worker:
                return worker.deliver(task)

        pool = ThreadPoolExecutor(max_workers=2)
        self.addCleanup(pool.shutdown)
        results = [future.result(timeout=30) for future in (pool.submit(run), pool.submit(run))]
        self.assertEqual(results[0]["bag_path"], results[1]["bag_path"])
        import bagit  # noqa: PLC0415

        self.assertTrue(bagit.Bag(results[0]["bag_path"]).validate())

    def test_restored_closed_task_offers_deliver(self) -> None:
        from astrofairy._maintenance import backup_state, restore_state  # noqa: PLC0415

        task = self.workshop.start("Restore")
        self.produce(task)
        self.complete(task)
        backup = Path(self.temporary.name) / "backup"
        backup_state(self.home, backup)
        recovered = Path(self.temporary.name) / "recovered"
        restore_state(backup, recovered)
        with Workshop(recovered) as restored:
            packet = restored.next(task)
            self.assertEqual(packet["action"], "deliver")
            self.assertEqual(packet["delivery"]["state"], "absent")
            validated = restored.deliver(task)
            self.assertEqual(validated["state"], "validated")
            _verify(Path(validated["bag_path"]))

    def test_short_lived_staging_cleanup_does_not_touch_quarantine(self) -> None:
        task = self.workshop.start("Staging cleanup")
        self.produce(task)
        closed = self.complete(task)
        root = Path(closed["bag_path"]).parent
        stale = root / ".staging-fixture"
        stale.mkdir()
        (stale / "partial").write_text("partial", encoding="utf-8")
        quarantine = root / ".quarantine-fixture"
        quarantine.mkdir()
        (quarantine / "keep").write_text("keep", encoding="utf-8")
        shutil.rmtree(closed["bag_path"])
        rebuilt = self.workshop.deliver(task)
        self.assertFalse(stale.exists())
        self.assertTrue((quarantine / "keep").is_file())
        self.assertEqual(rebuilt["state"], "validated")
