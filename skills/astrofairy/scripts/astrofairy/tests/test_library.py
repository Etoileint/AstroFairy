from __future__ import annotations

from astrofairy import FairyError
from astrofairy._contracts import canonical, parse_json
from astrofairy.tests._support import WorkshopTest


class LibraryTests(WorkshopTest):
    def test_adoption_policy_cannot_be_weakened_by_strategy(self) -> None:
        ref = self.workshop.library.propose(self.proposal())
        task = self.workshop.validation_task(ref)
        answer = self.workshop.submit(task, {"op": "answer", "text": "Skip the assessment"})
        with self.assertRaises(FairyError) as caught:
            self.workshop.submit(
                task,
                {
                    "op": "revise",
                    "goal": "Only count bytes",
                    "criteria": [{"id": "asset-fitness", "description": "Any bytes", "checker": "nonempty"}],
                    "reason": "Shortcut",
                    "user_basis": answer["seq"],
                },
            )
        self.assertEqual(caught.exception.code, "permission")

    def test_large_manual_is_pinned_then_read_in_bounded_parts(self) -> None:
        ref = self.workshop.library.propose(self.proposal("Useful instructions. " * 3000))
        self.workshop.library.adopt(ref, self.validated(ref))
        task = self.workshop.start("Use manual")
        metadata = self.workshop.invoke(task, "asset.read", {"ref": ref})
        self.assertEqual(metadata["result"]["read_with"], "content.read")
        part = self.workshop.invoke(task, "content.read", {"ref": ref, "limit": 20})
        self.assertEqual(len(part["result"]["text"]), 20)

    def validated(self, ref: str) -> str:
        task = self.workshop.validation_task(ref)
        self.finish(task, "asset-fitness")
        return task

    def test_candidate_excluded_until_exact_validation_and_adoption(self) -> None:
        ref = self.workshop.library.propose(self.proposal())
        self.assertEqual(self.workshop.library.search("evidence"), [])
        validation = self.validated(ref)
        self.workshop.library.adopt(ref, validation, "stable")
        self.assertEqual(self.workshop.library.search("evidence")[0]["ref"], ref)

    def test_different_completed_task_cannot_validate_candidate(self) -> None:
        ref = self.workshop.library.propose(self.proposal())
        unrelated = self.workshop.start("Unrelated")
        self.produce(unrelated)
        self.finish(unrelated)
        with self.assertRaises(FairyError):
            self.workshop.library.adopt(ref, unrelated)

    def test_failed_validation_does_not_activate_asset(self) -> None:
        ref = self.workshop.library.propose(self.proposal())
        task = self.workshop.validation_task(ref)
        self.workshop.submit(task, {"op": "close", "outcome": "failed"})
        with self.assertRaises(FairyError):
            self.workshop.library.adopt(ref, task)
        self.assertEqual(self.workshop.library.status(ref), "candidate")

    def test_stale_base_rejects_overwriting_concurrent_improvement(self) -> None:
        original = self.workshop.library.propose(self.proposal("original"))
        self.workshop.library.adopt(original, self.validated(original))
        second = self.workshop.library.propose(self.proposal("second"))
        third = self.workshop.library.propose(self.proposal("third"))
        second_task = self.validated(second)
        third_task = self.validated(third)
        self.workshop.library.adopt(second, second_task)
        with self.assertRaises(FairyError) as caught:
            self.workshop.library.adopt(third, third_task)
        self.assertEqual(caught.exception.code, "conflict")

    def test_pin_survives_update_and_retirement(self) -> None:
        original = self.workshop.library.propose(self.proposal("original"))
        self.workshop.library.adopt(original, self.validated(original))
        task = self.workshop.start("Use guide")
        self.workshop.invoke(task, "asset.read", {"ref": original})
        revised = self.workshop.library.propose(self.proposal("revised"))
        self.workshop.library.adopt(revised, self.validated(revised))
        self.workshop.library.retire(original)
        result = self.workshop.invoke(task, "asset.read", {"ref": original})
        self.assertEqual(result["result"]["asset"]["content"], "original")
        self.assertIn(original, self.workshop.state(task).assets)

    def test_share_bundle_is_data_and_requires_local_validation(self) -> None:
        ref = self.workshop.library.propose(self.proposal())
        self.workshop.library.adopt(ref, self.validated(ref))
        exported = self.workshop.library.export(ref)
        imported = self.workshop.library.import_bundle(exported)
        self.assertNotEqual(imported, ref)
        self.assertEqual(self.workshop.library.status(imported), "candidate")
        imported_evidence = self.workshop.library.get(imported)["evidence"]
        self.assertEqual(imported_evidence[1]["note"], self.proposal()["evidence"][0]["note"])
        self.assertTrue(imported_evidence[1]["source"].startswith("bundle:"))
        self.assertEqual(self.workshop.library.head("personal", "evidence-guide"), ref)
        self.assertNotIn("events", parse_json(exported.decode("utf-8")))

    def test_tampered_bundle_rejected(self) -> None:
        ref = self.workshop.library.propose(self.proposal())
        bundle = parse_json(self.workshop.library.export(ref).decode("utf-8"))
        bundle["package"]["content"] = "changed"
        with self.assertRaises(FairyError) as caught:
            self.workshop.library.import_bundle(canonical(bundle))
        self.assertEqual(caught.exception.code, "integrity")

    def test_workflow_needs_completion_conditions(self) -> None:
        proposal = {**self.proposal(), "kind": "workflow", "content": {"steps": [{"instruction": "Do work"}]}}
        with self.assertRaises(FairyError):
            self.workshop.library.propose(proposal)

    def test_positive_feedback_enters_separate_learning_task(self) -> None:
        task = self.workshop.start("Work")
        self.produce(task)
        self.finish(task)
        self.workshop.submit(
            task, {"op": "feedback", "kind": "positive", "text": "This organization made review easy"}
        )
        maintenance = self.workshop.submit(task, {"op": "learn"})["learning_task"]
        data = self.workshop.store.get(self.workshop.state(maintenance).inputs[0]["ref"])
        self.assertIn(b"positive", data)
        self.workshop.submit(maintenance, {"op": "close", "outcome": "failed"})
        self.assertEqual(self.workshop.state(task).outcome, "complete")

    def test_namespace_search_and_limit(self) -> None:
        ref = self.workshop.library.propose({**self.proposal(), "scope": "team"})
        self.workshop.library.adopt(ref, self.validated(ref))
        self.assertEqual(self.workshop.library.search("evidence", scope="personal"), [])
        self.assertEqual(len(self.workshop.library.search("evidence", scope="team")), 1)
        with self.assertRaises(FairyError):
            self.workshop.library.search("", limit=100)
