from __future__ import annotations

from pathlib import Path
from typing import Any

from astrofairy import FairyError
from astrofairy._contracts import (
    canonical,
    members_value,
    parse_json,
    relative_path,
    snapshot_value,
)
from astrofairy.tests._support import WorkshopTest


class MemberSnapshotContractTests(WorkshopTest):
    def publish_members(self, task: str, outputs: list[dict[str, Any]], roles: list[str]) -> dict[str, Any]:
        return self.publish(task, outputs, roles=roles)

    def explicit(self, *criteria: dict[str, Any], **spec: Any) -> dict[str, Any]:
        return {"criteria": list(criteria), **spec}

    def test_same_bytes_keep_distinct_member_identity_and_delivery(self) -> None:
        task = self.workshop.start(
            "Deliver two named files",
            spec=self.explicit(
                {"id": "goal", "description": "Relevant", "checker": "semantic"},
                {
                    "id": "usable",
                    "description": "Nonempty",
                    "checker": "nonempty",
                    "scope": "collection",
                },
            ),
        )
        first = self.produce(task, "identical bytes", publish=False, path="a.txt")
        request = self.workshop.submit(task, {"op": "request", "purpose": "second view"})
        second = self.workshop.submit(
            task,
            {
                "op": "report",
                "call": request["call"],
                "text": "identical bytes",
                "path": "b.txt",
                "media_type": "text/plain",
            },
        )
        self.assertEqual(first["ref"], second["ref"])
        self.assertNotEqual(first["media_type"], second["media_type"])
        self.publish_members(task, [first, second], ["main", "main"])
        snapshot = self.workshop.state(task).snapshot
        self.assertEqual([member["path"] for member in snapshot["members"]], ["a.txt", "b.txt"])
        self.assertEqual({member["ref"] for member in snapshot["members"]}, {first["ref"]})
        self.workshop.submit(task, {"op": "check"})
        self.semantic(task)
        delivery = self.workshop.submit(task, {"op": "close", "outcome": "complete"})["delivery"]
        self.assertEqual(sorted(delivery["files"]), ["a.txt", "b.txt"])
        self.assertEqual(
            [Path(delivery["files"][name]).read_text(encoding="utf-8") for name in ("a.txt", "b.txt")],
            ["identical bytes", "identical bytes"],
        )
        receipt = parse_json(Path(delivery["receipt_path"]).read_text(encoding="utf-8"))
        self.assertEqual(receipt["snapshot"]["ref"], snapshot["ref"])
        self.assertEqual({member["path"] for member in receipt["snapshot"]["members"]}, {"a.txt", "b.txt"})

    def test_member_paths_are_nfc_portable_and_collision_free(self) -> None:
        invalid = ["", "/absolute", "../escape", "a/../b", "a\\b", "a//b", "a/", "CON", "a. "]
        for value in invalid:
            with self.subTest(path=value), self.assertRaises(FairyError):
                relative_path(value)
        with self.assertRaises(FairyError) as caught:
            relative_path("é.txt")
        self.assertEqual(caught.exception.details, {"suggested": "é.txt"})
        base = {"ref": "0" * 64, "bytes": 1, "media_type": "text/plain", "role": "main"}
        for paths in (("Report.md", "report.md"), ("a", "a/b")):
            with self.subTest(paths=paths), self.assertRaises(FairyError):
                members_value([{**base, "path": path} for path in paths])
        with self.assertRaises(FairyError):
            members_value([])
        self.assertEqual(
            members_value(
                [
                    {**base, "path": "b.txt"},
                    {**base, "path": "a.txt"},
                ]
            )[0]["path"],
            "a.txt",
        )

    def test_required_roles_block_complete_until_covered(self) -> None:
        task = self.workshop.start(
            "Deliver a report and data",
            spec=self.explicit(
                {"id": "goal", "description": "Relevant", "checker": "semantic"},
                required_roles=["report", "data"],
            ),
        )
        report = self.produce(task, "report body", publish=False, path="report.md")
        self.publish_members(task, [report], ["report"])
        self.assertEqual(self.workshop.next(task)["missing_roles"], ["data"])
        self.assertEqual(self.workshop.next(task)["action"], "publish")
        self.semantic(task)
        with self.assertRaises(FairyError):
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        data = self.produce(task, "1,2", publish=False, path="data.csv")
        self.publish_members(task, [report, data], ["report", "data"])
        self.assertEqual(self.workshop.next(task)["missing_roles"], [])
        self.semantic(task)
        self.assertEqual(self.workshop.submit(task, {"op": "check"})["checks"], [])
        self.assertEqual(
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})["outcome"], "complete"
        )

    def test_criterion_scopes_bind_content_members_and_collections(self) -> None:
        task = self.workshop.start(
            "Scoped checks",
            spec=self.explicit(
                {
                    "id": "bytes",
                    "description": "Every content is nonempty",
                    "checker": "nonempty",
                    "scope": "content",
                },
                {
                    "id": "syntax",
                    "description": "Data is JSON",
                    "checker": "json",
                    "scope": "member",
                    "target": "data.json",
                },
                {
                    "id": "usable",
                    "description": "Snapshot is nonempty",
                    "checker": "nonempty",
                    "scope": "collection",
                },
            ),
        )
        data = self.produce(task, "{}", publish=False, path="data.json")
        note = self.produce(task, "needle", publish=False, path="note.txt")
        self.publish_members(task, [data, note], ["data", "note"])
        results = self.workshop.submit(task, {"op": "check"})["checks"]
        self.assertEqual(len(results), 4)
        self.assertTrue(all(item["result"]["verdict"] == "pass" for item in results))
        reviews = self.workshop.state(task).active_reviews()
        targets = {review["criterion"]: review["target"] for review in reviews}
        self.assertEqual(targets["syntax"]["scope"], "member")
        self.assertEqual(targets["syntax"]["member"]["path"], "data.json")
        self.assertEqual(targets["usable"]["scope"], "collection")
        self.assertEqual(targets["usable"]["paths"], ["data.json", "note.txt"])
        content_refs = {review["target"]["ref"] for review in reviews if review["criterion"] == "bytes"}
        self.assertEqual(content_refs, {data["ref"], note["ref"]})
        self.publish_members(task, [note], ["note"])
        packet = self.workshop.next(task)
        self.assertIn("target_missing", {issue["reason"] for issue in packet["issues"]})
        self.assertFalse(self.workshop.state(task).complete())

    def test_collection_nonempty_rejects_an_empty_member(self) -> None:
        task = self.workshop.start(
            "Collection checks",
            spec=self.explicit(
                {
                    "id": "usable",
                    "description": "Snapshot is nonempty",
                    "checker": "nonempty",
                    "scope": "collection",
                }
            ),
        )
        workspace = Path(self.workshop.next(task)["workspace"])
        (workspace / "empty.txt").write_bytes(b"")
        empty = self.workshop.invoke(task, "file.capture", {"path": "empty.txt"})["outputs"][0]
        self.publish_members(task, [empty], ["main"])
        result = self.workshop.submit(task, {"op": "check"})["checks"][0]
        self.assertEqual(result["result"]["verdict"], "fail")
        self.assertFalse(self.workshop.state(task).complete())
        content = self.produce(task, "content", publish=False, path="content.txt")
        self.publish_members(task, [content], ["main"])
        self.assertEqual(
            self.workshop.submit(task, {"op": "check"})["checks"][0]["result"]["verdict"], "pass"
        )
        self.assertTrue(self.workshop.state(task).complete())

    def test_failure_survives_republish_and_is_disposed_by_current_check(self) -> None:
        task = self.workshop.start(
            "Failure disposition",
            spec=self.explicit(
                {
                    "id": "must",
                    "description": "Must contain X",
                    "checker": "contains",
                    "parameters": {"text": "X"},
                    "scope": "content",
                }
            ),
        )
        bad = self.produce(task, "bad", publish=False, path="bad.txt")
        self.publish_members(task, [bad], ["main"])
        self.assertEqual(
            self.workshop.submit(task, {"op": "check"})["checks"][0]["result"]["verdict"], "fail"
        )
        failure = self.workshop.state(task).unresolved_failures()[0]
        good = self.produce(task, "X good", publish=False, path="good.txt")
        self.publish_members(task, [good], ["main"])
        state = self.workshop.state(task)
        self.assertEqual([item["id"] for item in state.unresolved_failures()], [failure["id"]])
        self.assertEqual(state.next_action(), "review")
        self.assertFalse(state.complete())
        self.assertEqual(
            self.workshop.submit(task, {"op": "check"})["checks"][0]["result"]["verdict"], "pass"
        )
        self.assertEqual(self.workshop.state(task).unresolved_failures(), [])
        self.assertTrue(self.workshop.state(task).complete())

    def test_rename_without_content_change_keeps_failure_until_replacement(self) -> None:
        task = self.workshop.start(
            "Rename disposition",
            spec=self.explicit({"id": "goal", "description": "Relevant", "checker": "semantic"}),
        )
        first = self.produce(task, "same content", publish=False, path="a.txt")
        self.publish_members(task, [first], ["main"])
        self.semantic(task, verdict="fail")
        failure = self.workshop.state(task).unresolved_failures()[0]
        renamed = self.produce(task, "same content", publish=False, path="b.txt")
        self.publish_members(task, [renamed], ["main"])
        self.assertEqual(renamed["ref"], first["ref"])
        state = self.workshop.state(task)
        self.assertEqual([item["id"] for item in state.unresolved_failures()], [failure["id"]])
        self.semantic(task)
        self.assertFalse(self.workshop.state(task).complete())
        self.semantic(task, replaces=[failure["id"]])
        self.assertTrue(self.workshop.state(task).complete())

    def test_member_role_change_does_not_clear_mechanical_failure(self) -> None:
        task = self.workshop.start(
            "Member identity",
            spec=self.explicit(
                {
                    "id": "syntax",
                    "description": "Data is JSON",
                    "checker": "json",
                    "scope": "member",
                    "target": "data.json",
                }
            ),
        )
        invalid = self.produce(task, "not-json", publish=False, path="data.json")
        self.publish_members(task, [invalid], ["data"])
        self.assertEqual(
            self.workshop.submit(task, {"op": "check"})["checks"][0]["result"]["verdict"], "fail"
        )
        failure = self.workshop.state(task).unresolved_failures()[0]
        same_content = self.produce(task, "not-json", publish=False, path="data.json")
        self.publish_members(task, [same_content], ["report"])
        state = self.workshop.state(task)
        self.assertEqual([item["id"] for item in state.unresolved_failures()], [failure["id"]])
        self.assertEqual(
            self.workshop.submit(task, {"op": "check"})["checks"][0]["result"]["verdict"], "fail"
        )
        self.assertFalse(self.workshop.state(task).complete())
        valid = self.produce(task, "{}", publish=False, path="data.json")
        self.publish_members(task, [valid], ["report"])
        self.assertEqual(
            self.workshop.submit(task, {"op": "check"})["checks"][0]["result"]["verdict"], "pass"
        )
        self.assertTrue(self.workshop.state(task).complete())

    def test_semantic_review_is_bound_to_the_current_snapshot(self) -> None:
        task = self.workshop.start(
            "Snapshot-bound review",
            spec=self.explicit({"id": "goal", "description": "Relevant", "checker": "semantic"}),
        )
        first = self.produce(task, "first", publish=False, path="a.txt")
        self.publish_members(task, [first], ["main"])
        self.semantic(task)
        self.assertTrue(self.workshop.state(task).complete())
        second = self.produce(task, "second", publish=False, path="b.txt")
        self.publish_members(task, [first, second], ["main", "main"])
        self.assertEqual(self.workshop.state(task).active_reviews(), [])
        self.assertFalse(self.workshop.state(task).complete())
        self.semantic(task)
        self.assertTrue(self.workshop.state(task).complete())

    def test_pure_content_review_is_reused_across_snapshot_changes(self) -> None:
        task = self.workshop.start(
            "Content reuse",
            spec=self.explicit(
                {
                    "id": "usable",
                    "description": "Content is nonempty",
                    "checker": "nonempty",
                    "scope": "content",
                }
            ),
        )
        first = self.produce(task, "first", publish=False, path="a.txt")
        self.publish_members(task, [first], ["main"])
        criteria = self.workshop.state(task).spec["criteria"]
        criteria[0]["target"] = first["ref"]
        self.workshop.submit(
            task,
            {
                "op": "revise",
                "goal": "Content reuse",
                "criteria": criteria,
                "reason": "Bind the exact content target",
            },
        )
        self.assertEqual(len(self.workshop.submit(task, {"op": "check"})["checks"]), 1)
        calls = len(self.workshop.state(task).calls)
        second = self.produce(task, "second", publish=False, path="b.txt")
        self.publish_members(task, [first, second], ["main", "extra"])
        result = self.workshop.submit(task, {"op": "check"})
        self.assertEqual(result["checks"], [])
        self.assertEqual(len(result["reused"]), 1)
        self.assertEqual(len(self.workshop.state(task).calls), calls + 1)

    def test_candidate_membership_without_exact_policy_checks_cannot_adopt(self) -> None:
        candidate = self.workshop.library.propose(self.proposal())
        content = self.workshop.store.get(candidate).decode("utf-8")
        task = self.workshop.start(
            "Ordinary task containing candidate bytes",
            spec=self.explicit({"id": "goal", "description": "Relevant", "checker": "semantic"}),
        )
        output = self.produce(task, content, publish=False, path="candidate.json")
        self.publish_members(task, [output], ["report"])
        self.semantic(task)
        self.assertEqual(
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})["outcome"], "complete"
        )
        with self.assertRaises(FairyError):
            self.workshop.library.adopt(candidate, task)
        self.assertEqual(self.workshop.library.status(candidate), "candidate")

    def test_provisional_agreement_requires_refinement_before_complete(self) -> None:
        task = self.workshop.start("Provisional work")
        self.assertEqual(self.workshop.next(task)["action"], "refine")
        self.produce(task)
        with self.assertRaises(FairyError):
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.refine(task)
        self.workshop.submit(task, {"op": "check"})
        self.semantic(task)
        self.assertEqual(
            self.workshop.submit(task, {"op": "close", "outcome": "complete"})["outcome"], "complete"
        )

    def test_snapshot_identity_is_order_independent(self) -> None:
        base = {
            "ref": "0" * 64,
            "path": "a.txt",
            "bytes": 1,
            "media_type": "text/plain",
            "role": "main",
        }
        other = {**base, "path": "b.txt"}
        self.assertEqual(snapshot_value([base, other])["ref"], snapshot_value([other, base])["ref"])
        self.assertEqual(snapshot_value([base, other])["members"][0]["path"], "a.txt")
        self.assertEqual(
            canonical(snapshot_value([base, other])["members"]),
            canonical(snapshot_value([base, other])["members"]),
        )
