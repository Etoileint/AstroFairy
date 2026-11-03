from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path
from typing import Any

from astrofairy import FairyError, Workshop
from astrofairy._library import MAX_SEARCH_RESULTS, Library
from astrofairy._maintenance import backup_state, restore_state
from astrofairy._search import CharTokenizer, SearchIndex
from astrofairy.tests._support import WorkshopTest


class HashEmbedder:
    dimension = 1024

    def _vector(self, text: str) -> list[float]:
        values: list[float] = []
        data = hashlib.sha256(text.encode("utf-8")).digest()
        while len(values) < self.dimension:
            data = hashlib.sha256(data).digest()
            values.extend(float(value) for value in data)
        values = values[: self.dimension]
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._vector("passage:" + text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector("query:" + text)


class CountingEmbedder(HashEmbedder):
    def __init__(self) -> None:
        self.embedded = 0

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        self.embedded += len(texts)
        return super().embed_passages(texts)


class SearchContractTests(WorkshopTest):
    def approved(self, **changes: Any) -> str:
        ref = self.workshop.library.propose({**self.proposal(), **changes})
        task = self.workshop.validation_task(ref)
        self.finish(task, "asset-fitness")
        self.workshop.library.adopt(ref, task)
        return ref

    def index(self, embedder: Any | None = None) -> SearchIndex:
        return SearchIndex(
            self.workshop.store,
            embedder=embedder or HashEmbedder(),
            tokenizer=CharTokenizer(),
        )

    def library(self, index: SearchIndex) -> Library:
        return Library(self.workshop.store, search=index)

    def test_explicit_refresh_builds_projection_and_reports_identity(self) -> None:
        ref = self.approved(summary="Evidence-based summaries", tags=["summary", "evidence"])
        index = self.index()
        with self.assertRaises(FairyError) as caught:
            index.search("evidence")
        self.assertEqual(caught.exception.code, "search_not_ready")
        self.assertIn("prepare_via", caught.exception.details)
        projection = index.refresh()
        self.assertEqual(projection["assets"], 1)
        self.assertGreaterEqual(projection["version"], 1)
        rows = self.library(index).search("evidence")
        self.assertEqual(rows[0]["ref"], ref)
        self.assertEqual(rows[0]["source_generation"], projection["generation"])
        self.assertEqual(rows[0]["table_version"], projection["version"])
        self.assertTrue(rows[0]["index_epoch"])

    def test_candidates_and_retired_heads_do_not_enter_discovery(self) -> None:
        old = self.approved(summary="Straße old", tags=[])
        candidate = self.workshop.library.propose({**self.proposal(), "summary": "Unadopted"})
        index = self.index()
        index.refresh()
        self.assertEqual(self.library(index).search("Straße")[0]["ref"], old)
        self.assertNotIn(candidate, [row["ref"] for row in self.library(index).search("")])
        new = self.approved(summary="New unrelated", tags=[])
        with self.assertRaises(FairyError) as caught:
            self.library(index).search("Straße")
        self.assertEqual(caught.exception.code, "search_not_ready")
        self.assertLess(
            caught.exception.details["projected_generation"], caught.exception.details["generation"]
        )
        index.refresh()
        self.assertNotIn(old, [row["ref"] for row in self.library(index).search("Straße")])
        self.workshop.library.retire(new)
        with self.assertRaises(FairyError):
            self.library(index).search("Straße")
        index.refresh()
        self.assertIn(old, [row["ref"] for row in self.library(index).search("Straße")])

    def test_scope_kind_browse_and_limits(self) -> None:
        personal = self.approved(summary="alpha personal", tags=[], kind="guide")
        team = self.approved(scope="team", summary="alpha team", tags=[], kind="case")
        index = self.index()
        index.refresh()
        library = self.library(index)
        self.assertEqual([row["ref"] for row in library.search("alpha", scope="team")], [team])
        self.assertEqual([row["ref"] for row in library.search("alpha", kind="guide")], [personal])
        self.assertEqual(len(library.search("")), 2)
        self.assertEqual(len(library.search("", limit=1)), 1)
        with self.assertRaises(FairyError):
            library.search("", limit=0)
        with self.assertRaises(FairyError):
            library.search("", limit=MAX_SEARCH_RESULTS + 1)
        first = library.search_page("", limit=1)
        self.assertEqual(len(first["matches"]), 1)
        self.assertEqual(first["total"], 2)
        second = library.search_page("", limit=1, cursor=first["next_cursor"])
        self.assertEqual(len(second["matches"]), 1)
        self.assertNotEqual(first["matches"][0]["ref"], second["matches"][0]["ref"])
        self.assertNotIn("next_cursor", second)
        with self.assertRaises(FairyError) as caught:
            library.search_page("", limit=1, cursor=first["next_cursor"], scope="team")
        self.assertEqual(caught.exception.code, "conflict")

    def test_chinese_body_and_metadata_terms_are_searchable(self) -> None:
        ref = self.approved(
            summary="订单数据清洗",
            tags=["中文", "检索"],
            content="订单数据清洗，缺失值待确认，不补零。依据活动数据制作汇报。",  # noqa: RUF001
        )
        index = self.index()
        index.refresh()
        library = self.library(index)
        self.assertEqual(library.search("缺失值")[0]["ref"], ref)
        self.assertEqual(library.search("订单")[0]["ref"], ref)
        self.assertEqual(library.search("中文")[0]["ref"], ref)

    def test_workflow_steps_and_locators_are_indexed(self) -> None:
        content = {
            "inputs": ["source"],
            "parameters": {},
            "steps": [
                {"instruction": "核实报名人数与到场人数", "done": "数字一致"},
                {"instruction": "制作演示文稿", "done": "文件可打开"},
            ],
        }
        self.approved(kind="workflow", summary="活动汇报流程", tags=["流程"], content=content)
        index = self.index()
        index.refresh()
        rows = self.library(index).search("到场人数")
        self.assertTrue(rows)
        self.assertEqual(rows[0]["locator"], "content.steps.0")

    def test_projection_reuse_and_embedding_cache(self) -> None:
        self.approved(summary="First", tags=[])
        embedder = CountingEmbedder()
        index = self.index(embedder)
        first = index.refresh()
        first_count = embedder.embedded
        second = index.refresh()
        self.assertEqual(second["table"], first["table"])
        self.assertEqual(embedder.embedded, first_count)
        self.approved(summary="Second", tags=[])
        third = index.refresh()
        self.assertNotEqual(third["table"], first["table"])
        self.assertGreater(embedder.embedded, first_count)

    def test_missing_table_version_requires_rebuild(self) -> None:
        self.approved(summary="Versioned", tags=[])
        index = self.index()
        index.refresh()
        with self.workshop.store.transaction():
            self.workshop.store.connection.execute(
                "UPDATE search_projection SET lance_version = 999 WHERE id = 1"
            )
        with self.assertRaises(FairyError) as caught:
            self.library(index).search("Versioned")
        self.assertEqual(caught.exception.code, "search_not_ready")
        index.refresh()
        self.assertTrue(self.library(index).search("Versioned"))

    def test_empty_library_does_not_start_model_or_projection(self) -> None:
        class ExplodingEmbedder(HashEmbedder):
            def embed_passages(self, _texts: list[str]) -> list[list[float]]:
                raise AssertionError("empty library must not start the model")

        index = SearchIndex(self.workshop.store, embedder=ExplodingEmbedder(), tokenizer=CharTokenizer())
        self.assertEqual(self.library(index).search("anything"), [])
        self.assertIsNone(self.workshop.store.projection())

    def test_pointer_without_watermark_replays_from_content_cache(self) -> None:
        self.approved(summary="Replayable", tags=[])
        embedder = CountingEmbedder()
        index = self.index(embedder)
        index.refresh()
        first_count = embedder.embedded
        with self.workshop.store.transaction():
            self.workshop.store.connection.execute("DELETE FROM search_projection WHERE id = 1")
        index.refresh()
        self.assertEqual(embedder.embedded, first_count)
        self.assertTrue(self.library(index).search("Replayable"))

    def test_profile_mismatch_requires_projection_rebuild(self) -> None:
        self.approved(summary="Profile", tags=[])
        index = self.index()
        index.refresh()
        with self.workshop.store.transaction():
            self.workshop.store.connection.execute(
                "UPDATE search_projection SET profile = 'other-profile' WHERE id = 1"
            )
        with self.assertRaises(FairyError) as caught:
            self.library(index).search("Profile")
        self.assertEqual(caught.exception.code, "search_not_ready")
        index.refresh()
        self.assertTrue(self.library(index).search("Profile"))

    def test_restore_invalidates_old_projection(self) -> None:
        ref = self.approved(summary="Restored", tags=[])
        index = self.index()
        index.refresh()
        backup = Path(self.temporary.name) / "search-backup"
        backup_state(self.home, backup)
        recovered = Path(self.temporary.name) / "search-recovered"
        restore_state(backup, recovered)
        with Workshop(recovered) as restored:
            self.assertIsNone(restored.store.projection())
            restored_index = SearchIndex(restored.store, embedder=HashEmbedder(), tokenizer=CharTokenizer())
            with self.assertRaises(FairyError) as caught:
                Library(restored.store, search=restored_index).search("Restored")
            self.assertEqual(caught.exception.code, "search_not_ready")
            restored_index.refresh()
            self.assertEqual(Library(restored.store, search=restored_index).search("Restored")[0]["ref"], ref)

    def test_real_e5_model_smoke_when_explicitly_enabled(self) -> None:
        if not os.environ.get("ASTROFAIRY_TEST_E5"):
            self.skipTest("Set ASTROFAIRY_TEST_E5 and ASTROFAIRY_MODEL_CACHE for the real-model smoke")
        cache = Path(os.environ["ASTROFAIRY_MODEL_CACHE"])
        self.approved(
            summary="制作 PPT 汇报",
            tags=["PPT", "汇报"],
            content="根据活动数据制作 PPT 汇报，核实报名和到场人数。",  # noqa: RUF001
        )
        index = SearchIndex(self.workshop.store, model_cache=cache)
        projection = index.refresh()
        self.assertEqual(projection["assets"], 1)
        rows = self.library(index).search("演示文稿")
        self.assertTrue(rows)
        self.assertEqual(rows[0]["profile"], index.profile_id)
