from __future__ import annotations

import hashlib
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest.mock import patch

import filelock

from astrofairy import FairyError
from astrofairy import _documents as documents
from astrofairy._contracts import canonical, parse_json
from astrofairy._documents import audit_document, freeze
from astrofairy._presentation import read_document
from astrofairy.tests._support import WorkshopTest

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import NoReturn


class DocumentTests(WorkshopTest):
    def test_bulk_audit_checks_shared_scalars_once_and_incoming_edges_before_seen(self) -> None:
        for number in range(24):
            freeze(self.home, {"items": list(range(number + 1)), "seq": number})
        with sqlite3.connect(self.home / "documents.sqlite3") as database:
            bodies = [
                documents.parse_json(row[0].decode("utf-8"))
                for row in database.execute("SELECT payload FROM nodes")
            ]
            scalar_count = sum(body["kind"] == "scalar" and body["json_type"] == "integer" for body in bodies)
        parse = documents.parse_json
        scalars = []

        def tracked(text: str) -> object:
            if text[:1].isdigit():
                scalars.append(text)
            return parse(text)

        with patch.object(documents, "parse_json", tracked):
            self.assertEqual(documents.audit_archive(self.home)["documents"], 24)
        self.assertEqual(len(scalars), scalar_count)
        with documents._Archive(self.home, write=True) as archive:
            valid = archive.build("shared")
            malformed = archive.put(
                {"kind": "scalar", "json_type": "string", "text": valid.edge("value").encoded()}
            )
            with self.assertRaises(FairyError):
                documents._audit_nodes(archive, [valid, malformed], set())
        with self.assertRaises(FairyError):
            documents.audit_archive(self.home)

    def test_cold_concurrent_initialization_and_reader_without_native_lock(self) -> None:
        for number in range(4):
            home = self.home / f"cold-{number}"
            with ThreadPoolExecutor(max_workers=8) as workers:
                roots = list(
                    workers.map(
                        lambda _, target=home: freeze(target, {"items": list(range(20))})["document"],
                        range(8),
                    )
                )
            self.assertEqual(len(set(roots)), 1)
            lock = home / "documents.sqlite3.init.lock"
            inode = lock.stat().st_ino
            self.assertEqual(lock.stat().st_mode & 0o777, 0o600)
            freeze(home, {"different": number})
            self.assertEqual(lock.stat().st_ino, inode)
            with patch("filelock.FileLock", side_effect=AssertionError("Read acquired a lock")):
                self.assertEqual(read_document(home, roots[0], pointer="/items/0")["text"], "0")
                self.assertEqual(audit_document(home, roots[0])["integrity"], "full")

    def test_native_only_lock_failure_timeout_and_connection_cleanup(self) -> None:
        def timeout(*_args: object, **_kwargs: object) -> NoReturn:
            raise filelock.Timeout("secret lock")

        for factory, code in [
            (filelock.SoftFileLock, "runtime_setup_required"),
            (timeout, "storage_busy"),
        ]:
            home = self.home / code
            with patch("filelock.FileLock", side_effect=factory), self.assertRaises(FairyError) as caught:
                freeze(home, {"value": "data"})
            self.assertEqual(caught.exception.code, code)
            self.assertFalse((home / "documents.sqlite3").exists())
            self.assertNotIn("secret lock", str(caught.exception.as_dict()))
        connections = []
        opened = sqlite3.connect

        def track(*args: object, **kwargs: object) -> sqlite3.Connection:
            result = opened(*args, **kwargs)
            connections.append(result)
            return result

        @contextmanager
        def broken_exit(*_args: object, **_kwargs: object) -> Iterator[None]:
            yield
            raise OSError("private lock exit")

        with (
            patch("filelock.FileLock", side_effect=broken_exit) as lease,
            patch.object(documents.sqlite3, "connect", side_effect=track),
            self.assertRaises(FairyError) as caught,
        ):
            freeze(self.home / "exit", {"value": "data"})
        self.assertEqual(caught.exception.code, "runtime_setup_required")
        self.assertEqual(lease.call_args.kwargs["timeout"], 10)
        self.assertFalse(lease.call_args.kwargs["fallback_to_soft"])
        self.assertTrue(lease.call_args.kwargs["preserve_lock_file"])
        for connection in connections:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT 1")

    def reconstruct(self, ref: str, pointer: str = "") -> str:
        offset = 0
        fragments = []
        selection = None
        while True:
            page = read_document(self.home, ref, pointer=pointer, offset=offset, limit=1000)
            selection = selection or page["selection"]
            self.assertEqual(page["selection"], selection)
            self.assertEqual(page["integrity"], "selected")
            fragments.append(page["text"])
            if page["next_offset"] is None:
                return "".join(fragments)
            self.assertGreater(page["next_offset"], offset)
            offset = page["next_offset"]

    def test_canonical_values_key_order_numeric_normalization_and_deep_input(self) -> None:
        value = {
            "": None,
            "same-prefix-" * 1000 + "a": -0.0,
            "same-prefix-" * 1000 + "b": True,
            "same-prefix-" * 1000 + "c": [1, 1.0, 1e-30, 10**200, '\u0000界"\\' * 1000],
            "integer_keys": {2: "two", 10: "ten"},
            "empty": [{}, []],
        }
        normalized = parse_json(canonical(value).decode())
        ref = freeze(self.home, value)["document"]
        text = self.reconstruct(ref)
        self.assertEqual(text.encode(), canonical(normalized))
        audit = audit_document(self.home, ref)
        self.assertEqual(audit["canonical_sha256"], hashlib.sha256(text.encode()).hexdigest())
        self.assertNotEqual(audit["selection"], audit["canonical_sha256"])
        key = "same-prefix-" * 1000 + "c"
        self.assertEqual(parse_json(self.reconstruct(ref, "/" + key)), normalized[key])
        deep: object = "leaf"
        for _ in range(400):
            deep = [deep]
        deep_ref = freeze(self.home, deep)["document"]
        self.assertEqual(read_document(self.home, deep_ref, pointer="/0" * 400)["text"], '"leaf"')

    def test_corrupt_unread_sibling_is_separate_from_whole_audit(self) -> None:
        ref = freeze(self.home, {"large": "q" * 20000, "tiny": "ok"})["document"]
        with documents.select(self.home, ref, pointer="/large") as (node, _):
            pending = [node]
            while pending[-1].kind != "text":
                parent = pending.pop()
                edge = next(item for item in parent.parts if not isinstance(item, str))
                pending.append(parent.archive.expect(edge))
            damaged = pending[-1].ref
        path = self.home / "documents.sqlite3"
        with sqlite3.connect(path) as database:
            data = database.execute("SELECT payload FROM nodes WHERE ref=?", (damaged,)).fetchone()[0]
            database.execute("UPDATE nodes SET payload=? WHERE ref=?", (data + b" ", damaged))
        self.assertEqual(read_document(self.home, ref, pointer="/tiny")["text"], '"ok"')
        for operation in [
            lambda: read_document(self.home, ref, pointer="/large"),
            lambda: audit_document(self.home, ref),
            lambda: freeze(self.home, {"large": "q" * 20000, "tiny": "ok"}),
        ]:
            with self.assertRaises(FairyError) as caught:
                operation()
            self.assertEqual(caught.exception.code, "integrity")

    def test_tiny_and_late_reads_fetch_bounded_rows_without_full_parse(self) -> None:
        value = "".join(hashlib.shake_256(str(n).encode()).hexdigest(1024) for n in range(600))
        ref = freeze(self.home, {"payload": value, "tiny": 7})["document"]
        fetched = []
        original = documents._Archive.fetch

        def tracked(archive: documents._Archive, identity: str) -> bytes | None:
            data = original(archive, identity)
            if data is not None:
                fetched.append(len(data))
            return data

        with patch.object(documents._Archive, "fetch", tracked):
            self.assertEqual(read_document(self.home, ref, pointer="/tiny")["text"], "7")
            page = read_document(self.home, ref, pointer="/payload", offset=len(value) - 99, limit=100)
        self.assertEqual(page["text"], canonical(value).decode()[len(value) - 99 : len(value) + 1])
        self.assertLess(sum(fetched), 120000)
        self.assertLess(max(fetched), documents.MAX_NODE_BYTES + 1)

    def test_append_storage_shares_immutable_values_and_indices(self) -> None:
        items = []
        measurements = []
        roots = []
        for number in range(64):
            items.append(hashlib.shake_256(str(number).encode()).hexdigest(4096))
            roots.append(freeze(self.home, {"history": items, "seq": number})["document"])
            if number + 1 in {16, 32, 64}:
                with sqlite3.connect(self.home / "documents.sqlite3") as database:
                    measurements.append(
                        database.execute("SELECT sum(length(payload)) FROM nodes").fetchone()[0]
                    )
        self.assertLess(measurements[1], measurements[0] * 2.7)
        self.assertLess(measurements[2], measurements[1] * 2.7)
        self.assertEqual(read_document(self.home, roots[0], pointer="/seq")["text"], "0")
        before = measurements[-1]
        self.assertEqual(freeze(self.home, {"history": items, "seq": 63})["document"], roots[-1])
        with sqlite3.connect(self.home / "documents.sqlite3") as database:
            self.assertEqual(database.execute("SELECT sum(length(payload)) FROM nodes").fetchone()[0], before)

    def test_archive_metadata_refusal_and_missing_reader_do_not_initialize(self) -> None:
        home = self.home / "missing"
        with self.assertRaises(FairyError):
            read_document(home, "a" * 64)
        self.assertFalse(home.exists())
        home.mkdir()
        path = home / "documents.sqlite3"
        with sqlite3.connect(path) as database:
            database.execute("CREATE TABLE sentinel(value TEXT)")
            database.execute("INSERT INTO sentinel VALUES ('keep')")
        before = path.read_bytes()
        with self.assertRaises(FairyError) as caught:
            freeze(home, {"value": "new"})
        self.assertEqual(caught.exception.code, "version")
        self.assertEqual(path.read_bytes(), before)

    def test_wrong_span_kind_and_cache_bound_are_verified(self) -> None:
        with documents._Archive(self.home, write=True) as archive:
            leaf = archive.put({"kind": "text", "text": '"value"'})
            malformed = archive.put({"kind": "scalar", "json_type": "string", "text": [leaf.ref, 1, 1]})
            root = archive.put(
                {"kind": "document", "format": 1, "owner": None, "value": malformed.edge("value").encoded()}
            )
        with self.assertRaises(FairyError) as caught:
            read_document(self.home, root.ref)
        self.assertEqual(caught.exception.code, "integrity")
        value = [str(n) + " data" for n in range(1000)]
        ref = freeze(self.home, value)["document"]
        with documents.select(self.home, ref) as (node, _):
            offset = 0
            while offset < node.characters:
                offset += len(node.archive.fragment(node, offset, 1000))
                self.assertLessEqual(len(node.archive.cache), documents.CACHE_NODES)
        self.assertLess(400, sys.getrecursionlimit())
