from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from astrofairy import FairyError, ResourcePolicy, Workshop
from astrofairy._contracts import canonical, digest
from astrofairy.tests._support import ROOT, WorkshopTest


class ResourcePolicyTests(WorkshopTest):
    def test_default_task_can_complete_after_more_than_sixteen_work_calls(self) -> None:
        task = self.workshop.start("Prepare a sourced brief through several bounded steps")
        for index in range(18):
            request = self.workshop.submit(task, {"op": "request", "purpose": f"Analyze section {index}"})
            output = self.workshop.submit(
                task, {"op": "report", "call": request["call"], "text": f"Section {index}: observed facts"}
            )
        self.publish(task, [output])
        self.assertEqual(self.finish(task)["outcome"], "complete")

    def test_task_freezes_policy_and_reports_warning_without_stopping_work(self) -> None:
        policy = ResourcePolicy(work_calls=4, warning_calls=2)
        task = self.workshop.start("Use an explicitly bounded resource policy", resources=policy)
        for _ in range(2):
            self.produce(task, publish=False)
        with Workshop(self.home) as reopened:
            resource = reopened.next(task)["resources"]
            self.assertEqual(resource["policy"], {"format": 1, "work_calls": 4, "warning_calls": 2})
            self.assertEqual(resource["fingerprint"], digest(canonical(resource["policy"])))
            self.assertEqual((resource["used_calls"], resource["remaining_calls"]), (2, 2))
            self.assertTrue(resource["warning"])
            self.assertFalse(resource["exhausted"])
            self.produce(task)
            self.assertEqual(reopened.next(task)["resources"]["remaining_calls"], 1)

    def test_context_reads_are_free_and_do_not_consume_the_work_budget(self) -> None:
        task = self.workshop.start(
            "Read context without spending work calls",
            resources=ResourcePolicy(work_calls=1, warning_calls=1),
        )
        self.workshop.invoke(task, "content.read", {"ref": "0" * 64})
        self.workshop.invoke(task, "content.read", {"ref": "1" * 64})
        result = self.workshop.invoke(task, "text.write", {"path": "result.md", "text": "usable"})
        self.assertEqual(result["status"], "ok")
        resource = self.workshop.next(task)["resources"]
        self.assertEqual((resource["used_calls"], resource["free_calls"]), (1, 2))
        self.assertEqual(resource["remaining_calls"], 0)

    def test_content_read_ceiling_is_24576_characters(self) -> None:
        task = self.workshop.start("Read a long source in one request")
        output = self.produce(task)
        accepted = self.workshop.invoke(task, "content.read", {"ref": output["ref"], "limit": 24576})
        self.assertEqual(accepted["status"], "ok")
        with self.assertRaises(FairyError):
            self.workshop.invoke(task, "content.read", {"ref": output["ref"], "limit": 24577})
        resource = self.workshop.next(task)["resources"]
        self.assertEqual((resource["used_calls"], resource["free_calls"]), (1, 1))

    def test_questions_remain_sequential_without_a_lifetime_quota(self) -> None:
        task = self.workshop.start("Clarify a changing brief")
        for index in range(6):
            self.workshop.submit(
                task, {"op": "ask", "question": f"Choose direction {index}", "recommendation": "Use A"}
            )
            with self.assertRaises(FairyError):
                self.workshop.submit(
                    task, {"op": "ask", "question": "An overlapping question", "recommendation": "Use A"}
                )
            self.workshop.submit(task, {"op": "answer", "text": "Use A"})
        self.produce(task)
        self.assertEqual(self.finish(task)["outcome"], "complete")

    def test_cli_rejects_invalid_policy_before_creating_home(self) -> None:
        variants = [{"work_calls": value} for value in (False, 0, -1, 1.5, "1024", None)] + [
            {"warning_calls": 1025},
            {"work_calls": 4, "warning_calls": 5},
            {"unlimited": True},
        ]
        for index, policy in enumerate(variants):
            with self.subTest(policy=policy):
                root = Path(self.temporary.name)
                path = root / "resources.json"
                path.write_text(json.dumps(policy), encoding="utf-8")
                home = root / f"invalid-resource-{index}"
                run = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        "-m",
                        "astrofairy",
                        "--home",
                        str(home),
                        "start",
                        "--request",
                        "Work",
                        "--resources",
                        str(path),
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    check=False,
                )
                self.assertEqual(run.returncode, 1, run.stderr)
                self.assertEqual(json.loads(run.stdout)["error"], "invalid")
                self.assertFalse(home.exists())

    def test_final_limit_preserves_reporting_and_honest_partial_delivery(self) -> None:
        task = self.workshop.start("Bounded work", resources=ResourcePolicy(work_calls=1, warning_calls=1))
        request = self.workshop.submit(task, {"op": "request", "purpose": "One useful result"})
        with self.assertRaises(FairyError) as caught:
            self.workshop.submit(task, {"op": "request", "purpose": "Exceed the limit"})
        self.assertEqual(caught.exception.code, "budget")
        self.workshop.submit(task, {"op": "report", "call": request["call"], "text": "Captured result"})
        state = self.workshop.state(task)
        self.publish(task, [state.outputs[0]])
        self.assertTrue(self.workshop.next(task)["resources"]["exhausted"])
        self.assertEqual(
            self.workshop.submit(task, {"op": "close", "outcome": "partial"})["outcome"], "partial"
        )

    def test_cli_policy_is_captured_once_and_cannot_be_revised_through_task_commands(self) -> None:
        root = Path(self.temporary.name)
        policy_path = root / "resources.json"
        policy_path.write_text('{"work_calls":4,"warning_calls":2}', encoding="utf-8")
        home = root / "configured"
        run = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "astrofairy",
                "--home",
                str(home),
                "start",
                "--request",
                "Work",
                "--resources",
                str(policy_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        task = json.loads(run.stdout)["task"]
        policy_path.write_text('{"work_calls":10000}', encoding="utf-8")
        with Workshop(home) as reopened:
            packet = reopened.next(task)
            self.assertEqual(packet["resources"]["policy"]["work_calls"], 4)
            with self.assertRaises(FairyError):
                reopened.submit(
                    task,
                    {
                        "op": "revise",
                        "goal": packet["goal"],
                        "criteria": packet["criteria"],
                        "reason": "Attempt to enlarge the fixed resource policy",
                        "resources": ResourcePolicy(work_calls=10000).snapshot(),
                    },
                )
            self.assertEqual(reopened.next(task)["seq"], packet["seq"])
