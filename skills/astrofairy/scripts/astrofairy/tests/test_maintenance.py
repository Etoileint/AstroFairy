from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

from astrofairy import FairyError, Workshop, _maintenance
from astrofairy._contracts import canonical, parse_json
from astrofairy._documents import audit_document, freeze
from astrofairy._maintenance import audit_state, backup_state, restore_state, verify_backup
from astrofairy._presentation import read_document
from astrofairy._store import Store
from astrofairy.tests._support import WorkshopTest

if TYPE_CHECKING:
    from collections.abc import Iterator


class MaintenanceTests(WorkshopTest):
    def test_absent_archive_is_allowed_but_dangling_archive_is_not_omitted(self) -> None:
        self.workshop.start("Optional archive admission")
        self.assertEqual(audit_state(self.home)["documents"], 0)
        backup_state(self.home, self.home.parent / "absent-archive")
        (self.home / "documents.sqlite3").symlink_to(self.home / "missing-target")
        with self.assertRaises(FairyError):
            audit_state(self.home)
        partial = self.home.parent / "invalid-archive"
        with self.assertRaises(FairyError):
            backup_state(self.home, partial)
        self.assertFalse((partial / "manifest.json").exists())

    def test_single_event_reply_uses_one_verified_prestate_and_exact_commit_sequence(self) -> None:
        task = self.workshop.start("Measure admitted feedback")
        events = Store.events
        loads = []

        def load(store: Store, identity: str) -> list[dict[str, Any]]:
            loads.append(identity)
            return events(store, identity)

        with patch.object(Store, "events", load):
            reply = self.workshop.submit(task, {"op": "feedback", "text": "Useful result"})
        self.assertEqual(loads, [task])
        self.assertEqual(reply["seq"], 2)
        original = self.workshop.store.transaction
        with Workshop(self.home) as other:

            @contextmanager
            def intervening() -> Iterator[None]:
                with original():
                    yield
                other.submit(task, {"op": "feedback", "text": "A later committed fact"})

            with patch.object(self.workshop.store, "transaction", intervening):
                reply = self.workshop.submit(task, {"op": "feedback", "text": "This committed fact"})
        self.assertEqual(reply["seq"], 3)
        self.assertEqual(self.workshop.state(task).seq, 4)
        self.workshop.store.connection.execute("UPDATE events SET payload = '{}' WHERE seq = 1")
        with self.assertRaises(FairyError):
            self.workshop.submit(task, {"op": "feedback", "text": "Must refuse corrupt history"})

    def test_backup_restore_retains_documents_pins_pending_calls_and_delivery(self) -> None:
        ref = self.workshop.library.propose(self.proposal())
        validation = self.workshop.validation_task(ref)
        self.finish(validation, "asset-fitness")
        self.workshop.library.adopt(ref, validation)
        task = self.workshop.start("Use a retained guide")
        self.workshop.invoke(task, "asset.read", {"ref": ref})
        self.produce(task)
        delivery = self.finish(task)
        child = self.workshop.learning_task(task)
        locator = self.workshop.state(child).inputs[0]["source_document"]
        external = freeze(self.home, {"outside": "retained handle"})
        pending = self.workshop.start("Pending work remains pending")
        call = self.workshop.submit(pending, {"op": "request", "purpose": "Wait for result"})
        self.workshop.library.retire(ref)
        before = audit_state(self.home)
        backup = self.home.parent / "backup"
        result = backup_state(self.home, backup)
        self.assertEqual(result["counts"], before)
        self.assertEqual(verify_backup(backup)["counts"], before)
        recovered = self.home.parent / "recovered"
        self.assertEqual(restore_state(backup, recovered)["counts"], before)
        self.assertFalse((recovered / "restore.pending").exists())
        with Workshop(recovered) as restored:
            self.assertEqual(restored.library.get(ref), self.workshop.library.get(ref))
            self.assertEqual(restored.library.status(ref), "retired")
            self.assertIn(ref, restored.state(task).assets)
            self.assertEqual(restored.state(pending).calls[call["call"]]["status"], "pending")
            self.assertTrue(Path(restored.next(pending)["workspace"]).is_dir())
            regenerated = restored.deliver(task)
            self.assertEqual(
                Path(regenerated["artifact_path"]).read_bytes(), Path(delivery["artifact_path"]).read_bytes()
            )
        self.assertEqual(audit_document(recovered, locator["document"], task=task)["seq"], locator["seq"])
        self.assertEqual(
            read_document(recovered, external["document"], pointer="/outside")["text"], '"retained handle"'
        )

    def test_main_first_backup_keeps_later_archive_superset(self) -> None:
        task = self.workshop.start("Source before copy")
        self.produce(task)
        self.finish(task)
        first = self.workshop.learning_task(task)
        copy = _maintenance._copy_database
        later = []

        def interleave(source: Path, target: Path) -> None:
            copy(source, target)
            if source.name == "workshop.sqlite3":
                self.workshop.submit(task, {"op": "feedback", "text": "After the main snapshot"})
                later.append(self.workshop.learning_task(task))

        target = self.home.parent / "ordered"
        with patch.object(_maintenance, "_copy_database", interleave):
            backup_state(self.home, target)
        captured = _maintenance._ReadOnly(target)
        try:
            self.assertIn(first, captured.tasks())
            self.assertNotIn(later[0], captured.tasks())
        finally:
            captured.close()
        self.assertEqual(audit_state(target)["documents"], 2)

    def test_failed_restore_keeps_marker_and_blocks_normal_store_before_ddl(self) -> None:
        self.workshop.start("Preserve failure")
        backup = self.home.parent / "backup"
        backup_state(self.home, backup)
        target = self.home.parent / "failed"
        audit = _maintenance.audit_state

        def interrupted(home: Path) -> dict[str, Any]:
            if home == target:
                raise OSError("private injected failure")
            return audit(home)

        with patch.object(_maintenance, "audit_state", interrupted), self.assertRaises(OSError):
            restore_state(backup, target)
        self.assertTrue((target / "restore.pending").exists())
        before = (target / "workshop.sqlite3").read_bytes()
        with self.assertRaises(FairyError) as caught:
            Workshop(target)
        self.assertEqual(caught.exception.code, "incomplete_restore")
        self.assertEqual((target / "workshop.sqlite3").read_bytes(), before)

    def test_manifest_mutations_symlink_existing_destination_and_missing_ref_refuse(self) -> None:
        task = self.workshop.start("Capture a referenced blob")
        ref = self.produce(task)
        backup = self.home.parent / "backup"
        backup_state(self.home, backup)
        path = backup / "manifest.json"
        original = path.read_bytes()
        manifest = parse_json(original.decode())
        variants = [
            {**manifest, "extra": True},
            {**manifest, "store": 6},
            {**manifest, "files": {"../escape": {"bytes": 0, "sha256": "0" * 64}}},
        ]
        for value in variants:
            path.write_bytes(canonical(value))
            with self.assertRaises(FairyError):
                verify_backup(backup)
        path.write_bytes(original)
        extra = backup / "unexpected"
        extra.touch()
        with self.assertRaises(FairyError):
            verify_backup(backup)
        extra.unlink()
        with self.assertRaises(FileExistsError):
            backup_state(self.home, backup)
        with self.assertRaises(FileExistsError):
            restore_state(backup, self.home)
        image = backup / "workshop.sqlite3"
        saved = backup.parent / "saved.sqlite3"
        image.rename(saved)
        image.symlink_to(saved)
        with self.assertRaises(FairyError):
            verify_backup(backup)
        self.workshop.store.connection.execute("DELETE FROM blobs WHERE ref = ?", (ref,))
        with self.assertRaises(FairyError):
            audit_state(self.home)

    def test_typed_locator_archive_and_asset_metadata_corruption_refuse(self) -> None:
        ref = self.workshop.library.propose(self.proposal())
        self.workshop.store.connection.execute("UPDATE assets SET summary = 'changed'")
        with self.assertRaises(FairyError):
            audit_state(self.home)
        self.workshop.store.connection.execute("UPDATE assets SET summary = ?", (self.proposal()["summary"],))
        task = self.workshop.validation_task(ref)
        self.finish(task, "asset-fitness")
        child = self.workshop.learning_task(task)
        source = self.workshop.state(child).inputs[0]["source_document"]
        with sqlite3.connect(self.home / "documents.sqlite3") as connection:
            connection.execute("DELETE FROM nodes WHERE ref = ?", (source["document"],))
        with self.assertRaises(FairyError):
            audit_state(self.home)

    def test_backup_deadline_preserves_partial_without_manifest_and_source_bytes(self) -> None:
        self.workshop.start("Bound backup retries")
        before = (self.home / "workshop.sqlite3").read_bytes()
        target = self.home.parent / "timed-out"
        with (
            patch.object(_maintenance.time, "monotonic", side_effect=[0, 61]),
            self.assertRaises(FairyError) as caught,
        ):
            backup_state(self.home, target)
        self.assertEqual(caught.exception.code, "storage_busy")
        self.assertFalse((target / "manifest.json").exists())
        self.assertEqual((self.home / "workshop.sqlite3").read_bytes(), before)
