from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from astrofairy import FairyError
from astrofairy.tests._support import ROOT, WorkshopTest


class FairyStagePacketTests(WorkshopTest):
    def plan(self, *members: dict[str, str]) -> dict[str, Any]:
        return {"members": list(members)}

    def test_skill_identity_is_unique_fairy(self) -> None:
        skill = ROOT / "skills/fairy/SKILL.md"
        self.assertTrue(skill.is_file())
        self.assertIn("name: fairy\n", skill.read_text(encoding="utf-8"))
        self.assertFalse((ROOT / "skills/astrofairy").exists())

    def test_next_stage_packet_templates_and_completion(self) -> None:
        task = self.workshop.start("Stage packet")
        packet = self.workshop.next(task)
        self.assertEqual(packet["stage_packet_version"], 1)
        self.assertEqual(packet["action"], "refine")
        self.assertEqual(packet["payload"]["op"], "revise")
        self.assertFalse(packet["completion"]["provisional_refined"])
        self.assertEqual(packet["recovery"]["task"], task)
        self.assertEqual(packet["recovery"]["seq"], packet["seq"])
        self.workshop.submit(
            task,
            {
                "op": "revise",
                "goal": packet["goal"],
                "criteria": packet["criteria"],
                "reason": "Refine for the actual task",
            },
        )
        packet = self.workshop.next(task)
        self.assertEqual((packet["action"], packet["payload"]["op"]), ("produce", "request"))
        request = self.workshop.submit(task, packet["payload"])
        report = self.workshop.submit(
            task,
            {"op": "report", "call": request["call"], "text": "result", "path": "result.md"},
        )
        packet = self.workshop.next(task)
        self.assertEqual((packet["action"], packet["payload"]["op"]), ("publish", "publish"))
        self.assertEqual(packet["payload"]["members"][0]["ref"], report["ref"])
        self.publish(task, [report], roles=["main"])
        packet = self.workshop.next(task)
        self.assertEqual((packet["action"], packet["payload"]["op"]), ("review", "review"))
        self.assertEqual(packet["payload"]["criterion"], "goal")
        self.assertGreaterEqual(len(packet["payload"]["evidence"]), 1)
        self.assertFalse(packet["completion"]["complete"])

    def test_mechanical_issue_payload_is_check_not_a_model_pass(self) -> None:
        task = self.workshop.start(
            "Mechanical stage",
            spec={
                "criteria": [
                    {
                        "id": "usable",
                        "description": "Content is nonempty",
                        "checker": "nonempty",
                        "scope": "content",
                    }
                ]
            },
        )
        self.produce(task)
        packet = self.workshop.next(task)
        self.assertEqual(packet["action"], "review")
        self.assertEqual(
            packet["payload"],
            {"op": "check", "criterion": "usable", "expected_seq": packet["seq"]},
        )

    def test_prepare_delivery_captures_publishes_and_checks(self) -> None:
        task = self.workshop.start(
            "Prepare a multi-file delivery",
            spec={
                "criteria": [
                    {"id": "goal", "description": "Relevant", "checker": "semantic"},
                    {
                        "id": "usable",
                        "description": "Nonempty",
                        "checker": "nonempty",
                        "scope": "collection",
                    },
                ],
                "required_roles": ["report", "data"],
            },
        )
        workspace = Path(self.workshop.next(task)["workspace"])
        (workspace / "report.md").write_text("report body", encoding="utf-8")
        (workspace / "data.csv").write_text("a,1\n", encoding="utf-8")
        result = self.workshop.prepare_delivery(
            task,
            self.plan(
                {"path": "report.md", "role": "report"},
                {"path": "data.csv", "role": "data", "media_type": "text/csv"},
            ),
        )
        self.assertEqual([member["role"] for member in result["members"]], ["report", "data"])
        self.assertEqual([check["result"]["verdict"] for check in result["checks"]], ["pass"])
        self.assertFalse(self.workshop.state(task).complete())
        self.semantic(task)
        delivery = self.workshop.submit(task, {"op": "close", "outcome": "complete"})
        self.assertEqual(sorted(delivery["files"]), ["data.csv", "report.md"])

    def test_prepare_delivery_resume_reuses_committed_members(self) -> None:
        task = self.workshop.start(
            "Resume preparation",
            spec={"criteria": [{"id": "goal", "description": "Relevant", "checker": "semantic"}]},
        )
        workspace = Path(self.workshop.next(task)["workspace"])
        (workspace / "a.txt").write_text("a", encoding="utf-8")
        with self.assertRaises(FairyError) as caught:
            self.workshop.prepare_delivery(
                task,
                self.plan(
                    {"path": "a.txt", "role": "main"},
                    {"path": "b.txt", "role": "main"},
                ),
            )
        self.assertEqual(caught.exception.details["completed"], ["a.txt"])
        self.assertEqual(caught.exception.details["remaining"], ["b.txt"])
        self.assertIn("seq", caught.exception.details)
        (workspace / "b.txt").write_text("b", encoding="utf-8")
        calls = len(self.workshop.state(task).calls)
        result = self.workshop.prepare_delivery(
            task,
            self.plan(
                {"path": "a.txt", "role": "main"},
                {"path": "b.txt", "role": "main"},
            ),
        )
        self.assertEqual(result["reused_members"], ["a.txt"])
        self.assertEqual(len(self.workshop.state(task).calls), calls + 1)
        self.assertEqual(
            self.workshop.prepare_delivery(
                task,
                self.plan(
                    {"path": "a.txt", "role": "main"},
                    {"path": "b.txt", "role": "main"},
                ),
            )["published"].get("reused"),
            True,
        )

    def test_prepare_delivery_rejects_invalid_plans_and_closed_tasks(self) -> None:
        task = self.workshop.start("Invalid plans")
        workspace = Path(self.workshop.next(task)["workspace"])
        (workspace / "a.txt").write_text("a", encoding="utf-8")
        variants = [
            {},
            {"members": []},
            {"members": [{"path": "a.txt"}]},
            {"members": [{"path": "../escape", "role": "main"}]},
            {"members": [{"path": "a.txt", "role": "main", "extra": True}]},
            {
                "members": [
                    {"path": "a.txt", "role": "main"},
                    {"path": "a.txt", "role": "main"},
                ]
            },
        ]
        for plan in variants:
            with self.subTest(plan=plan), self.assertRaises(FairyError):
                self.workshop.prepare_delivery(task, plan)
        closed = self.workshop.start("Closed")
        self.workshop.submit(closed, {"op": "close", "outcome": "cancelled"})
        with self.assertRaises(FairyError):
            self.workshop.prepare_delivery(closed, self.plan({"path": "a.txt", "role": "main"}))

    def test_prepare_delivery_cli_uses_the_recorded_composite(self) -> None:
        task = self.workshop.start(
            "CLI preparation",
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
        workspace = Path(self.workshop.next(task)["workspace"])
        (workspace / "report.md").write_text("content", encoding="utf-8")
        plan = Path(self.temporary.name) / "plan.json"
        plan.write_text(json.dumps({"members": [{"path": "report.md", "role": "report"}]}), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "astrofairy",
                "--home",
                str(self.home),
                "prepare-delivery",
                task,
                "--members",
                str(plan),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual([member["path"] for member in payload["members"]], ["report.md"])
        self.assertEqual(payload["next"]["action"], "review")
