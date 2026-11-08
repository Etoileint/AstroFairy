from __future__ import annotations

import hashlib
import os
import shutil
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from functools import partial
from pathlib import Path
from typing import Any
from unittest.mock import patch

import bagit

from astrofairy import FairyError, Workshop
from astrofairy._contracts import parse_json
from astrofairy._limits import LIMITS
from astrofairy._maintenance import audit_state, backup_state, restore_state
from astrofairy.tests._support import WorkshopTest


class BagDeliveryTests(WorkshopTest):
    def complete(self, task: str) -> dict[str, Any]:
        self.workshop.submit(task, {"op": "check"})
        self.semantic(task)
        return self.workshop.submit(task, {"op": "close", "outcome": "complete"})["delivery"]

    def multi_member_task(self) -> tuple[str, dict[str, Any]]:
        task = self.workshop.start(
            "Deliver a report and data",
            spec={
                "criteria": [
                    {"id": "goal", "description": "Relevant", "checker": "semantic"},
                    {
                        "id": "usable",
                        "description": "Nonempty",
                        "checker": "nonempty",
                        "scope": "collection",
                    },
                ],
                "required_roles": ["report", "data"],
            },
        )
        report = self.produce(task, "report body", publish=False, path="report.md")
        data = self.produce(task, "a,1\n", publish=False, path="data/data.csv")
        self.publish(task, [report, data], roles=["report", "data"])
        return task, self.complete(task)

    def test_bagit_delivery_members_receipt_and_full_validation(self) -> None:
        task, delivery = self.multi_member_task()
        bag = Path(delivery["bag_path"])
        self.assertEqual(
            sorted(path.name for path in bag.iterdir()),
            [
                "README.txt",
                "bag-info.txt",
                "bagit.txt",
                "data",
                "manifest-sha256.txt",
                "receipt.json",
                "tagmanifest-sha256.txt",
            ],
        )
        self.assertEqual(
            sorted(Path(name).as_posix() for name in bagit.Bag(str(bag)).payload_entries()),
            ["data/data/data.csv", "data/report.md"],
        )
        self.assertTrue(bagit.Bag(str(bag)).validate())
        self.assertEqual(
            sorted(delivery["files"]),
            ["data/data.csv", "report.md"],
        )
        for path in delivery["files"].values():
            self.assertTrue(Path(path).is_file())
        self.assertNotIn("receipt.json", bagit.Bag(str(bag)).payload_entries())
        self.assertTrue((bag / "README.txt").is_file())
        receipt = parse_json((bag / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["snapshot"], self.workshop.state(task).snapshot)
        self.assertEqual(receipt["delivery_files"]["data/report.md"]["role"], "report")
        self.assertEqual(receipt["delivery_files"]["data/data/data.csv"]["role"], "data")
        self.assertEqual(receipt["bag"]["validation"], "full")
        again = self.workshop.deliver(task)
        self.assertEqual(again["bag_path"], delivery["bag_path"])
        self.assertTrue(bagit.Bag(str(bag)).validate())

    @unittest.skipUnless(os.name == "posix", "POSIX file modes; native redirect tests cover Windows paths")
    def test_posix_delivery_permissions(self) -> None:
        _task, delivery = self.multi_member_task()
        for path in delivery["files"].values():
            self.assertEqual(Path(path).stat().st_mode & 0o777, 0o600)
        self.assertEqual((Path(delivery["bag_path"]) / "data").stat().st_mode & 0o777, 0o700)

    def test_tampered_missing_extra_and_tag_changes_are_refused(self) -> None:
        task, delivery = self.multi_member_task()
        bag = Path(delivery["bag_path"])
        pristine = Path(self.temporary.name) / "pristine"
        shutil.copytree(bag, pristine)

        def restore() -> None:
            shutil.rmtree(bag)
            shutil.copytree(pristine, bag)

        mutations = [
            partial((bag / "data" / "report.md").write_bytes, b"changed"),
            partial((bag / "data" / "data" / "data.csv").unlink),
            partial((bag / "data" / "extra.txt").write_bytes, b"extra"),
            partial((bag / "receipt.json").write_bytes, b"{}"),
            partial((bag / "README.txt").unlink),
            partial((bag / "extra.txt").write_bytes, b"extra tag"),
        ]
        for mutation in mutations:
            restore()
            mutation()
            with self.assertRaises(FairyError) as caught:
                self.workshop.deliver(task)
            self.assertEqual(caught.exception.code, "integrity")
        restore()

    def test_failed_generation_leaves_no_published_mixed_state_and_retry_succeeds(self) -> None:
        task, delivery = self.multi_member_task()
        final = Path(delivery["bag_path"])
        shutil.rmtree(final)
        with (
            patch("bagit.make_bag", side_effect=RuntimeError("fixture generation failure")),
            self.assertRaises(FairyError) as caught,
        ):
            self.workshop.deliver(task)
        self.assertEqual(caught.exception.code, "integrity")
        self.assertFalse(final.exists())
        self.assertEqual(list((self.home / "deliveries" / task).glob(".staging-*")), [])
        delivery = self.workshop.deliver(task)
        self.assertEqual(delivery["seq"], self.workshop.state(task).seq)
        self.assertTrue(bagit.Bag(delivery["bag_path"]).validate())

    def test_workspace_change_after_capture_does_not_change_delivered_bytes(self) -> None:
        task = self.workshop.start(
            "Capture then change",
            spec={
                "criteria": [
                    {"id": "goal", "description": "Relevant", "checker": "semantic"},
                    {
                        "id": "usable",
                        "description": "Nonempty",
                        "checker": "nonempty",
                        "scope": "collection",
                    },
                ]
            },
        )
        workspace = Path(self.workshop.next(task)["workspace"])
        (workspace / "draft.txt").write_bytes(b"original bytes")
        captured = self.workshop.invoke(task, "file.capture", {"path": "draft.txt"})["outputs"][0]
        self.publish(task, [captured], roles=["main"])
        (workspace / "draft.txt").write_bytes(b"changed after capture")
        delivery = self.complete(task)
        self.assertEqual(Path(delivery["files"]["draft.txt"]).read_bytes(), b"original bytes")

    def test_concurrent_delivery_returns_one_valid_bag(self) -> None:
        task, _delivery = self.multi_member_task()

        def run() -> dict[str, Any]:
            with Workshop(self.home) as worker:
                return worker.deliver(task)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=30) for future in (pool.submit(run), pool.submit(run))]
        self.assertEqual(results[0]["bag_path"], results[1]["bag_path"])
        self.assertTrue(bagit.Bag(results[0]["bag_path"]).validate())

    def test_cancelled_task_without_snapshot_gets_valid_empty_bag(self) -> None:
        task = self.workshop.start("No artifact")
        delivery = self.workshop.submit(task, {"op": "close", "outcome": "cancelled"})["delivery"]
        self.assertEqual(delivery["files"], {})
        self.assertIsNone(delivery["artifact_path"])
        bag = Path(delivery["bag_path"])
        self.assertTrue(bagit.Bag(str(bag)).validate())
        self.assertEqual(bagit.Bag(str(bag)).payload_entries(), {})
        self.assertTrue((bag / "manifest-sha256.txt").is_file())
        self.assertTrue((bag / "receipt.json").is_file())
        self.assertTrue((bag / "README.txt").is_file())

    def test_streaming_capture_large_member_and_aggregate_limits(self) -> None:
        task = self.workshop.start(
            "Large streaming capture",
            spec={
                "criteria": [
                    {"id": "goal", "description": "Relevant", "checker": "semantic"},
                    {
                        "id": "usable",
                        "description": "Nonempty",
                        "checker": "nonempty",
                        "scope": "collection",
                    },
                ]
            },
        )
        workspace = Path(self.workshop.next(task)["workspace"])
        payload = b"streamed" * (1024 * 1024)
        source = workspace / "large.bin"
        source.write_bytes(payload)
        captured = self.workshop.invoke(task, "file.capture", {"path": "large.bin"})["outputs"][0]
        self.assertEqual(captured["bytes"], len(payload))
        self.assertEqual(self.workshop.store.length(captured["ref"]), len(payload))
        self.publish(task, [captured], roles=["main"])
        delivery = self.complete(task)
        delivered = Path(delivery["files"]["large.bin"]).read_bytes()
        self.assertEqual(hashlib.sha256(delivered).hexdigest(), hashlib.sha256(payload).hexdigest())
        aggregate = self.workshop.start("Aggregate limit")
        small = Path(self.workshop.next(aggregate)["workspace"]) / "small.bin"
        small.write_bytes(b"12345")
        with patch("astrofairy._capabilities.LIMITS", replace(LIMITS, task_capture_bytes=4)):
            result = self.workshop.invoke(aggregate, "file.capture", {"path": "small.bin"})
        self.assertEqual((result["status"], result["result"]["error"]), ("failed", "limit"))
        with patch("astrofairy._capabilities.LIMITS", replace(LIMITS, content_bytes=4)):
            result = self.workshop.invoke(aggregate, "file.capture", {"path": "small.bin"})
        self.assertEqual((result["status"], result["result"]["error"]), ("failed", "limit"))

    def test_backup_restore_retains_all_members_and_snapshots(self) -> None:
        task = self.workshop.start(
            "Two snapshots",
            spec={
                "criteria": [
                    {"id": "goal", "description": "Relevant", "checker": "semantic"},
                    {
                        "id": "usable",
                        "description": "Nonempty",
                        "checker": "nonempty",
                        "scope": "collection",
                    },
                ]
            },
        )
        first = self.produce(task, "first", publish=False, path="a.txt")
        self.publish(task, [first], roles=["main"])
        second = self.produce(task, "second", publish=False, path="b.txt")
        self.publish(task, [first, second], roles=["main", "extra"])
        delivery = self.complete(task)
        before = audit_state(self.home)
        backup = Path(self.temporary.name) / "backup"
        backup_state(self.home, backup)
        recovered = Path(self.temporary.name) / "recovered"
        restore_state(backup, recovered)
        with Workshop(recovered) as restored:
            self.assertGreaterEqual(len(restored.state(task).snapshots), 2)
            self.assertEqual(
                {member["path"] for member in restored.state(task).snapshot["members"]},
                {"a.txt", "b.txt"},
            )
            regenerated = restored.deliver(task)
            self.assertEqual(regenerated["seq"], delivery["seq"])
            self.assertEqual(
                Path(regenerated["files"]["b.txt"]).read_bytes(),
                Path(delivery["files"]["b.txt"]).read_bytes(),
            )
        self.assertEqual(audit_state(recovered), before)
