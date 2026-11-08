from __future__ import annotations

import ntpath
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import patch

from astrofairy import FairyError, _delivery
from astrofairy._delivery import _manifest_identity
from astrofairy.tests._support import WorkshopTest


class DeliveryBoundaryTests(WorkshopTest):
    def ready_task(self) -> str:
        task = self.workshop.start("Deliver a boundary-checked result")
        self.produce(task)
        self.refine(task)
        self.workshop.submit(task, {"op": "check"})
        self.semantic(task)
        return task

    def closed_task(self) -> tuple[str, Path]:
        task = self.ready_task()
        response = self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        delivery = response["delivery"]
        self.assertEqual(delivery["state"], "validated")
        return task, Path(delivery["bag_path"])

    def test_windows_manifest_representation_is_converted_before_classification(self) -> None:
        task, final = self.closed_task()
        bag_type, validation_error, make_bag = _delivery._bagit()

        class WindowsBag(bag_type):  # type: ignore[misc, valid-type]
            def __init__(self, path: str) -> None:
                super().__init__(path)
                self.entries = {ntpath.normpath(key): value for key, value in self.entries.items()}

            def validate(self) -> bool:
                return bool(bag_type(self.path).validate())

            def payload_entries(self) -> dict[str, Any]:
                return {key: value for key, value in self.entries.items() if key.startswith("data\\")}

        state = self.workshop.state(task)
        inspection = self.workshop._inspection(state)
        with patch("astrofairy._delivery._bagit", return_value=(WindowsBag, validation_error, make_bag)):
            _delivery._verify(final, state, self.workshop.store, inspection)

    def test_converted_keys_must_not_collide(self) -> None:
        task, final = self.closed_task()

        class CollidingBag:
            def __init__(self, _path: str) -> None:
                self.entries = {"data\\a.txt": {}, "data/a.txt": {}}

            def validate(self) -> bool:
                return True

            def payload_entries(self) -> dict[str, Any]:
                return dict(self.entries)

            def tagmanifest_files(self) -> list[str]:
                return []

        state = self.workshop.state(task)
        inspection = self.workshop._inspection(state)
        with (
            patch("astrofairy._delivery._bagit", return_value=(CollidingBag, Exception, None)),
            self.assertRaisesRegex(FairyError, "collide"),
        ):
            _delivery._verify(final, state, self.workshop.store, inspection)

    def test_manifest_identities_reject_escapes_and_foreign_absolute_paths(self) -> None:
        root = Path(self.temporary.name) / "bag"
        self.assertEqual(_manifest_identity("data\\sub\\file.txt", root), "data/sub/file.txt")
        self.assertEqual(_manifest_identity("data//sub/file.txt", root), "data/sub/file.txt")
        for raw, message in (
            ("..\\evil.txt", "escapes"),
            ("C:\\outside.txt", "foreign absolute"),
            ("\\\\server\\share\\file.txt", "UNC"),
            ("/etc/passwd", "outside the bag root"),
        ):
            with self.subTest(raw=raw), self.assertRaisesRegex(FairyError, message):
                _manifest_identity(raw, root)

    def test_ancestor_redirect_is_refused_without_touching_the_target(self) -> None:
        task = self.ready_task()
        external = Path(self.temporary.name) / "outside"
        external.mkdir()
        (self.home / "deliveries").symlink_to(external, target_is_directory=True)
        response = self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        delivery = response["delivery"]
        self.assertEqual(delivery["state"], "failed")
        self.assertTrue(delivery["committed"])
        self.assertEqual(delivery["error"]["error"], "unsafe_delivery")
        self.assertEqual(list(external.iterdir()), [])
        self.assertEqual(self.workshop.state(task).outcome, "complete")
        self.assertEqual(self.workshop.next(task)["action"], "inspect_delivery")

    def test_task_root_redirect_is_refused(self) -> None:
        task = self.ready_task()
        external = Path(self.temporary.name) / "outside"
        external.mkdir()
        (self.home / "deliveries").mkdir()
        (self.home / "deliveries" / task).symlink_to(external, target_is_directory=True)
        response = self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.assertEqual(response["delivery"]["state"], "failed")
        self.assertEqual(list(external.iterdir()), [])
        self.assertEqual(self.workshop.next(task)["action"], "inspect_delivery")

    def test_target_redirect_and_linked_payload_are_refused(self) -> None:
        task, final = self.closed_task()
        external = Path(self.temporary.name) / "outside"
        external.mkdir()
        shutil.rmtree(final)
        final.symlink_to(external, target_is_directory=True)
        with self.assertRaises(FairyError) as caught:
            self.workshop.deliver(task)
        self.assertEqual(caught.exception.code, "unsafe_delivery")
        self.assertEqual(list(external.iterdir()), [])
        final.unlink()
        regenerated = self.workshop.deliver(task)
        bag_path = Path(regenerated["bag_path"])
        (bag_path / "data" / "linked").symlink_to(external, target_is_directory=True)
        with self.assertRaises(FairyError) as caught:
            self.workshop.deliver(task)
        self.assertEqual(caught.exception.code, "unsafe_delivery")
        self.assertEqual(list(external.iterdir()), [])
