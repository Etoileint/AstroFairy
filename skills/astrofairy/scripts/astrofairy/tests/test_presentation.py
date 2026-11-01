from __future__ import annotations

import builtins
import io
import sqlite3
from importlib.metadata import version
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from astrofairy import Context, FairyError, Workshop
from astrofairy._cli import main
from astrofairy._contracts import MAX_BLOB_BYTES, MAX_CONTEXT_BYTES, canonical, digest, parse_json
from astrofairy._documents import audit_document, freeze
from astrofairy._presentation import encode_response, read_document
from astrofairy.tests._support import WorkshopTest, mock_capability


class PresentationTests(WorkshopTest):
    def cli(self, *arguments: str) -> tuple[int, dict[str, Any]]:
        output = io.BytesIO()
        with patch("astrofairy._cli.sys.stdout", SimpleNamespace(buffer=output)):
            status = main(["--home", str(self.home), *arguments])
        data = output.getvalue()
        self.assertLessEqual(len(data), MAX_CONTEXT_BYTES)
        return status, parse_json(data.decode("utf-8"))

    def reconstruct(self, document: str, task: str | None, pointer: str = "", limit: int = 2000) -> Any:
        fragments = []
        offset = 0
        selections = set()
        while True:
            result = read_document(
                self.home, document, task=task, pointer=pointer, offset=offset, limit=limit
            )
            self.assertLessEqual(len(canonical(result)) + 1, MAX_CONTEXT_BYTES)
            selections.add(result["selection"])
            fragments.append(result["text"])
            if result["next_offset"] is None:
                break
            self.assertGreater(result["next_offset"], offset)
            offset = result["next_offset"]
        self.assertEqual(len(selections), 1)
        if not pointer:
            audit = audit_document(self.home, document, task=task)
            self.assertEqual(audit["canonical_sha256"], digest("".join(fragments).encode("utf-8")))
        return parse_json("".join(fragments))

    def test_exact_wire_cap_and_lossless_all_shapes_with_escaping(self) -> None:
        value = {"a/b": ['界\u0001"\\' * 4000], "": None, "long" * 10000: {"~1": True}}
        inline = {"a": "small"}
        self.assertEqual(encode_response(self.home, inline), canonical(inline) + b"\n")
        encoded = encode_response(self.home, value)
        self.assertLessEqual(len(encoded), MAX_CONTEXT_BYTES)
        packet = parse_json(encoded.decode())
        self.assertTrue(packet["deferred"])
        self.assertEqual(self.reconstruct(packet["document"], None), value)
        self.assertEqual(self.reconstruct(packet["document"], None, "/a~1b/0"), value["a/b"][0])
        scalar = freeze(self.home, 42)
        self.assertEqual(self.reconstruct(scalar["document"], None, limit=1), 42)

    def test_rfc_pointer_errors_are_fixed_safe_and_never_return_the_source(self) -> None:
        value = {
            "foo": ["bar", "baz"],
            "": 0,
            "a/b": 1,
            "m~n": 8,
            "~1": 9,
            "\u0000": 10,
            "01": 11,
            "private": "SENSITIVE-CONTROL",
        }
        ref = freeze(self.home, value)["document"]
        for pointer, expected in [
            ("/", 0),
            ("/foo/0", "bar"),
            ("/a~1b", 1),
            ("/m~0n", 8),
            ("/~01", 9),
            ("/\u0000", 10),
            ("/01", 11),
        ]:
            with self.subTest(pointer=pointer):
                self.assertEqual(self.reconstruct(ref, None, pointer, limit=1), expected)
        for pointer in [
            "missing",
            "/missing",
            "/foo/01",
            "/foo/-",
            "/foo/-1",
            "/foo/" + chr(0xFF12),
            "/foo/2",
            "/~2",
            "#",
        ]:
            with self.subTest(pointer=pointer), self.assertRaises(FairyError) as caught:
                read_document(self.home, ref, pointer=pointer)
            self.assertEqual(caught.exception.code, "invalid")
            self.assertNotIn("SENSITIVE", str(caught.exception.as_dict()))

    def test_free_read_reuses_locked_runtime_authority_and_refuses_broken_import(self) -> None:
        ref = freeze(self.home, {"text": "Actual value"})["document"]
        with patch(
            "astrofairy._contracts.version",
            side_effect=lambda name: "0.0.0" if name == "jsonpointer" else version(name),
        ):
            status, result = self.cli("read", ref)
        self.assertEqual((status, result["error"]), (1, "runtime_setup_required"))
        imported = builtins.__import__

        def blocked(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "jsonpointer":
                raise ImportError("fixture import unavailable")
            return imported(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=blocked):
            status, result = self.cli("read", ref)
        self.assertEqual((status, result["error"]), (1, "runtime_setup_required"))
        self.assertNotIn("fixture", str(result))

    def test_scope_integrity_offsets_reuse_and_restart(self) -> None:
        task = self.workshop.start("Work")
        descriptor = freeze(self.home, {"text": "large" * 10000}, task=task)
        path = self.home / "documents.sqlite3"
        with sqlite3.connect(path) as database:
            before = database.execute("SELECT count(*), sum(length(payload)) FROM nodes").fetchone()
        self.assertEqual(freeze(self.home, {"text": "large" * 10000}, task=task), descriptor)
        with sqlite3.connect(path) as database:
            self.assertEqual(
                database.execute("SELECT count(*), sum(length(payload)) FROM nodes").fetchone(), before
            )
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        for owner in [None, "a" * 32]:
            with self.assertRaises(FairyError):
                read_document(self.home, descriptor["document"], task=owner)
        for options in [
            {"offset": -1},
            {"offset": True},
            {"offset": 1000000},
            {"limit": 0},
            {"limit": MAX_CONTEXT_BYTES + 1},
        ]:
            with self.assertRaises(FairyError):
                read_document(self.home, descriptor["document"], task=task, **options)
        with self.assertRaises(FairyError):
            read_document(self.home, "../private")
        with self.assertRaises(FairyError):
            read_document(self.home, "f" * 64)
        status, page = self.cli(
            "read", descriptor["document"], "--task", task, "--pointer", "/text", "--limit", "1"
        )
        self.assertEqual((status, page["text"]), (0, '"'))
        with sqlite3.connect(path) as database:
            row = database.execute(
                "SELECT payload FROM nodes WHERE ref=?", (descriptor["document"],)
            ).fetchone()
            database.execute(
                "UPDATE nodes SET payload=? WHERE ref=?", (row[0] + b" ", descriptor["document"])
            )
        with self.assertRaises(FairyError) as caught:
            read_document(self.home, descriptor["document"], task=task)
        self.assertEqual(caught.exception.code, "integrity")

    def test_large_next_free_selected_context_and_immutable_pages_at_zero_budget(self) -> None:
        task = self.workshop.start(
            "Useful deliverable", budget=1, spec={"criteria": [{"id": "goal", "description": "Relevant"}]}
        )
        self.produce(task)
        for number in range(40):
            self.workshop.submit(task, {"op": "answer", "text": f"update {number}: " + "界\u0001" * 500})
        seq = self.workshop.state(task).seq
        status, packet = self.cli("next", task)
        self.assertEqual(
            (status, packet["control"]["action"], packet["control"]["budget_left"]), (0, "review", 0)
        )
        self.assertEqual(packet["counts"]["user_updates"], 40)
        old = packet["document"]
        status, update = self.cli("read", old, "--task", task, "--pointer", "/user_updates/39/payload/text")
        self.assertEqual(status, 0)
        self.assertTrue(parse_json(update["text"]).startswith("update 39:"))
        self.assertEqual(self.workshop.state(task).seq, seq)
        self.workshop.submit(task, {"op": "answer", "text": "Later update"})
        self.assertEqual(self.reconstruct(old, task, "/seq"), seq)
        self.semantic(task)
        self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.assertEqual(
            self.reconstruct(old, task, "/user_updates/39/payload/text"), parse_json(update["text"])
        )

    def test_start_projection_failure_keeps_committed_recovery_identity(self) -> None:
        with patch("astrofairy._documents._Archive.put", side_effect=OSError("fixture secret")):
            status, result = self.cli("start", "--request", "\u0001" * 5000)
        self.assertEqual((status, result["error"]), (1, "projection_failed"))
        self.assertEqual(self.workshop.state(result["task"]).seq, result["seq"])
        self.assertNotIn("fixture secret", str(result))

    def test_real_effect_fact_survives_presentation_failure(self) -> None:
        def writer(context: Context, _parameters: dict[str, Any]) -> dict[str, Any]:
            context.path("effect.txt").write_text("one effect", encoding="utf-8")
            return {"outputs": [], "detail": "x" * 50000, "task": "f" * 32}

        capability = mock_capability("write", writer)
        task = self.workshop.start("Perform effect")
        command = self.home / "command.json"
        command.write_bytes(canonical({"op": "invoke", "capability": "fixture.write", "parameters": {}}))
        factory = Workshop
        with (
            patch(
                "astrofairy._cli.Workshop",
                side_effect=lambda home: factory(home, {"fixture.write": capability}),
            ),
            patch("astrofairy._documents._Archive.put", side_effect=OSError("projection unavailable")),
        ):
            status, result = self.cli("submit", task, "--file", str(command))
        state = self.workshop.state(task)
        self.assertEqual(
            (status, result["error"], result["task"], result["status"]), (1, "projection_failed", task, "ok")
        )
        self.assertEqual(state.calls[result["call"]]["status"], "ok")
        self.assertEqual(len(state.calls), 1)
        self.assertEqual((self.home / "workspaces" / task / "effect.txt").read_text(), "one effect")

    def test_learning_uses_small_locator_for_large_exact_history(self) -> None:
        self.workshop.register(
            "fixture.large",
            mock_capability(
                "read",
                lambda _context, _parameters: {"outputs": [], "detail": "x" * (MAX_BLOB_BYTES + 1)},
            ),
        )
        task = self.workshop.start("Observe a large result")
        observation = self.workshop.invoke(task, "fixture.large", {})
        self.assertEqual(observation["status"], "ok")
        self.workshop.submit(task, {"op": "answer", "text": "Retain this correction"})
        self.workshop.submit(task, {"op": "close", "outcome": "cancelled"})
        seq = self.workshop.state(task).seq
        child = self.workshop.learning_task(task)
        locator = parse_json(self.workshop.store.get(self.workshop.state(child).inputs[0]["ref"]).decode())
        self.assertLess(len(canonical(locator)), 1024)
        self.assertEqual((locator["task"], locator["seq"]), (task, seq))
        page = read_document(self.home, locator["document"], task=task, pointer="/events/3/payload/text")
        self.assertEqual(parse_json(page["text"]), "Retain this correction")
        page = read_document(
            self.home, locator["document"], task=task, pointer="/calls/0/result/detail", limit=1
        )
        self.assertEqual(page["characters"], MAX_BLOB_BYTES + 3)
        self.produce(child, "Observed success and correction support a reusable improvement")
        self.finish(child, "grounded")
        self.assertEqual(self.workshop.state(task).seq, seq)

    def test_oversized_failed_check_batch_retains_nonzero_exit_status(self) -> None:
        task = self.workshop.start(
            "Check exact requirements",
            budget=8,
            spec={
                "criteria": [
                    {
                        "id": f"c{n}",
                        "description": "Required text",
                        "checker": "contains",
                        "parameters": {"text": "missing" + "界" * 2000},
                    }
                    for n in range(6)
                ]
            },
        )
        self.produce(task, "Actual artifact")
        path = self.home / "check.json"
        path.write_bytes(canonical({"op": "check"}))
        status, result = self.cli("submit", task, "--file", str(path))
        self.assertEqual(status, 1)
        self.assertTrue(result["deferred"])
        checks = self.reconstruct(result["document"], task, "/checks")
        self.assertEqual(len(checks), 6)
        self.assertTrue(all(item["result"]["verdict"] == "fail" for item in checks))
