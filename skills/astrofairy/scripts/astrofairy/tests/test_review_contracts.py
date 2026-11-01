from __future__ import annotations

from typing import Any

from astrofairy import FairyError, Workshop
from astrofairy._capabilities import Context, builtins
from astrofairy._contracts import canonical, parse_json
from astrofairy._kernel import admit_review
from astrofairy.tests._support import WorkshopTest, mock_capability


class ReviewContractTests(WorkshopTest):
    def test_republication_and_returning_content_preserve_conflict(self) -> None:
        task = self.workshop.start("Work")
        original = self.produce(task, "A")
        self.workshop.check(task)
        self.semantic(task, verdict="fail")
        failed = self.workshop.state(task).reviews[-1]["id"]
        for alternate in (False, True):
            with self.subTest(alternate=alternate):
                if alternate:
                    self.produce(task, "B")
                self.workshop.submit(task, {"op": "publish", "ref": original})
                self.semantic(task)
                with self.assertRaises(FairyError):
                    self.workshop.submit(task, {"op": "close", "outcome": "complete"})
                self.assertIn(failed, [item["id"] for item in self.workshop.state(task).active_reviews()])
        with Workshop(self.home) as reopened:
            self.assertFalse(reopened.state(task).complete())
        self.semantic(task, replaces=[failed])
        self.assertTrue(self.workshop.state(task).complete())

    def test_noop_revision_preserves_failure_but_real_context_change_invalidates(self) -> None:
        task = self.workshop.start("Work")
        self.produce(task)
        self.workshop.check(task)
        self.semantic(task, verdict="fail")
        state = self.workshop.state(task)
        command = {
            "op": "revise",
            "goal": state.spec["goal"],
            "criteria": state.spec["criteria"],
            "assumptions": state.spec["assumptions"],
            "reason": "Restate agreement",
        }
        self.workshop.submit(task, command)
        self.assertEqual(self.workshop.state(task).revision, state.revision)
        self.semantic(task)
        self.assertFalse(self.workshop.state(task).complete())
        self.workshop.submit(task, {**command, "goal": "Changed goal"})
        self.assertEqual(self.workshop.state(task).revision, state.revision + 1)
        self.assertEqual(self.workshop.state(task).active_reviews(), [])
        self.finish(task)

    def test_forwarded_answer_invalidates_even_unchanged_spec(self) -> None:
        task = self.workshop.start("Work")
        self.produce(task)
        self.workshop.check(task)
        self.semantic(task)
        self.workshop.submit(task, {"op": "answer", "text": "Please reconsider"})
        self.assertFalse(self.workshop.state(task).complete())

    def test_observed_contract_must_match_durable_invocation(self) -> None:
        original = builtins()["content.check"]
        variants: list[dict[str, Any]] = [
            {"checked": None},
            {"checked": {"ref": "wrong", "checker": "nonempty", "parameters": {}}},
            {"checked": {"checker": "json"}},
            {"checked": {"parameters": {"text": "different"}}},
            {"verdict": "invalid"},
            {"basis": ""},
            {"basis": 1},
        ]
        for replacement in variants:
            with self.subTest(replacement=replacement):
                task = self.workshop.start("Work")
                self.produce(task)
                self.workshop.register("content.check", original, replace=True)
                self.workshop.check(task)
                prior = canonical(self.workshop.state(task).reviews)

                def malformed(
                    context: Context, parameters: dict[str, Any], changes: dict[str, Any] = replacement
                ) -> dict[str, Any]:
                    return {**original.handler(context, parameters), **changes}

                self.workshop.register(
                    "content.check", mock_capability("read", malformed, original), replace=True
                )
                with self.assertRaises(FairyError):
                    self.workshop.check(task)
                self.assertEqual(canonical(self.workshop.state(task).reviews), prior)

    def test_mutated_arguments_cannot_redefine_checked_identity(self) -> None:
        task = self.workshop.start("Work")
        ref = self.produce(task)
        original = builtins()["content.check"]

        def changed(context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
            parameters["checker"] = "json"
            return original.handler(context, parameters)

        self.workshop.register("content.check", mock_capability("read", changed, original), replace=True)
        with self.assertRaises(FairyError):
            self.workshop.check(task)
        state = self.workshop.state(task)
        self.assertFalse(state.reviews)
        self.assertEqual(list(state.calls.values())[-1]["parameters"]["checker"], "nonempty")
        self.assertEqual(state.artifact["ref"], ref)

    def test_review_links_exact_observation_and_kernel_rejects_unbacked_review(self) -> None:
        task = self.workshop.start("Work")
        self.produce(task)
        self.workshop.check(task)
        state = self.workshop.state(task)
        review = state.active_reviews()[0]
        call = state.calls[review["call"]]
        self.assertEqual(call["result"]["checked"], call["parameters"])
        for changes in ({"call": "absent"}, {"basis": "Invented basis"}, {"verdict": "fail"}):
            with self.subTest(changes=changes), self.assertRaises(FairyError):
                admit_review(state, {**review, **changes, "replaces": []})
        forged = {**review, "id": state.seq + 1, "call": "absent", "replaces": [review["id"]]}
        state.reviews.append(forged)
        self.assertEqual(state.active_reviews(), [review])

    def test_validation_cannot_erase_failure_by_republishing_candidate(self) -> None:
        ref = self.workshop.library.propose(self.proposal())
        task = self.workshop.validation_task(ref)
        self.workshop.check(task)
        self.semantic(task, "asset-fitness", "fail")
        self.produce(task, self.workshop.store.get(ref).decode("utf-8"))
        self.workshop.check(task)
        self.semantic(task, "asset-fitness")
        with self.assertRaises(FairyError):
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        with self.assertRaises(FairyError):
            self.workshop.library.adopt(ref, task)
        self.assertEqual(self.workshop.library.status(ref), "candidate")

    def test_closed_effect_domain_and_failure_classification(self) -> None:
        for unsupported in ("delete", "send", "READ", "", "network"):
            with self.subTest(effect=unsupported):
                with self.assertRaises(FairyError):
                    mock_capability(unsupported, lambda _context, _parameters: {})
                before = self.workshop.store.tasks()
                with self.assertRaises(FairyError):
                    self.workshop.start("Work", effects=[unsupported])
                self.assertEqual(self.workshop.store.tasks(), before)
        effects: list[str] = []

        def invalid_result(_context: Context, _parameters: dict[str, Any]) -> dict[str, Any]:
            effects.append("performed")
            return {"outputs": [], "bad": object()}

        for effect in ("read", "reason", "write"):
            with self.subTest(effect=effect):
                task = self.workshop.start("Work")
                self.workshop.register("custom", mock_capability(effect, invalid_result), replace=True)
                result = self.workshop.invoke(task, "custom", {})
                self.assertEqual(result["status"], "unknown" if effect == "write" else "failed")
                if effect == "write":
                    count = len(effects)
                    with self.assertRaises(FairyError):
                        self.workshop.invoke(task, "custom", {})
                    self.assertEqual(len(effects), count)
                self.assertEqual(parse_json(canonical(result).decode("utf-8")), result)
