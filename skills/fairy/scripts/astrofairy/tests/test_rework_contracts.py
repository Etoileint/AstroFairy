from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import bagit

from astrofairy import FairyError
from astrofairy._contracts import _require_portable_set, canonical, parse_json
from astrofairy._search import FastEmbedder, SearchIndex, chunks_from_package
from astrofairy.tests._support import ROOT, WorkshopTest
from astrofairy.tests.test_search_contracts import HashEmbedder


class ReworkContractTests(WorkshopTest):
    def complete(self, task: str) -> dict:
        self.workshop.submit(task, {"op": "check"})
        return self.workshop.submit(task, {"op": "close", "outcome": "complete"})

    def test_interrupted_prepare_keeps_full_plan_and_resume_uses_it(self) -> None:
        task = self.workshop.start(
            "Deliver both members",
            spec={
                "criteria": [
                    {
                        "id": "usable",
                        "description": "Nonempty collection",
                        "checker": "nonempty",
                        "scope": "collection",
                    }
                ]
            },
        )
        workspace = Path(self.workshop.next(task)["workspace"])
        (workspace / "a.txt").write_text("first", encoding="utf-8")
        with self.assertRaises(FairyError) as caught:
            self.workshop.prepare_delivery(
                task,
                {"members": [{"path": "a.txt", "role": "main"}, {"path": "b.txt", "role": "main"}]},
            )
        self.assertEqual(caught.exception.details["remaining"], ["b.txt"])
        packet = self.workshop.next(task)
        self.assertEqual(packet["action"], "prepare_delivery")
        self.assertEqual([item["path"] for item in packet["payload"]["members"]], ["a.txt", "b.txt"])
        (workspace / "b.txt").write_text("second", encoding="utf-8")
        result = self.workshop.prepare_delivery(task, {"members": [{"path": "b.txt", "role": "main"}]})
        self.assertEqual([item["path"] for item in result["members"]], ["a.txt", "b.txt"])
        delivery = self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.assertEqual(sorted(delivery["files"]), ["a.txt", "b.txt"])
        self.assertEqual(Path(delivery["files"]["a.txt"]).read_text(), "first")

    def test_changed_delivery_plan_is_rejected_explicitly(self) -> None:
        task = self.workshop.start("Plan stability")
        workspace = Path(self.workshop.next(task)["workspace"])
        (workspace / "a.txt").write_text("a", encoding="utf-8")
        with self.assertRaises(FairyError):
            self.workshop.prepare_delivery(task, {"members": [{"path": "missing.txt", "role": "main"}]})
        with self.assertRaises(FairyError) as caught:
            self.workshop.prepare_delivery(task, {"members": [{"path": "other.txt", "role": "main"}]})
        self.assertEqual(caught.exception.code, "conflict")

    def test_bagit_1_and_authoritative_payload_binding(self) -> None:
        task = self.workshop.start(
            "Bag binding",
            spec={
                "criteria": [
                    {
                        "id": "usable",
                        "description": "Nonempty",
                        "checker": "nonempty",
                        "scope": "collection",
                    }
                ]
            },
        )
        output = self.produce(task)
        self.workshop.submit(task, {"op": "check"})
        delivery = self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        bag_root = Path(delivery["bag_path"])
        self.assertEqual((bag_root / "bagit.txt").read_text().splitlines()[0], "BagIt-Version: 1.0")
        receipt = parse_json((bag_root / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["bag"]["format"], "bagit-1.0")
        self.assertTrue(bagit.Bag(str(bag_root)).validate())
        payload = bag_root / "data" / "result.md"
        payload.write_text("changed and internally re-manifested", encoding="utf-8")
        bagit.Bag(str(bag_root)).save(manifests=True)
        with self.assertRaises(FairyError) as caught:
            self.workshop.deliver(task)
        self.assertEqual(caught.exception.code, "integrity")
        self.assertEqual(self.workshop.store.get(output["ref"]), b"A useful result")

    def test_unselected_payload_and_forged_receipt_are_rejected(self) -> None:
        task = self.workshop.start(
            "Authoritative delivery",
            spec={
                "criteria": [
                    {
                        "id": "usable",
                        "description": "Nonempty",
                        "checker": "nonempty",
                        "scope": "collection",
                    }
                ]
            },
        )
        self.produce(task)
        self.workshop.submit(task, {"op": "check"})
        delivery = self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        bag_root = Path(delivery["bag_path"])
        extra = bag_root / "data" / "unselected.txt"
        extra.write_text("not selected\n", encoding="utf-8")
        bagit.Bag(str(bag_root)).save(manifests=True)
        with self.assertRaises(FairyError):
            self.workshop.deliver(task)
        extra.unlink()
        receipt_path = bag_root / "receipt.json"
        forged = parse_json(receipt_path.read_text(encoding="utf-8"))
        forged["goal"] = "FORGED AGREEMENT"
        forged["outcome"] = "failed"
        forged["reviews"] = []
        receipt_path.write_bytes(canonical(forged))
        bagit.Bag(str(bag_root)).save()
        with self.assertRaises(FairyError):
            self.workshop.deliver(task)

    def test_casefolded_directory_prefix_conflict_is_rejected(self) -> None:
        with self.assertRaises(FairyError):
            _require_portable_set(["A", "a/file.txt"])
        _require_portable_set(["a.txt", "a/b.txt"])

    def test_failed_review_is_reopened_for_a_legitimate_fix(self) -> None:
        criterion = {
            "id": "contains",
            "description": "Must contain X",
            "checker": "contains",
            "parameters": {"text": "X"},
            "scope": "content",
        }
        task = self.workshop.start("Repair a failed result", spec={"criteria": [criterion]})
        good = self.produce(task, "X good")
        self.workshop.submit(task, {"op": "check"})
        self.produce(task, "bad")
        self.workshop.submit(task, {"op": "check"})
        self.publish(task, [good])
        before = self.workshop.state(task).seq
        first = self.workshop.submit(task, {"op": "check"})
        second = self.workshop.submit(task, {"op": "check"})
        after = self.workshop.state(task).seq
        self.assertGreater(after, before)
        self.assertEqual(len(first["checks"]), 1)
        self.assertEqual(len(second["checks"]), 0)
        self.assertFalse(self.workshop.state(task).unresolved_failures())

    def test_two_path_fusion_preserves_cross_path_rank_contributions(self) -> None:
        index = SearchIndex(self.workshop.store)
        refs = [char * 64 for char in "abcd"]
        heads = [
            {"ref": ref, "name": name, "scope": "personal", "kind": "guide", "summary": name, "version": 1}
            for ref, name in zip(refs, "abcd", strict=True)
        ]
        pointer = {
            "generation": 1,
            "profile": index.profile_id,
            "table_name": "controlled",
            "lance_version": 1,
            "epoch": "test",
        }

        class Query:
            def __init__(self, rows: list[dict]) -> None:
                self.rows = rows

            def where(self, *_args: object, **_kwargs: object) -> Query:
                return self

            def limit(self, *_args: object) -> Query:
                return self

            def to_list(self) -> list[dict]:
                return self.rows

        def ranked(order: list[int]) -> list[dict]:
            return [{"asset_ref": refs[index], "text": str(index), "locator": "body"} for index in order]

        class Table:
            def search(self, _value: object, *, query_type: str) -> Query:
                return Query(ranked([0, 1] if query_type == "fts" else [1, 2, 3, 0]))

        index.embedder = HashEmbedder()
        with (
            patch(
                "astrofairy._search._read_snapshot",
                return_value={"generation": 1, "pointer": pointer, "heads": heads},
            ),
            patch.object(index, "_table", return_value=Table()),
        ):
            matches = index.page("controlled", limit=4)["matches"]
        self.assertEqual([item["name"] for item in matches[:2]], ["b", "a"])
        scores = {item["name"]: item["score"] for item in matches}
        self.assertGreater(scores["b"], scores["a"])

    def test_deferred_todos_are_global_and_resolve_with_later_decision(self) -> None:
        task = self.workshop.start("Deferred learning")
        self.produce(task)
        self.finish(task)
        self.workshop.submit(task, {"op": "learn", "decision": "defer", "note": "wait"})
        self.assertEqual(len(self.workshop.next(task)["learning"]["todos"]), 1)
        self.assertEqual(len(self.workshop.todos()), 1)
        self.assertEqual(self.workshop.todos()[0]["task"], task)
        self.workshop.submit(task, {"op": "learn", "decision": "no_change", "note": "resolved"})
        self.assertEqual(self.workshop.next(task)["learning"]["todos"], [])
        self.assertEqual(self.workshop.todos(), [])

    def test_governance_scope_selects_adopted_constraints_without_topk(self) -> None:
        package = {
            **self.proposal(),
            "name": "scope-constraint",
            "kind": "constraint",
            "applicability": {"use_when": ["internal review"]},
        }
        ref = self.workshop.library.propose(package)
        validation = self.workshop.validation_task(ref)
        self.workshop.submit(validation, {"op": "check"})
        self.workshop.submit(
            validation,
            {
                "op": "review",
                "criterion": "asset-fitness",
                "verdict": "pass",
                "basis": "Governance scope fixture",
            },
        )
        self.workshop.submit(validation, {"op": "close", "outcome": "complete"})
        self.workshop.library.adopt(ref, validation, "stable")
        candidates = self.workshop.governance("personal")["assets"]
        self.assertEqual(candidates[0]["ref"], ref)
        self.assertFalse(candidates[0]["requires_host_judgment"])
        task = self.workshop.start(
            "Scoped governance",
            spec={"governance_scope": ["personal"]},
        )
        self.assertEqual(self.workshop.next(task)["governance"], [ref])

    def test_structured_asset_fields_are_projected_and_learning_decisions_recorded(self) -> None:
        package = {
            **self.proposal(),
            "applicability": {"use_when": ["internal summary"], "avoid_when": ["legal advice"]},
            "dependencies": ["source note"],
            "invalidation": ["audience changes"],
        }
        ref = self.workshop.library.propose(package)
        stored = self.workshop.library.get(ref)
        self.assertEqual(stored["applicability"]["use_when"], ["internal summary"])
        locators = {locator for _text, locator in chunks_from_package(stored)}
        self.assertTrue({"applicability", "dependencies", "invalidation"} <= locators)
        task = self.workshop.start("Deliver a learning source")
        self.produce(task)
        self.finish(task)
        self.workshop.submit(task, {"op": "learn", "decision": "defer", "note": "wait for feedback"})
        packet = self.workshop.next(task)
        self.assertTrue(packet["learning"]["decided"])
        self.assertEqual(packet["learning"]["decision"]["decision"], "defer")
        self.assertEqual(len(packet["learning"]["todos"]), 1)

    def test_governance_assets_are_fixed_references_and_must_be_pinned(self) -> None:
        ref = self.workshop.library.propose(self.proposal())
        validation = self.workshop.validation_task(ref)
        self.workshop.submit(validation, {"op": "check"})
        self.workshop.submit(
            validation,
            {
                "op": "review",
                "criterion": "asset-fitness",
                "verdict": "pass",
                "basis": "Governance fixture is usable",
            },
        )
        self.workshop.submit(validation, {"op": "close", "outcome": "complete"})
        self.workshop.library.adopt(ref, validation, "stable")
        task = self.workshop.start(
            "Use pinned governance",
            spec={
                "criteria": [
                    {
                        "id": "usable",
                        "description": "Nonempty",
                        "checker": "nonempty",
                        "scope": "collection",
                    }
                ],
                "governance": [ref],
            },
        )
        self.assertEqual(self.workshop.next(task)["missing_governance"], [ref])
        self.produce(task)
        with self.assertRaises(FairyError):
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.workshop.invoke(task, "asset.read", {"ref": ref})
        self.workshop.submit(task, {"op": "check"})
        self.assertEqual(
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})["outcome"],
            "complete",
        )

    def test_model_prepare_and_load_pass_fixed_revision_and_offline_consumption(self) -> None:
        captured: dict[str, object] = {}

        def fake_download(**kwargs: object) -> str:
            captured.update(kwargs)
            raise RuntimeError("fixture stops after argument capture")

        with patch("huggingface_hub.snapshot_download", fake_download), self.assertRaises(FairyError):
            FastEmbedder(Path(self.temporary.name) / "empty").prepare()
        self.assertEqual(captured["revision"], "ac6781cd1cf88b8306a536d7c9d18a5bd57cc14b")
        self.assertFalse(captured["local_files_only"])
        self.assertIn("cache_dir", captured)

        cache = ROOT / ".cache/fastembed"
        if not (cache / "models--Qdrant--multilingual-e5-large-onnx").is_dir():
            self.skipTest("fixed model cache is not present")

        class FakeEmbedding:
            def __init__(self, **kwargs: object) -> None:
                captured.update(kwargs)
                raise RuntimeError("fixture stops after argument capture")

        captured.clear()
        with patch("fastembed.TextEmbedding", FakeEmbedding), self.assertRaises(FairyError):
            FastEmbedder(cache)._load()
        self.assertTrue(captured["local_files_only"])
        self.assertTrue(
            str(captured["specific_model_path"]).endswith("ac6781cd1cf88b8306a536d7c9d18a5bd57cc14b")
        )

    def test_missing_fixed_model_is_not_downloaded_by_query(self) -> None:
        with (
            patch("fastembed.TextEmbedding", side_effect=AssertionError("must not load")),
            self.assertRaises(FairyError),
        ):
            FastEmbedder(Path(self.temporary.name) / "empty")._load()
