from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from astrofairy._contracts import (
    ResourcePolicy,
    canonical,
    criterion_fingerprint,
    delivery_plan_value,
    digest,
    effect_value,
    integer,
    member_value,
    object_value,
    snapshot_value,
    text_value,
)
from astrofairy._errors import FairyError


@dataclass
class State:
    task: str
    spec: dict[str, Any]
    seq: int = 0
    revision: int = 1
    calls: dict[str, dict[str, Any]] = field(default_factory=dict)
    snapshots: list[dict[str, Any]] = field(default_factory=list)
    reviews: list[dict[str, Any]] = field(default_factory=list)
    inputs: list[dict[str, Any]] = field(default_factory=list)
    feedback: list[dict[str, Any]] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    learning_decisions: list[dict[str, Any]] = field(default_factory=list)
    delivery_plan: dict[str, Any] | None = None
    delivery_progress: dict[str, dict[str, Any]] = field(default_factory=dict)
    question: dict[str, Any] | None = None
    question_count: int = 0
    outcome: str | None = None
    checker_contracts: dict[str, str] = field(default_factory=dict)

    @property
    def snapshot(self) -> dict[str, Any] | None:
        return self.snapshots[-1] if self.snapshots else None

    @property
    def outputs(self) -> list[dict[str, Any]]:
        return [item for call in self.calls.values() for item in call["outputs"]]

    def current_targets(self, criterion: dict[str, Any]) -> list[dict[str, Any]]:
        snapshot = self.snapshot
        if snapshot is None:
            return []
        members = snapshot["members"]
        by_path = {member["path"]: member for member in members}
        present = {member["ref"] for member in members}
        scope = criterion["scope"]
        target = criterion["target"]
        if scope == "content":
            if target is None:
                refs = sorted(present)
            elif isinstance(target, str):
                refs = [target] if target in present else []
            else:
                refs = [] if any(ref not in present for ref in target) else target
            return [{"scope": "content", "ref": ref} for ref in refs]
        if scope == "member":
            if not isinstance(target, str) or target not in by_path:
                return []
            return [{"scope": "member", "member": by_path[target]}]
        if target is None:
            selected = members
        else:
            if any(path not in by_path for path in target):
                return []
            selected = [by_path[path] for path in target]
        return [
            {
                "scope": "collection",
                "snapshot": snapshot["ref"],
                "paths": [member["path"] for member in selected],
            }
        ]

    def _review_applies(
        self, review: dict[str, Any], criterion: dict[str, Any], target: dict[str, Any]
    ) -> bool:
        if (
            review["criterion"] != criterion["id"]
            or review["criterion_fingerprint"] != criterion_fingerprint(criterion)
            or review["revision"] != self.revision
            or canonical(review["target"]) != canonical(target)
        ):
            return False
        snapshot = self.snapshot
        if review["producer"] == "model":
            return (
                snapshot is not None
                and review.get("snapshot") == snapshot["ref"]
                and review_is_grounded(self, review, self.checker_contracts)
            )
        return review_is_grounded(self, review, self.checker_contracts)

    def active_reviews(self) -> list[dict[str, Any]]:
        if self.snapshot is None:
            return []
        criteria = {criterion["id"]: criterion for criterion in self.spec["criteria"]}
        eligible = []
        for review in self.reviews:
            criterion = criteria.get(review.get("criterion"))
            if criterion is None:
                continue
            targets = self.current_targets(criterion)
            if any(self._review_applies(review, criterion, target) for target in targets):
                eligible.append(review)
        replaced = {identity for review in eligible for identity in review["replaces"]}
        return [review for review in eligible if review["id"] not in replaced]

    def issues(self) -> list[dict[str, Any]]:
        reviews = self.active_reviews()
        issues = []
        for criterion in self.spec["criteria"]:
            targets = self.current_targets(criterion)
            if not targets:
                issues.append(
                    {"criterion": criterion, "targets": [], "reviews": [], "reason": "target_missing"}
                )
                continue
            for target in targets:
                group = [
                    review
                    for review in reviews
                    if review["criterion"] == criterion["id"]
                    and canonical(review["target"]) == canonical(target)
                ]
                if not group:
                    issues.append(
                        {
                            "criterion": criterion,
                            "targets": [target],
                            "reviews": [],
                            "reason": "missing_check",
                        }
                    )
                elif any(review["verdict"] != "pass" for review in group):
                    issues.append(
                        {"criterion": criterion, "targets": [target], "reviews": group, "reason": "failed"}
                    )
        return issues

    def unresolved_failures(self) -> list[dict[str, Any]]:
        criteria = {criterion["id"]: criterion for criterion in self.spec["criteria"]}
        replaced = {identity for review in self.reviews for identity in review["replaces"]}
        return [
            {
                **review,
                "criterion_required": criteria[review["criterion"]]["required"],
                "criterion_scope": criteria[review["criterion"]]["scope"],
                "current_targets": self.current_targets(criteria[review["criterion"]]),
            }
            for review in self.reviews
            if review["verdict"] != "pass"
            and review["revision"] == self.revision
            and review["criterion"] in criteria
            and review["id"] not in replaced
        ]

    def role_coverage(self) -> dict[str, int]:
        snapshot = self.snapshot
        if snapshot is None:
            return {}
        roles = sorted(member["role"] for member in snapshot["members"])
        return {role: roles.count(role) for role in set(roles)}

    def missing_roles(self) -> list[str]:
        present = set(self.role_coverage())
        return [role for role in self.spec.get("required_roles", []) if role not in present]

    def missing_governance(self) -> list[str]:
        return [ref for ref in self.spec.get("governance", []) if ref not in self.assets]

    def missing_delivery_members(self) -> list[str]:
        if self.delivery_plan is None or self.snapshot is None:
            return (
                []
                if self.delivery_plan is None
                else [member["path"] for member in self.delivery_plan["members"]]
            )
        by_path = {member["path"]: member for member in self.snapshot["members"]}
        return [
            member["path"]
            for member in self.delivery_plan["members"]
            if member["path"] not in by_path
            or by_path[member["path"]]["role"] != member["role"]
            or by_path[member["path"]]["media_type"] != member["media_type"]
        ]

    def complete(self) -> bool:
        return (
            bool(self.snapshot)
            and not self.spec.get("provisional", False)
            and self.question is None
            and not self.missing_roles()
            and not self.missing_governance()
            and not self.missing_delivery_members()
            and not any(issue["criterion"]["required"] for issue in self.issues())
            and not any(item["criterion_required"] for item in self.unresolved_failures())
            and self.execution_settled()
        )

    def next_action(self) -> str:
        if self.execution_conflicts():
            return "inspect_conflict"
        if self.outcome is not None:
            return "delivered"
        if self.complete():
            return "close"
        if self.question is not None:
            return "wait_for_answer"
        if not self.execution_settled():
            return "resolve_pending"
        if self.spec.get("provisional", False):
            return "refine"
        if self.delivery_plan is not None and self.missing_delivery_members():
            return "prepare_delivery"
        if self.snapshot is None:
            if self.outputs:
                return "publish"
            return "produce" if self.budget_left() else "close_failed"
        if self.missing_roles():
            return "publish" if self.outputs else "produce"
        failures = [failure for failure in self.unresolved_failures() if failure["criterion_required"]]
        if failures:
            if not self.budget_left() and any(
                failure["producer"].startswith("tool:") for failure in failures
            ):
                return "close_partial"
            return "review"
        issues = [issue for issue in self.issues() if issue["criterion"]["required"]]
        if not self.budget_left():
            return (
                "review"
                if all(issue["criterion"]["checker"] == "semantic" for issue in issues)
                else "close_partial"
            )
        return "repair" if any(issue["reviews"] for issue in issues) else "review"

    def execution_conflicts(self) -> list[dict[str, Any]]:
        return [
            {"call": call["id"], "first": call["positive"], "conflicts": call["conflicts"]}
            for call in self.calls.values()
            if call.get("conflicts")
        ]

    def execution_settled(self) -> bool:
        return not self.execution_conflicts() and all(
            call["status"] not in {"pending", "unknown"} or call.get("confirmation")
            for call in self.calls.values()
        )

    def counted_calls(self) -> int:
        return sum(1 for call in self.calls.values() if call.get("counted", True))

    def budget_left(self) -> int:
        return max(0, ResourcePolicy.restore(self.spec["resources"]).work_calls - self.counted_calls())

    def resource_status(self) -> dict[str, Any]:
        policy = ResourcePolicy.restore(self.spec["resources"])
        used = self.counted_calls()
        return {
            **policy.snapshot(),
            "used_calls": used,
            "free_calls": len(self.calls) - used,
            "remaining_calls": self.budget_left(),
            "warning": used >= policy.warning_calls,
            "exhausted": self.budget_left() == 0,
        }


def replay(task: str, events: list[dict[str, Any]]) -> State:
    if not events or events[0]["kind"] != "created":
        raise FairyError("missing", "Unknown task")
    state = State(task, events[0]["payload"]["spec"])
    ResourcePolicy.restore(state.spec.get("resources"))
    for event in events:
        payload = event["payload"]
        kind = event["kind"]
        state.seq = event["seq"]
        if kind == "created":
            state.inputs = payload["inputs"]
        elif kind == "revised":
            if canonical(payload["spec"].get("resources")) != canonical(state.spec["resources"]):
                raise FairyError("integrity", "A task revision cannot replace its fixed resource policy")
            previous = {key: value for key, value in state.spec.items() if key != "provisional"}
            current = {key: value for key, value in payload["spec"].items() if key != "provisional"}
            if canonical(previous) != canonical(current):
                state.revision += 1
            state.spec = payload["spec"]
        elif kind == "invoked":
            state.calls[payload["id"]] = {
                **payload,
                "status": "pending",
                "outputs": [],
                "invoked_seq": event["seq"],
            }
        elif kind == "observed":
            call = state.calls[payload["call"]]
            call.update(payload)
            if call.get("reconciler") and payload["origin"] == "tool" and payload["status"] == "ok":
                _positive(call, payload["result"], payload["call"], event["seq"])
            proof = reconciliation_for(state, payload["call"], payload)
            if proof is not None:
                target = state.calls[call["reconciles"]]
                fact = _positive(target, proof["result"], payload["call"], event["seq"])
                target.setdefault("confirmation", {**fact, "basis": proof["basis"]})
        elif kind == "published":
            normalized = snapshot_value(payload["members"])
            if payload.get("format") != 1 or normalized["ref"] != payload.get("ref"):
                raise FairyError("integrity", "Published snapshot identity does not match its members")
            state.snapshots.append({**payload, "members": normalized["members"], "seq": event["seq"]})
        elif kind == "reviewed":
            state.reviews.append({**payload, "id": event["seq"]})
        elif kind == "asked":
            state.question = payload
            state.question_count += 1
        elif kind == "answered":
            state.question = None
            state.revision += 1
        elif kind == "feedback":
            state.feedback.append({**payload, "seq": event["seq"]})
        elif kind == "asset_used":
            state.assets.append(payload["ref"])
        elif kind == "learning_decision":
            decision = payload.get("decision")
            expected = {"decision", "note", "basis"}
            if decision == "maintain":
                expected.add("learning_task")
            if (
                state.outcome is None
                or decision not in {"maintain", "defer", "no_change"}
                or set(payload) != expected
                or not isinstance(payload.get("note"), str)
                or not isinstance(payload.get("basis"), str)
                or not payload["basis"]
                or (decision == "maintain" and not isinstance(payload["learning_task"], str))
            ):
                raise FairyError("integrity", "Invalid learning decision event")
            state.learning_decisions.append({**payload, "seq": event["seq"]})
        elif kind == "delivery_planned":
            state.delivery_plan = delivery_plan_value(payload)
        elif kind == "delivery_progress":
            if set(payload) != {"member"}:
                raise FairyError("integrity", "Invalid delivery progress event")
            member = member_value(payload["member"])
            state.delivery_progress[member["path"]] = member
        elif kind == "closed":
            state.outcome = payload["outcome"]
        else:
            raise FairyError("integrity", "Unknown task event kind")
    return state


def _positive(call: dict[str, Any], result: Any, source: str, seq: int) -> dict[str, Any]:
    fact = {"source_call": source, "seq": seq, "result_digest": digest(canonical(result))}
    first = call.setdefault("positive", fact)
    if first["result_digest"] != fact["result_digest"]:
        call.setdefault("conflicts", []).append(fact)
    return fact


def reconciliation_for(state: State, identity: str, observation: dict[str, Any]) -> dict[str, Any] | None:
    source = state.calls[identity]
    target_id = source.get("reconciles")
    if target_id is None or observation["origin"] != "tool" or observation["status"] != "ok":
        return None
    target = state.calls[target_id]
    if (
        target["effect"] != "write"
        or source["effect"] != "read"
        or target["invoked_seq"] >= source["invoked_seq"]
        or source["parameters"] != {"call": target_id}
        or target["reconciler"] != {"name": source["capability"], "contract_ref": source["contract_ref"]}
    ):
        raise FairyError("invalid", "Verification does not match its committed authority")
    proof = observation["result"].get("reconciliation")
    if proof is None:
        return None
    proof = object_value(proof)
    if type(proof.get("final")) is not bool:
        raise FairyError("invalid", "Verification must declare boolean finality")
    if not proof["final"]:
        return None
    expected = {"call": target_id, "operation": target["operation"], "contract_ref": target["contract_ref"]}
    if set(proof) != {"target", "final", "result", "basis"} or canonical(proof["target"]) != canonical(
        expected
    ):
        raise FairyError("invalid", "Final confirmation must bind the exact attempt")
    object_value(proof["result"])
    text_value(proof["basis"], "confirmation basis")
    return proof


def admit_call(state: State, effect: str, operation: str, *, counted: bool = True) -> None:
    require_open(state)
    effect_value(effect)
    if effect not in state.spec["effects"]:
        raise FairyError("permission", "Capability effect is outside this task's scope")
    if counted and state.budget_left() == 0:
        raise FairyError("budget", "Invocation budget exhausted; deliver honestly or request help")
    if any(
        call["operation"] == operation
        and (call["status"] in {"pending", "unknown"} or call.get("confirmation") or call.get("conflicts"))
        for call in state.calls.values()
    ):
        raise FairyError("unknown", "Previous execution is unresolved or confirmed; do not repeat it")


def require_open(state: State) -> None:
    if state.outcome is not None:
        raise FairyError("closed", "Task is closed; late observations and feedback remain recordable")


def require_sequence(state: State, expected_seq: int | None) -> None:
    if expected_seq is not None and state.seq != integer(expected_seq, "expected sequence"):
        raise FairyError("conflict", "Task changed; inspect before submitting")


def review_is_grounded(
    state: State, review: dict[str, Any], checker_contracts: dict[str, str] | None = None
) -> bool:
    criterion = next((item for item in state.spec["criteria"] if item["id"] == review.get("criterion")), None)
    if criterion is None or review.get("verdict") not in {"pass", "fail", "unknown"}:
        return False
    if not isinstance(review.get("basis"), str) or not review["basis"].strip():
        return False
    if criterion["checker"] == "semantic":
        return (
            review.get("producer") == "model"
            and review.get("call") is None
            and review.get("checker_contract") is None
        )
    capability = "snapshot.check" if criterion["scope"] == "collection" else "content.check"
    if review.get("producer") != "tool:" + criterion["checker"]:
        return False
    call_id = review.get("call")
    call = state.calls.get(call_id) if isinstance(call_id, str) else None
    if (
        call is None
        or call["capability"] != capability
        or call["status"] != "ok"
        or call["origin"] != "tool"
        or call["revision"] != review.get("revision")
        or review.get("checker_capability") != capability
        or review.get("checker_contract") != call["contract_ref"]
    ):
        return False
    if (
        checker_contracts is not None
        and capability in checker_contracts
        and checker_contracts[capability] != call["contract_ref"]
    ):
        return False
    target = review.get("target")
    if not isinstance(target, dict):
        return False
    if criterion["scope"] == "content":
        expected = {
            "ref": target.get("ref"),
            "checker": criterion["checker"],
            "parameters": criterion["parameters"],
        }
    elif criterion["scope"] == "member":
        member = target.get("member")
        if not isinstance(member, dict):
            return False
        expected = {
            "ref": member.get("ref"),
            "checker": criterion["checker"],
            "parameters": criterion["parameters"],
        }
    else:
        expected = {
            "snapshot": target.get("snapshot"),
            "paths": target.get("paths"),
            "checker": criterion["checker"],
            "parameters": criterion["parameters"],
        }
    if canonical(call["parameters"]) != canonical(expected):
        return False
    result = call["result"]
    return (
        canonical(result.get("checked")) == canonical(expected)
        and result.get("verdict") == review["verdict"]
        and result.get("basis") == review["basis"]
    )


def admit_review(state: State, review: dict[str, Any]) -> None:
    require_open(state)
    if state.snapshot is None:
        raise FairyError("not_ready", "Publish a snapshot before reviewing it")
    if review["revision"] != state.revision:
        raise FairyError("stale", "Review must bind the current task revision")
    criterion = next((item for item in state.spec["criteria"] if item["id"] == review.get("criterion")), None)
    if criterion is None or review.get("verdict") not in {"pass", "fail", "unknown"}:
        raise FairyError("invalid", "Unknown criterion or verdict")
    if review.get("criterion_fingerprint") != criterion_fingerprint(criterion):
        raise FairyError("stale", "Review must bind the current criterion definition")
    targets = state.current_targets(criterion)
    if not any(canonical(target) == canonical(review.get("target")) for target in targets):
        raise FairyError("not_ready", "Criterion target is not present in the current snapshot")
    expected = "model" if criterion["checker"] == "semantic" else "tool:" + criterion["checker"]
    if review.get("producer") != expected:
        raise FairyError("permission", "Review producer does not match the criterion's checker")
    if review["producer"] == "model" and review.get("snapshot") != state.snapshot["ref"]:
        raise FairyError("stale", "Semantic review must bind the current snapshot")
    if not review_is_grounded(state, review, state.checker_contracts):
        raise FairyError("invalid", "Review must match its recorded check invocation and observation")
    replaced = {identity for item in state.reviews for identity in item["replaces"]}
    for identity in review["replaces"]:
        previous = next((item for item in state.reviews if item["id"] == identity), None)
        if (
            previous is None
            or previous["criterion"] != review["criterion"]
            or previous["verdict"] == "pass"
            or identity in replaced
        ):
            raise FairyError("conflict", "Review replacement has no matching unresolved failure")


def admit_question(state: State) -> None:
    require_open(state)
    if state.question is not None:
        raise FairyError("limit", "A question is already pending; forward its answer before asking another")


def admit_close(state: State, outcome: str) -> None:
    require_open(state)
    if outcome not in {"complete", "partial", "failed", "cancelled"}:
        raise FairyError("invalid", "Unknown outcome")
    if outcome == "complete" and not state.complete():
        raise FairyError("not_ready", "Required checks, answers or execution results remain unresolved")
    if outcome == "partial" and not state.snapshot:
        raise FairyError("not_ready", "Partial delivery requires a snapshot")
