from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from astrofairy._contracts import MAX_QUESTIONS, integer
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

    def active_reviews(self) -> list[dict[str, Any]]:
        replaced = {identity for review in self.reviews for identity in review["replaces"]}
        if not self.artifact:
            return []
        return [
            review
            for review in self.reviews
            if review["id"] not in replaced
            and review["revision"] == self.revision
            and review["artifact_seq"] == self.artifact["seq"]
        ]

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
            and not any(call["status"] in {"pending", "unknown"} for call in self.calls.values())
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
            state.spec = payload["spec"]
            state.revision += 1
        elif kind == "invoked":
            state.calls[payload["id"]] = {**payload, "status": "pending", "outputs": []}
        elif kind == "observed":
            state.calls[payload["call"]].update(payload)
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


def admit_call(state: State, effect: str, operation: str) -> None:
    require_open(state)
    if effect not in state.spec["effects"]:
        raise FairyError("permission", "Capability effect is outside this task's scope")
    if state.budget_left() == 0:
        raise FairyError("budget", "Invocation budget exhausted; deliver honestly or request help")
    if any(
        call["operation"] == operation and call["status"] in {"pending", "unknown"}
        for call in state.calls.values()
    ):
        raise FairyError("unknown", "Previous execution is unresolved; do not retry blindly")


def require_open(state: State) -> None:
    if state.outcome is not None:
        raise FairyError("closed", "Task is closed; late observations and feedback remain recordable")


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
