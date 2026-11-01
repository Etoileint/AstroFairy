from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from astrofairy._contracts import (
    MAX_QUESTIONS,
    canonical,
    digest,
    effect_value,
    integer,
    object_value,
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
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    reviews: list[dict[str, Any]] = field(default_factory=list)
    inputs: list[dict[str, Any]] = field(default_factory=list)
    feedback: list[dict[str, Any]] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    question: dict[str, Any] | None = None
    question_count: int = 0
    outcome: str | None = None

    @property
    def artifact(self) -> dict[str, Any] | None:
        return self.artifacts[-1] if self.artifacts else None

    @property
    def outputs(self) -> dict[str, dict[str, Any]]:
        return {item["ref"]: item for call in self.calls.values() for item in call["outputs"]}

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
        if self.artifact is None:
            if self.outputs:
                return "publish"
            return "produce" if self.budget_left() else "close_failed"
        issues = [issue for issue in self.issues() if issue["criterion"]["required"]]
        if not self.budget_left():
            return (
                "review"
                if all(issue["criterion"]["checker"] == "semantic" for issue in issues)
                else "close_partial"
            )
        return "repair" if any(issue["reviews"] for issue in issues) else "review"

    def active_reviews(self) -> list[dict[str, Any]]:
        if not self.artifact:
            return []
        eligible = [
            review
            for review in self.reviews
            if review["revision"] == self.revision
            and review["ref"] == self.artifact["ref"]
            and review_is_grounded(self, review)
        ]
        replaced = {identity for review in eligible for identity in review["replaces"]}
        return [review for review in eligible if review["id"] not in replaced]

    def issues(self) -> list[dict[str, Any]]:
        reviews = self.active_reviews()
        issues = []
        for criterion in self.spec["criteria"]:
            group = [review for review in reviews if review["criterion"] == criterion["id"]]
            if not group or any(review["verdict"] != "pass" for review in group):
                issues.append({"criterion": criterion, "reviews": group})
        return issues

    def complete(self) -> bool:
        return (
            bool(self.artifact)
            and self.question is None
            and not any(issue["criterion"]["required"] for issue in self.issues())
            and self.execution_settled()
        )

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

    def budget_left(self) -> int:
        return max(0, integer(self.spec["budget"], "invocation budget", 1) - len(self.calls))


def replay(task: str, events: list[dict[str, Any]]) -> State:
    if not events or events[0]["kind"] != "created":
        raise FairyError("missing", "Unknown task")
    state = State(task, events[0]["payload"]["spec"])
    for event in events:
        payload = event["payload"]
        kind = event["kind"]
        state.seq = event["seq"]
        if kind == "created":
            state.inputs = payload["inputs"]
        elif kind == "revised":
            if canonical(state.spec) != canonical(payload["spec"]):
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
            state.artifacts.append({**payload, "seq": event["seq"]})
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
        elif kind == "closed":
            state.outcome = payload["outcome"]
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


def admit_call(state: State, effect: str, operation: str) -> None:
    require_open(state)
    effect_value(effect)
    if effect not in state.spec["effects"]:
        raise FairyError("permission", "Capability effect is outside this task's scope")
    if state.budget_left() == 0:
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


def review_is_grounded(state: State, review: dict[str, Any]) -> bool:
    criterion = next((item for item in state.spec["criteria"] if item["id"] == review["criterion"]), None)
    if criterion is None or review["verdict"] not in {"pass", "fail", "unknown"}:
        return False
    if not isinstance(review["basis"], str) or not review["basis"].strip():
        return False
    if criterion["checker"] == "semantic":
        return review["producer"] == "model" and review["call"] is None
    call = state.calls.get(review["call"])
    expected = {"ref": review["ref"], "checker": criterion["checker"], "parameters": criterion["parameters"]}
    if (
        review["producer"] != "tool:" + criterion["checker"]
        or call is None
        or call["capability"] != "content.check"
        or call["status"] != "ok"
        or call["origin"] != "tool"
        or call["revision"] != review["revision"]
        or canonical(call["parameters"]) != canonical(expected)
    ):
        return False
    result = call["result"]
    return (
        canonical(result.get("checked")) == canonical(expected)
        and result.get("verdict") == review["verdict"]
        and result.get("basis") == review["basis"]
    )


def admit_review(state: State, review: dict[str, Any]) -> None:
    require_open(state)
    if not state.artifact or review["ref"] != state.artifact["ref"]:
        raise FairyError("stale", "Review must bind the current artifact")
    if review["revision"] != state.revision:
        raise FairyError("stale", "Review must bind the current task revision")
    criterion = next((item for item in state.spec["criteria"] if item["id"] == review["criterion"]), None)
    if criterion is None or review["verdict"] not in {"pass", "fail", "unknown"}:
        raise FairyError("invalid", "Unknown criterion or verdict")
    expected = "model" if criterion["checker"] == "semantic" else "tool:" + criterion["checker"]
    if review["producer"] != expected:
        raise FairyError("permission", "Review producer does not match the criterion's checker")
    if not review_is_grounded(state, review):
        raise FairyError("invalid", "Review must match its recorded check invocation and observation")
    active = {item["id"]: item for item in state.active_reviews()}
    for identity in review["replaces"]:
        previous = active.get(identity)
        if (
            previous is None
            or previous["criterion"] != review["criterion"]
            or previous["producer"] != expected
        ):
            raise FairyError("conflict", "Review replacement has no matching active predecessor")


def admit_question(state: State) -> None:
    require_open(state)
    if state.question is not None or state.question_count >= MAX_QUESTIONS:
        raise FairyError("limit", "Question budget reached or a question is already pending")


def admit_close(state: State, outcome: str) -> None:
    require_open(state)
    if outcome not in {"complete", "partial", "failed", "cancelled"}:
        raise FairyError("invalid", "Unknown outcome")
    if outcome == "complete" and not state.complete():
        raise FairyError("not_ready", "Required checks, answers or execution results remain unresolved")
    if outcome == "partial" and not state.artifact:
        raise FairyError("not_ready", "Partial delivery requires an artifact")
