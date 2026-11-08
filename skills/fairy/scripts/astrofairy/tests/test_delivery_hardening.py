from __future__ import annotations

import io
import json
import os
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from typing import Any
from unittest.mock import patch

from astrofairy import FairyError, Workshop, _delivery
from astrofairy._cli import main
from astrofairy.tests._support import LiteralSearch, WorkshopTest, mock_capability


class _CommitProxy:
    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        lose_acknowledgment: bool = False,
        fail_commit_and_rollback: bool = False,
    ) -> None:
        self.connection = connection
        self.lose_acknowledgment = lose_acknowledgment
        self.fail_commit_and_rollback = fail_commit_and_rollback
        self.lost = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self.connection, name)

    def execute(self, sql: str, *parameters: Any) -> sqlite3.Cursor:
        if self.fail_commit_and_rollback:
            if sql == "COMMIT":
                raise sqlite3.OperationalError("controlled commit failure")
            if sql == "ROLLBACK":
                raise sqlite3.OperationalError("controlled rollback failure")
        if self.lose_acknowledgment and sql == "COMMIT" and not self.lost:
            self.connection.execute(sql, *parameters)
            self.lost = True
            raise sqlite3.OperationalError("controlled loss of commit acknowledgment")
        return self.connection.execute(sql, *parameters)


class _StatementProxy:
    def __init__(
        self,
        connection: sqlite3.Connection,
        kind: str,
        *,
        lose_insert_acknowledgment: bool = False,
        fail_rollback: bool = False,
    ) -> None:
        self.connection = connection
        self.kind = kind
        self.lose_insert_acknowledgment = lose_insert_acknowledgment
        self.fail_rollback = fail_rollback
        self.failed = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self.connection, name)

    def execute(self, sql: str, *parameters: Any) -> sqlite3.Cursor:
        if (
            sql.startswith("INSERT INTO events")
            and parameters
            and len(parameters[0]) >= 3
            and parameters[0][2] == self.kind
        ):
            self.failed = True
            if self.lose_insert_acknowledgment:
                self.connection.execute(sql, *parameters)
                raise sqlite3.OperationalError("controlled statement acknowledgment loss")
            raise sqlite3.OperationalError("controlled statement failure")
        if self.failed and self.fail_rollback and sql == "ROLLBACK":
            raise sqlite3.OperationalError("controlled rollback failure")
        return self.connection.execute(sql, *parameters)


class DeliveryHardeningTests(WorkshopTest):
    def ready(self) -> str:
        task = self.workshop.start("Harden delivery")
        self.produce(task)
        self.refine(task)
        self.workshop.submit(task, {"op": "check"})
        self.semantic(task)
        return task

    def complete(self, task: str) -> dict[str, Any]:
        response = self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        delivery = response["delivery"]
        self.assertEqual(delivery["state"], "validated")
        return delivery

    def test_repair_refuses_unsafe_descendants(self) -> None:
        task = self.ready()
        closed = self.complete(task)
        bag = Path(closed["bag_path"])
        external = Path(self.temporary.name) / "outside"
        external.mkdir()
        (external / "keep").write_text("sentinel", encoding="utf-8")
        self.directory_redirect(bag / "data" / "linked", external)
        with self.assertRaises(FairyError) as caught:
            self.workshop.deliver(task, repair=True)
        self.assertEqual(caught.exception.code, "unsafe_delivery")
        self.assertEqual(list((self.home / "deliveries" / task).glob(".quarantine-*")), [])
        self.assertTrue((bag / "data" / "linked").is_symlink() or (bag / "data" / "linked").is_junction())
        self.assertEqual((external / "keep").read_text(encoding="utf-8"), "sentinel")

    def test_post_commit_sqlite_export_error_preserves_recovery(self) -> None:
        task = self.ready()
        stream = io.BytesIO()
        stdout = io.TextIOWrapper(stream, encoding="utf-8")
        with patch.object(
            self.workshop.store,
            "copy_to_file",
            side_effect=sqlite3.OperationalError("controlled post-commit read failure"),
        ):
            response = self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        with (
            patch("astrofairy._cli._run", return_value=response),
            patch("astrofairy._cli.sys.stdout", stdout),
        ):
            status = main(["--home", str(self.home), "submit", task])
        self.assertEqual(status, 1)
        decoded = json.loads(stream.getvalue())
        self.assertNotIn("error", decoded)
        delivery = decoded["delivery"]
        self.assertEqual(delivery["state"], "failed")
        self.assertTrue(delivery["committed"])
        self.assertEqual(delivery["operation"], "close")
        self.assertEqual(delivery["committed_seq"], self.workshop.state(task).seq)
        self.assertEqual(delivery["error"]["error"], "storage_failed")
        self.assertIn("sqlite_code", delivery["error"])
        self.assertEqual(delivery["recovery"]["command"], f"deliver {task}")
        self.assertEqual(self.workshop.state(task).outcome, "complete")

    def test_failure_selection_identity_is_the_frozen_snapshot(self) -> None:
        task = self.ready()
        selected: dict[str, int] = {}

        def append_then_fail(
            _home: Path, state: Any, store: Any, _inspection: dict[str, Any], **_kwargs: Any
        ) -> Any:
            selected["actual"] = state.seq
            with store.transaction():
                store.append(
                    task,
                    "feedback",
                    {"text": "concurrent", "kind": "observation", "origin": "user_report"},
                    state.seq,
                )
            raise FairyError("integrity", "controlled export failure")

        with patch("astrofairy._runtime.deliver_bag", side_effect=append_then_fail):
            response = self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        delivery = response["delivery"]
        self.assertEqual(delivery["state"], "failed")
        self.assertEqual(delivery["selected_seq"], selected["actual"])
        self.assertEqual(delivery["committed_seq"], selected["actual"])
        self.assertEqual(Path(delivery["target"]), self.home / "deliveries" / task / str(selected["actual"]))
        self.assertEqual(self.workshop.state(task).seq, selected["actual"] + 1)

    def test_repair_postpublication_failure_reports_progress(self) -> None:
        task = self.ready()
        closed = self.complete(task)
        bag = Path(closed["bag_path"])
        (bag / "receipt.json").write_text("{}", encoding="utf-8")
        original = _delivery._verify
        observations = {"final_checks": 0}

        def fail_after_publication(root: Path, *args: Any, **kwargs: Any) -> None:
            if root == bag:
                observations["final_checks"] += 1
                if observations["final_checks"] == 2:
                    raise FairyError("integrity", "controlled post-publication observation failure")
            original(root, *args, **kwargs)

        with (
            patch("astrofairy._delivery._verify", side_effect=fail_after_publication),
            self.assertRaises(FairyError) as caught,
        ):
            self.workshop.deliver(task, repair=True)
        details = caught.exception.details
        self.assertTrue(details["published"])
        self.assertEqual(details["completed"], ["staging_validated", "quarantine", "publication"])
        self.assertTrue(details["quarantined"].startswith(".quarantine-"))
        self.assertEqual(json.loads((bag / "receipt.json").read_text(encoding="utf-8"))["format"], 2)
        quarantine = bag.parent / details["quarantined"]
        self.assertEqual((quarantine / "receipt.json").read_text(encoding="utf-8"), "{}")

    def test_missing_current_checkers_fail_closed_but_history_stays_valid(self) -> None:
        task = self.workshop.start(
            "Checker applicability",
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
        self.produce(task)
        self.workshop.submit(task, {"op": "check"})
        self.semantic(task)
        closed = self.complete(task)
        receipt = Path(closed["receipt_path"]).read_bytes()
        capabilities = dict(self.workshop.capabilities)
        del capabilities["snapshot.check"]
        del capabilities["content.check"]
        with Workshop(self.home, capabilities=capabilities, search=LiteralSearch(self.home)) as other:
            packet = other.next(task)
            self.assertEqual(packet["acceptance"]["assessment"]["missing_checkers"], ["snapshot.check"])
            self.assertFalse(packet["acceptance"]["complete"])
            self.assertTrue(other.inspect(task)["issues"])
            self.assertEqual(other.deliver(task)["state"], "validated")
            self.assertEqual(Path(closed["receipt_path"]).read_bytes(), receipt)

    def test_precommit_failure_reports_false_explicitly(self) -> None:
        task = self.workshop.start(
            "Pre-commit",
            spec={"criteria": [{"id": "goal", "description": "Relevant", "checker": "semantic"}]},
        )
        with self.assertRaises(FairyError) as caught:
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.assertIn("committed", caught.exception.details)
        self.assertFalse(caught.exception.details["committed"])
        self.assertIsNone(self.workshop.state(task).outcome)

    def test_unknown_write_effect_is_not_a_commit_certainty(self) -> None:
        def exploding(_context: Any, _parameters: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError("fixture write failure")

        task = self.workshop.start("Unknown write")
        self.workshop.register("fixture.write", mock_capability("write", exploding))
        observation = self.workshop.invoke(task, "fixture.write", {})
        self.assertEqual(observation["status"], "unknown")
        self.assertEqual(observation["effect_state"], "unknown")
        self.assertNotIn("committed", observation)
        self.assertNotIn("recovery", observation)
        call = self.workshop.state(task).calls[observation["call"]]
        self.assertEqual(call["status"], "unknown")
        self.assertEqual(call["effect"], "write")
        with self.assertRaises(FairyError):
            self.workshop.invoke(task, "fixture.write", {})

    def test_real_commit_busy_after_rollback_reports_not_committed(self) -> None:
        task = self.ready()
        before = self.workshop.state(task).seq
        self.workshop.store.connection.execute("PRAGMA busy_timeout = 0")
        reader = sqlite3.connect(self.home / "workshop.sqlite3", isolation_level=None)
        self.addCleanup(reader.close)
        reader.execute("BEGIN")
        reader.execute("SELECT count(*) FROM events").fetchone()
        try:
            with self.assertRaises(FairyError) as caught:
                self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        finally:
            reader.execute("ROLLBACK")
        error = caught.exception
        self.assertEqual(error.code, "storage_failed")
        self.assertIsInstance(error.details["committed"], bool)
        self.assertFalse(error.details["committed"])
        self.assertNotIn("commit", error.details)
        self.assertEqual(error.details["transaction"], "commit")
        self.assertEqual(error.details["stage"], "admission")
        self.assertEqual(error.details["task"], task)
        self.assertEqual(error.details["operation"], "close")
        self.assertEqual(error.details["seq"], before)
        self.assertEqual(error.details["rollback"], {"state": "rolled_back"})
        self.assertEqual(self.workshop.state(task).seq, before)
        self.assertIsNone(self.workshop.state(task).outcome)

    def test_lost_commit_acknowledgment_is_explicit_unknown(self) -> None:
        task = self.ready()
        before = self.workshop.state(task).seq
        real = self.workshop.store.connection
        proxy = _CommitProxy(real, lose_acknowledgment=True)
        self.workshop.store.connection = proxy
        try:
            with self.assertRaises(FairyError) as caught:
                self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        finally:
            self.workshop.store.connection = real
        error = caught.exception
        self.assertEqual(error.code, "storage_failed")
        self.assertEqual(error.details["committed"], "unknown")
        self.assertNotIn("commit", error.details)
        self.assertEqual(error.details["transaction"], "commit")
        self.assertEqual(error.details["task"], task)
        self.assertEqual(error.details["operation"], "close")
        self.assertEqual(error.details["seq"], before)
        self.assertTrue(proxy.lost)
        self.assertIsInstance(error.__cause__.__cause__, sqlite3.OperationalError)
        self.assertEqual(str(error.__cause__.__cause__), "controlled loss of commit acknowledgment")
        state = self.workshop.state(task)
        self.assertEqual(state.seq, before + 1)
        self.assertEqual(state.outcome, "complete")
        with Workshop(self.home) as reopened:
            self.assertEqual(reopened.state(task).seq, before + 1)
            self.assertEqual(reopened.state(task).outcome, "complete")

    def test_commit_error_is_not_masked_by_rollback_failure(self) -> None:
        task = self.ready()
        before = self.workshop.state(task).seq
        real = self.workshop.store.connection
        proxy = _CommitProxy(real, fail_commit_and_rollback=True)
        self.workshop.store.connection = proxy
        try:
            with self.assertRaises(FairyError) as caught:
                self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        finally:
            self.workshop.store.connection = real
            if real.in_transaction:
                real.execute("ROLLBACK")
        error = caught.exception
        self.assertEqual(error.code, "storage_failed")
        self.assertEqual(error.details["committed"], "unknown")
        self.assertEqual(error.details["transaction"], "commit")
        self.assertEqual(error.details["task"], task)
        self.assertEqual(error.details["operation"], "close")
        self.assertIn("rollback", error.details)
        self.assertIsInstance(error.__cause__.__cause__, sqlite3.OperationalError)
        self.assertEqual(str(error.__cause__.__cause__), "controlled commit failure")
        self.assertEqual(self.workshop.state(task).seq, before)
        self.assertIsNone(self.workshop.state(task).outcome)

    def test_observed_append_failure_preserves_invoked_identity_and_effect(self) -> None:
        task = self.workshop.start("Observe boundary")
        before = self.workshop.state(task).seq
        sentinel = Path(self.temporary.name) / "external-effect.txt"

        def write_effect(_context: Any, _parameters: dict[str, Any]) -> dict[str, Any]:
            sentinel.write_text("completed", encoding="utf-8")
            return {"outputs": []}

        self.workshop.register("fixture.write", mock_capability("write", write_effect))
        original_append = self.workshop._append

        def refuse_observation(state: Any, kind: str, payload: dict[str, Any]) -> None:
            if kind == "observed":
                raise FairyError("integrity", "controlled observation append refusal")
            original_append(state, kind, payload)

        with (
            patch.object(self.workshop, "_append", side_effect=refuse_observation),
            self.assertRaises(FairyError) as caught,
        ):
            self.workshop.invoke(task, "fixture.write", {})
        error = caught.exception
        self.assertEqual(error.code, "integrity")
        self.assertEqual(error.details["task"], task)
        self.assertEqual(error.details["stage"], "observed")
        self.assertIsInstance(error.details["committed"], bool)
        self.assertTrue(error.details["committed"])
        self.assertNotIn("commit", error.details)
        self.assertEqual(error.details["committed_seq"], before + 1)
        self.assertTrue(error.details["invoked"])
        self.assertEqual(error.details["effect_state"], "ok")
        self.assertIsInstance(error.details["observed"], bool)
        self.assertFalse(error.details["observed"])
        self.assertEqual(
            error.details["recovery"]["action"],
            "Inspect the recorded invocation and any external effect; do not repeat the write",
        )
        self.assertEqual(error.details["recovery"]["command"], f"inspect {task} --history")
        call = self.workshop.state(task).calls[error.details["call"]]
        self.assertEqual(call["status"], "pending")
        self.assertEqual(call["invoked_seq"], before + 1)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "completed")

    @unittest.skipUnless(
        os.name == "posix", "POSIX directory DAC; native junction and denied-walk tests run on Windows"
    )
    def test_unreadable_old_tree_is_not_quarantined_or_followed(self) -> None:
        task = self.ready()
        closed = self.complete(task)
        bag = Path(closed["bag_path"])
        (bag / "receipt.json").write_text("{}", encoding="utf-8")
        external = Path(self.temporary.name) / "outside"
        external.mkdir()
        (external / "keep").write_text("sentinel", encoding="utf-8")
        blocked = bag / "data" / "blocked"
        blocked.mkdir()
        (blocked / "link").symlink_to(external, target_is_directory=True)
        blocked.chmod(0)
        self.addCleanup(blocked.chmod, 0o700)
        with self.assertRaises(FairyError) as caught:
            self.workshop.deliver(task, repair=True)
        blocked.chmod(0o700)
        self.assertEqual(caught.exception.code, "unsafe_delivery")
        self.assertEqual(caught.exception.details["reason"], "unreadable_subtree")
        self.assertEqual(list(bag.parent.glob(".quarantine-*")), [])
        self.assertTrue(bag.is_dir())
        self.assertTrue((blocked / "link").is_symlink())
        self.assertEqual((external / "keep").read_text(encoding="utf-8"), "sentinel")

    def test_denied_tree_walk_refuses_repair_on_every_platform(self) -> None:
        task = self.ready()
        closed = self.complete(task)
        bag = Path(closed["bag_path"])
        (bag / "receipt.json").write_bytes(b"{}")
        walk = os.walk

        def denied(path: Any, *args: Any, **kwargs: Any) -> Any:
            if Path(path) == bag:
                kwargs["onerror"](PermissionError("controlled directory traversal denial"))
                return iter(())
            return walk(path, *args, **kwargs)

        with (
            patch("astrofairy._delivery.os.walk", side_effect=denied),
            self.assertRaises(FairyError) as caught,
        ):
            self.workshop.deliver(task, repair=True)
        self.assertEqual(caught.exception.code, "unsafe_delivery")
        self.assertEqual(caught.exception.details["reason"], "unreadable_subtree")
        self.assertTrue(bag.is_dir())
        self.assertEqual(list(bag.parent.glob(".quarantine-*")), [])

    def test_postpublication_guard_failure_reports_full_progress(self) -> None:
        task = self.ready()
        closed = self.complete(task)
        bag = Path(closed["bag_path"])
        (bag / "receipt.json").write_text("{}", encoding="utf-8")
        original_lstat = Path.lstat
        observed = {"postpublication": False}

        def failing_lstat(path: Path, *args: Any, **kwargs: Any) -> Any:
            if path == bag and list(bag.parent.glob(".quarantine-*")) and (bag / "receipt.json").exists():
                observed["postpublication"] = True
                raise PermissionError("controlled final directory inspection failure")
            return original_lstat(path, *args, **kwargs)

        with patch.object(Path, "lstat", failing_lstat), self.assertRaises(FairyError) as caught:
            self.workshop.deliver(task, repair=True)
        self.assertTrue(observed["postpublication"])
        error = caught.exception
        self.assertEqual(error.code, "unsafe_delivery")
        self.assertEqual(error.details["task"], task)
        self.assertTrue(error.details["published"])
        self.assertEqual(error.details["completed"], ["staging_validated", "quarantine", "publication"])
        self.assertTrue(error.details["quarantined"].startswith(".quarantine-"))
        self.assertEqual(error.details["recovery"], f"deliver {task}")
        self.assertEqual(json.loads((bag / "receipt.json").read_text(encoding="utf-8"))["format"], 2)
        quarantine = bag.parent / error.details["quarantined"]
        self.assertEqual((quarantine / "receipt.json").read_text(encoding="utf-8"), "{}")

    def test_first_rename_native_oserror_keeps_delivery_progress(self) -> None:
        task = self.ready()
        closed = self.complete(task)
        bag = Path(closed["bag_path"])
        (bag / "receipt.json").write_text("{}", encoding="utf-8")
        original_rename = Path.rename

        def failing_rename(path: Path, target: Path) -> Path:
            if path == bag:
                raise PermissionError("controlled quarantine rename failure")
            return original_rename(path, target)

        with (
            patch.object(Path, "rename", failing_rename),
            self.assertRaises(FairyError) as caught,
        ):
            self.workshop.deliver(task, repair=True)
        error = caught.exception
        self.assertEqual(error.code, "storage_failed")
        self.assertEqual(error.details["task"], task)
        self.assertFalse(error.details["published"])
        self.assertEqual(error.details["completed"], ["staging_validated"])
        self.assertNotIn("quarantined", error.details)
        self.assertEqual(error.details["recovery"], f"deliver {task}")
        self.assertEqual(error.details["exception"], "PermissionError")
        self.assertIsInstance(error.__cause__, PermissionError)
        self.assertEqual(list(bag.parent.glob(".quarantine-*")), [])
        self.assertTrue(bag.is_dir())
        self.assertEqual((bag / "receipt.json").read_text(encoding="utf-8"), "{}")

    def test_unlock_failure_after_publication_keeps_delivery_identity(self) -> None:
        task = self.ready()
        closed = self.complete(task)
        bag = Path(closed["bag_path"])
        (bag / "receipt.json").write_text("{}", encoding="utf-8")
        original_lock = _delivery._file_lock

        class ReleaseFault:
            def __init__(self, lock: Any) -> None:
                self.lock = lock

            def release(self) -> None:
                self.lock.release()
                raise OSError("controlled unlock acknowledgment failure")

        with (
            patch.object(_delivery, "_file_lock", side_effect=lambda path: ReleaseFault(original_lock(path))),
            self.assertRaises(FairyError) as caught,
        ):
            self.workshop.deliver(task, repair=True)
        error = caught.exception
        self.assertEqual(error.code, "storage_failed")
        self.assertEqual(error.details["task"], task)
        self.assertTrue(error.details["published"])
        self.assertEqual(error.details["completed"], ["staging_validated", "quarantine", "publication"])
        self.assertTrue(error.details["quarantined"].startswith(".quarantine-"))
        self.assertEqual(error.details["recovery"], f"deliver {task}")
        self.assertEqual(error.details["exception"], "OSError")
        self.assertIsInstance(error.__cause__, OSError)
        self.assertEqual(json.loads((bag / "receipt.json").read_text(encoding="utf-8"))["format"], 2)
        quarantine = bag.parent / error.details["quarantined"]
        self.assertEqual((quarantine / "receipt.json").read_text(encoding="utf-8"), "{}")

    def test_unlock_failure_does_not_mask_the_delivery_error(self) -> None:
        task = self.ready()
        closed = self.complete(task)
        bag = Path(closed["bag_path"])
        (bag / "receipt.json").write_text("{}", encoding="utf-8")
        original_verify = _delivery._verify
        observations = {"final_checks": 0}

        def failing_verify(root: Path, *args: Any, **kwargs: Any) -> None:
            if root == bag:
                observations["final_checks"] += 1
                if observations["final_checks"] == 2:
                    raise FairyError("integrity", "controlled final verification failure")
            original_verify(root, *args, **kwargs)

        original_lock = _delivery._file_lock

        class ReleaseFault:
            def __init__(self, lock: Any) -> None:
                self.lock = lock

            def release(self) -> None:
                self.lock.release()
                raise OSError("controlled unlock acknowledgment failure")

        with (
            patch.object(_delivery, "_verify", side_effect=failing_verify),
            patch.object(_delivery, "_file_lock", side_effect=lambda path: ReleaseFault(original_lock(path))),
            self.assertRaises(FairyError) as caught,
        ):
            self.workshop.deliver(task, repair=True)
        error = caught.exception
        self.assertEqual(error.code, "integrity")
        self.assertEqual(error.message, "controlled final verification failure")
        self.assertEqual(error.details["lock_release"], "failed")
        self.assertTrue(error.details["published"])
        self.assertEqual(error.details["completed"], ["staging_validated", "quarantine", "publication"])
        self.assertIsInstance(error.__cause__, FairyError)
        self.assertEqual(error.__cause__.code, "integrity")

    def test_real_authorizer_refusal_reports_rolled_back_certainty(self) -> None:
        task = self.ready()
        before = self.workshop.state(task).seq
        connection = self.workshop.store.connection

        def deny_events(action: int, arg1: str | None, _arg2: Any, _db: Any, _source: Any) -> int:
            if action == sqlite3.SQLITE_INSERT and arg1 == "events":
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        connection.set_authorizer(deny_events)
        try:
            with self.assertRaises(FairyError) as caught:
                self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        finally:
            connection.set_authorizer(None)
        error = caught.exception
        self.assertEqual(error.code, "storage_failed")
        self.assertIsInstance(error.details["committed"], bool)
        self.assertFalse(error.details["committed"])
        self.assertNotIn("commit", error.details)
        self.assertEqual(error.details["stage"], "admission")
        self.assertEqual(error.details["transaction"], "body")
        self.assertEqual(error.details["rollback"], {"state": "rolled_back"})
        self.assertEqual(error.details["task"], task)
        self.assertEqual(error.details["operation"], "close")
        self.assertEqual(error.details["seq"], before)
        self.assertEqual(self.workshop.state(task).seq, before)
        self.assertIsNone(self.workshop.state(task).outcome)
        with closing(sqlite3.connect(self.home / "workshop.sqlite3")) as observer, observer:
            kinds = [row[0] for row in observer.execute("SELECT kind FROM events WHERE task=?", (task,))]
        self.assertNotIn("closed", kinds)

    def test_body_error_with_failed_rollback_preserves_original_cause(self) -> None:
        task = self.ready()
        before = self.workshop.state(task).seq
        real = self.workshop.store.connection
        proxy = _StatementProxy(real, "closed", fail_rollback=True)
        self.workshop.store.connection = proxy
        try:
            with self.assertRaises(FairyError) as caught:
                self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        finally:
            self.workshop.store.connection = real
            if real.in_transaction:
                real.execute("ROLLBACK")
        error = caught.exception
        self.assertEqual(error.code, "storage_failed")
        self.assertNotIn("commit", error.details)
        self.assertEqual(error.details["committed"], "unknown")
        self.assertEqual(error.details["transaction"], "body")
        self.assertIn("rollback", error.details)
        self.assertEqual(error.details["task"], task)
        self.assertEqual(error.details["operation"], "close")
        self.assertIsInstance(error.__cause__.__cause__, sqlite3.OperationalError)
        self.assertEqual(str(error.__cause__.__cause__), "controlled statement failure")
        self.assertEqual(self.workshop.state(task).seq, before)
        self.assertIsNone(self.workshop.state(task).outcome)

    def test_observed_statement_acknowledgment_loss_is_unknown(self) -> None:
        task = self.workshop.start("Observed statement loss")
        before = self.workshop.state(task).seq
        sentinel = Path(self.temporary.name) / "external-effect.txt"

        def write_effect(_context: Any, _parameters: dict[str, Any]) -> dict[str, Any]:
            sentinel.write_text("completed", encoding="utf-8")
            return {"outputs": []}

        self.workshop.register("fixture.write", mock_capability("write", write_effect))
        real = self.workshop.store.connection
        proxy = _StatementProxy(real, "observed", lose_insert_acknowledgment=True, fail_rollback=True)
        self.workshop.store.connection = proxy
        try:
            with self.assertRaises(FairyError) as caught:
                self.workshop.invoke(task, "fixture.write", {})
        finally:
            self.workshop.store.connection = real
        error = caught.exception
        self.assertEqual(error.details["committed"], True)
        self.assertEqual(error.details["observed"], "unknown")
        self.assertEqual(error.details["effect_state"], "ok")
        self.assertEqual(error.details["committed_seq"], before + 1)
        self.assertTrue(error.details["invoked"])
        self.assertIsInstance(error.__cause__.__cause__, sqlite3.OperationalError)
        self.assertEqual(str(error.__cause__.__cause__), "controlled statement acknowledgment loss")
        self.assertTrue(real.in_transaction)
        with closing(sqlite3.connect(self.home / "workshop.sqlite3")) as observer, observer:
            self.assertEqual(
                observer.execute("SELECT MAX(seq) FROM events WHERE task=?", (task,)).fetchone()[0],
                before + 1,
            )
        self.assertEqual(self.workshop.state(task).seq, before + 2)
        real.execute("ROLLBACK")
        self.assertEqual(self.workshop.state(task).seq, before + 1)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "completed")

    def test_invocation_commit_unknown_keeps_call_and_investigation(self) -> None:
        task = self.workshop.start("Invocation commit unknown")
        before = self.workshop.state(task).seq
        sentinel = Path(self.temporary.name) / "handler-ran"

        def handler(_context: Any, _parameters: dict[str, Any]) -> dict[str, Any]:
            sentinel.write_text("ran", encoding="utf-8")
            return {"outputs": []}

        self.workshop.register("fixture.write", mock_capability("write", handler))
        real = self.workshop.store.connection
        proxy = _CommitProxy(real, lose_acknowledgment=True)
        self.workshop.store.connection = proxy
        try:
            with self.assertRaises(FairyError) as caught:
                self.workshop.invoke(task, "fixture.write", {})
        finally:
            self.workshop.store.connection = real
        error = caught.exception
        self.assertEqual(error.details["committed"], "unknown")
        self.assertEqual(error.details["stage"], "invoked")
        self.assertEqual(error.details["task"], task)
        self.assertEqual(error.details["known_seq"], before)
        self.assertEqual(error.details["attempted_seq"], before + 1)
        call_id = error.details["call"]
        self.assertEqual(len(call_id), 32)
        self.assertEqual(error.details["recovery"]["command"], f"inspect {task} --history")
        self.assertFalse(sentinel.exists())
        state = self.workshop.state(task)
        self.assertEqual(state.seq, before + 1)
        self.assertEqual(list(state.calls), [call_id])
        self.assertEqual(state.calls[call_id]["status"], "pending")

    def test_invocation_rollback_reports_false_with_call_identity(self) -> None:
        task = self.workshop.start("Invocation rollback")
        before = self.workshop.state(task).seq
        sentinel = Path(self.temporary.name) / "handler-ran"
        self.workshop.register(
            "fixture.write",
            mock_capability(
                "write",
                lambda _context, _parameters: sentinel.write_text("ran", encoding="utf-8") or {"outputs": []},
            ),
        )
        real = self.workshop.store.connection
        real.set_authorizer(
            lambda action, arg1, _arg2, _db, _source: (
                sqlite3.SQLITE_DENY
                if action == sqlite3.SQLITE_INSERT and arg1 == "events"
                else sqlite3.SQLITE_OK
            )
        )
        try:
            with self.assertRaises(FairyError) as caught:
                self.workshop.invoke(task, "fixture.write", {})
        finally:
            real.set_authorizer(None)
        error = caught.exception
        self.assertEqual(error.code, "storage_failed")
        self.assertFalse(error.details["committed"])
        self.assertEqual(error.details["stage"], "invoked")
        self.assertEqual(error.details["task"], task)
        self.assertEqual(error.details["known_seq"], before)
        self.assertEqual(error.details["attempted_seq"], before + 1)
        self.assertEqual(len(error.details["call"]), 32)
        self.assertEqual(error.details["recovery"]["command"], f"inspect {task} --history")
        self.assertFalse(sentinel.exists())
        self.assertEqual(self.workshop.state(task).seq, before)
