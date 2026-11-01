from __future__ import annotations

from typing import Any

from astrofairy import FairyError, Workshop
from astrofairy._library import MAX_SEARCH_RESULTS
from astrofairy._store import _search_text
from astrofairy.tests._support import WorkshopTest


class SearchContractTests(WorkshopTest):
    def approved(self, **changes: Any) -> str:
        ref = self.workshop.library.propose({**self.proposal(), **changes})
        task = self.workshop.validation_task(ref)
        self.finish(task, "asset-fitness")
        self.workshop.library.adopt(ref, task)
        return ref

    def test_unicode_metadata_values_match_through_api_tool_and_reopened_store(self) -> None:
        ref = self.approved(summary="Straße ÉTUDE Москва", tags=["ΟΣ", "日本語", 'quoted"tag', r"path\part"])
        queries = (
            "Straße",
            "STRASSE",
            "ÉTUDE",
            "étude",
            "\u041c\u041e\u0421\u041a\u0412\u0410",
            "ος",
            "\u03bf\u03c3",
            "日本",
            'quoted"tag',
            r"path\part",
        )
        for query in queries:
            with self.subTest(query=query):
                self.assertEqual(self.workshop.library.search(query)[0]["ref"], ref)
        task = self.workshop.start("Find a method")
        result = self.workshop.invoke(task, "asset.search", {"query": "STRASSE"})
        self.assertEqual(result["result"]["matches"][0]["ref"], ref)
        with Workshop(self.home) as reopened:
            self.assertEqual(reopened.library.search("ΟΣ")[0]["ref"], ref)
            self.assertEqual(reopened.library.get(ref)["summary"], "Straße ÉTUDE Москва")

    def test_tag_storage_syntax_and_content_do_not_become_searchable_metadata(self) -> None:
        self.approved(summary="Plain", tags=['quoted"tag', r"path\part"], content="body-only-secret")
        for query in ("[", "]", '\\"', "body-only-secret"):
            with self.subTest(query=query):
                self.assertEqual(self.workshop.library.search(query), [])
        self.assertTrue(self.workshop.library.search('quoted"tag'))
        self.assertTrue(self.workshop.library.search(r"path\part"))

    def test_casefold_only_boundaries_keep_accents_and_normalization_distinctions(self) -> None:
        ref = self.approved(summary="café \uff3a ① İ \u0131", tags=[])
        for query in ("café", "\uff5a", "①", "İ", "\u0131"):
            with self.subTest(query=query):
                self.assertEqual(self.workshop.library.search(query)[0]["ref"], ref)
        for query in ("cafe", "cafe\u0301", "Z", "1", "coffee"):
            with self.subTest(query=query):
                self.assertEqual(self.workshop.library.search(query), [])

    def test_head_selection_precedes_scoring_and_retirement_reveals_previous_head(self) -> None:
        old = self.approved(summary="Straße old", tags=[])
        candidate = self.workshop.library.propose({**self.proposal(), "summary": "Unadopted"})
        self.assertEqual(self.workshop.library.search("STRASSE")[0]["ref"], old)
        new = self.approved(summary="New unrelated", tags=[])
        self.assertEqual(self.workshop.library.search("STRASSE"), [])
        self.assertEqual(self.workshop.library.search("")[0]["ref"], new)
        self.workshop.library.retire(new)
        self.assertEqual(self.workshop.library.search("STRASSE")[0]["ref"], old)
        self.assertNotIn(candidate, [item["ref"] for item in self.workshop.library.search("")])

    def test_scoring_term_cap_literal_queries_scope_and_total_ties(self) -> None:
        personal = self.approved(summary="alpha beta %_", tags=[])
        team = self.approved(scope="team", summary="alpha beta %_", tags=[])
        other = self.approved(name="other-guide", summary="beta", tags=[])
        rows = self.workshop.library.search("alpha alpha beta")
        self.assertEqual([(r["ref"], r["score"]) for r in rows], [(personal, 3), (team, 3), (other, 1)])
        self.assertEqual(self.workshop.library.search("alpha", scope="team")[0]["ref"], team)
        self.assertEqual(self.workshop.library.search("%_")[0]["ref"], personal)
        self.assertEqual(self.workshop.library.search("' OR 1=1 --"), [])
        self.assertEqual(self.workshop.library.search(" ".join(["absent"] * 16 + ["alpha"])), [])
        self.assertEqual(len(self.workshop.library.search(" \t ", limit=1)), 1)

    def test_declared_and_actual_result_limit_agree_before_invocation(self) -> None:
        definition = self.workshop.describe("asset.search")
        self.assertEqual(definition["inputSchema"]["properties"]["limit"]["maximum"], MAX_SEARCH_RESULTS)
        task = self.workshop.start("Find a method")
        for limit in (0, MAX_SEARCH_RESULTS + 1):
            with self.subTest(limit=limit), self.assertRaises(FairyError):
                self.workshop.invoke(task, "asset.search", {"query": "", "limit": limit})
        self.assertEqual(self.workshop.state(task).calls, {})
        self.assertEqual(self.workshop.library.search("", limit=MAX_SEARCH_RESULTS), [])

    def test_materialization_folds_selected_heads_once_and_browsing_bypasses_tags(self) -> None:
        old = self.approved(summary="Old", tags=[])
        current = self.approved(summary="Current", tags=[])
        other = self.approved(scope="team", summary="Other", tags=[])
        self.workshop.store.connection.execute(
            "UPDATE assets SET tags = ? WHERE ref IN (?, ?)", ("Malformed fixture JSON", old, other)
        )
        calls: list[str] = []

        def traced(name: str, summary: str, tags: str) -> str:
            calls.append(summary)
            return _search_text(name, summary, tags)

        self.workshop.store.connection.create_function(
            "astrofairy_search_text", 3, traced, deterministic=True
        )
        rows = self.workshop.library.search(" ".join(["current"] * 16), scope="personal")
        self.assertEqual([(row["ref"], row["score"]) for row in rows], [(current, 16)])
        self.assertEqual(calls, ["Current"])
        calls.clear()
        self.assertEqual(len(self.workshop.library.search("")), 2)
        self.assertEqual(calls, [])
