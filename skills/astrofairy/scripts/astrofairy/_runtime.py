from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Self

from astrofairy._capabilities import Capability, Context, atomic_write, builtins
from astrofairy._contracts import (
    DEFAULT_CALL_BUDGET,
    MAX_BLOB_BYTES,
    canonical,
    command_value,
    criteria_value,
    digest,
    file_name,
    integer,
    object_value,
    strings,
    text_value,
)
from astrofairy._errors import FairyError
from astrofairy._kernel import (
    State,
    admit_call,
    admit_close,
    admit_question,
    admit_review,
    replay,
    require_open,
)
from astrofairy._library import Library, validation_criteria
from astrofairy._store import Store


class Workshop:
    def __init__(self, home: Path, capabilities: dict[str, Capability] | None = None) -> None:
        self.store = Store(home)
        self.library = Library(self.store)
        self.capabilities = builtins() if capabilities is None else capabilities

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.store.close()

    def state(self, task: str) -> State:
        return replay(task, self.store.events(task))

    def _start(self, spec: dict[str, Any], inputs: list[dict[str, Any]], seed: str | None = None) -> str:
        task = uuid.uuid4().hex
        (self.store.home / "workspaces" / task).mkdir(mode=0o700, parents=True)
        with self.store.transaction():
            self.store.append(task, "created", {"spec": spec, "inputs": inputs, "origin": "host_report"}, 0)
            if seed is not None:
                self.store.get(seed)
                self.store.append(
                    task,
                    "published",
                    {
                        "ref": seed,
                        "name": "asset.json",
                        "media_type": "application/json",
                        "origin": "library",
                    },
                    1,
                )
        return task

    def start(
        self,
        request: str,
        *,
        goal: str | None = None,
        criteria: list[dict[str, Any]] | None = None,
        budget: int = DEFAULT_CALL_BUDGET,
        effects: list[str] | None = None,
        inputs: list[Path] | None = None,
    ) -> str:
        request = text_value(request, "task request")
        default = [
            {
                "id": "goal",
                "description": "Respond to the stated goal with usable content",
                "checker": "semantic",
            },
            {"id": "usable", "description": "Deliver nonempty content", "checker": "nonempty"},
        ]
        spec = {
            "request": request,
            "goal": text_value(goal or request, "goal"),
            "criteria": criteria_value(default if criteria is None else criteria),
            "budget": integer(budget, "invocation budget", 1),
            "effects": strings(["reason", "read", "write"] if effects is None else effects, "effects"),
            "assumptions": [],
        }
        captured = []
        for path in inputs or []:
            with path.open("rb") as stream:
                data = stream.read(MAX_BLOB_BYTES + 1)
            captured.append({"ref": self.store.put(data), "name": path.name})
        return self._start(spec, captured)

    def _append(self, state: State, kind: str, payload: dict[str, Any]) -> None:
        self.store.append(state.task, kind, payload, state.seq)

    def _known_outputs(self, state: State) -> dict[str, dict[str, Any]]:
        return {item["ref"]: item for call in state.calls.values() for item in call["outputs"]}

    def _request(self, state: State, command: dict[str, Any]) -> dict[str, Any]:
        purpose = text_value(command["purpose"], "work purpose")
        refs = strings(command.get("refs", []), "input references")
        for ref in refs:
            Context(self.store, state).content(ref)
        operation = "model:" + digest(canonical({"purpose": purpose, "refs": refs}))
        admit_call(state, "reason", operation)
        identity = uuid.uuid4().hex
        self._append(
            state,
            "invoked",
            {
                "id": identity,
                "capability": "host.model",
                "effect": "reason",
                "purpose": purpose,
                "operation": operation,
                "refs": refs,
                "origin": "runner",
            },
        )
        return {"call": identity, "purpose": purpose, "refs": refs, "return_via": "report"}

    def invoke(
        self,
        task: str,
        capability: str,
        parameters: dict[str, Any],
        expected_seq: int | None = None,
    ) -> dict[str, Any]:
        handler = self.capabilities.get(capability)
        if handler is None:
            raise FairyError("missing", "Capability is not registered")
        if not set(handler.required) <= set(parameters) or set(parameters) - set(handler.required) - set(
            handler.optional
        ):
            raise FairyError("invalid", "Missing or unknown capability parameters")
        operation = capability + ":" + digest(canonical(parameters))
        with self.store.transaction():
            state = self.state(task)
            if expected_seq is not None and state.seq != expected_seq:
                raise FairyError("conflict", "Task changed; inspect before invoking")
            admit_call(state, handler.effect, operation)
            identity = uuid.uuid4().hex
            self._append(
                state,
                "invoked",
                {
                    "id": identity,
                    "capability": capability,
                    "effect": handler.effect,
                    "parameters": parameters,
                    "operation": operation,
                    "origin": "runner",
                },
            )
        try:
            result = object_value(handler.handler(Context(self.store, state), parameters))
            outputs = result.get("outputs", [])
            if not isinstance(outputs, list):
                raise FairyError("invalid", "Capability outputs must be a list")
            for item in outputs:
                self.store.get(object_value(item)["ref"])
            canonical(result)
            observation = {
                "call": identity,
                "status": "ok",
                "outputs": outputs,
                "result": result,
                "origin": "tool",
            }
        except Exception as exc:  # noqa: BLE001 - extension failure must retain the invocation's observed state.
            observation = {
                "call": identity,
                "status": "unknown" if handler.effect == "write" else "failed",
                "outputs": [],
                "result": {"error": exc.code if isinstance(exc, FairyError) else type(exc).__name__},
                "origin": "tool",
            }
        with self.store.transaction():
            current = self.state(task)
            self._append(current, "observed", observation)
            if observation["status"] == "ok" and "asset_ref" in result:
                current = self.state(task)
                self._append(current, "asset_used", {"ref": result["asset_ref"], "origin": "runner"})
        return observation

    def _review(self, state: State, command: dict[str, Any], producer: str = "model") -> None:
        if state.artifact is None:
            raise FairyError("not_ready", "Publish an artifact before reviewing it")
        replaces = command.get("replaces", [])
        if not isinstance(replaces, list):
            raise FairyError("invalid", "Replacement ids must be a list")
        replacements = [integer(item, "review event id", 1) for item in replaces]
        evidence = strings(command.get("evidence", [state.artifact["ref"]]), "review evidence")
        for ref in evidence:
            Context(self.store, state).content(ref)
        review = {
            "criterion": text_value(command["criterion"], "criterion"),
            "verdict": text_value(command["verdict"], "verdict"),
            "basis": text_value(command["basis"], "review basis"),
            "ref": text_value(command.get("ref", state.artifact["ref"]), "reviewed reference"),
            "revision": integer(command.get("revision", state.revision), "task revision", 1),
            "artifact_seq": state.artifact["seq"],
            "producer": producer,
            "replaces": replacements,
            "evidence": evidence,
        }
        admit_review(state, review)
        self._append(state, "reviewed", review)

    def check(self, task: str, criterion: str | None = None) -> dict[str, Any]:
        initial = self.state(task)
        require_open(initial)
        if initial.artifact is None:
            raise FairyError("not_ready", "No artifact to check")
        candidates = [item for item in initial.spec["criteria"] if item["checker"] != "semantic"]
        if criterion is not None:
            candidates = [item for item in candidates if item["id"] == criterion]
            if not candidates:
                raise FairyError("invalid", "No matching mechanical criterion")
        results = []
        for item in candidates:
            observation = self.invoke(
                task,
                "content.check",
                {
                    "checker": item["checker"],
                    "ref": initial.artifact["ref"],
                    "parameters": item["parameters"],
                },
            )
            results.append(observation)
            if observation["status"] != "ok":
                continue
            with self.store.transaction():
                current = self.state(task)
                if (
                    current.artifact is None
                    or current.artifact["seq"] != initial.artifact["seq"]
                    or current.revision != initial.revision
                ):
                    raise FairyError("stale", "Artifact or task changed during the check")
                self._review(
                    current,
                    {
                        "criterion": item["id"],
                        "verdict": observation["result"]["verdict"],
                        "basis": observation["result"]["basis"],
                        "evidence": [initial.artifact["ref"]],
                        "replaces": [
                            review["id"]
                            for review in current.active_reviews()
                            if review["criterion"] == item["id"]
                            and review["producer"] == "tool:" + item["checker"]
                        ],
                    },
                    "tool:" + item["checker"],
                )
        return {"checks": results}

    def submit(self, task: str, value: dict[str, Any]) -> dict[str, Any]:
        command = command_value(value)
        operation = command["op"]
        if operation == "invoke":
            return self.invoke(
                task,
                text_value(command["capability"], "capability"),
                object_value(command["parameters"]),
                command.get("expected_seq"),
            )
        if operation == "check":
            if "expected_seq" in command and self.state(task).seq != command["expected_seq"]:
                raise FairyError("conflict", "Task changed before checking")
            return self.check(task, command.get("criterion"))
        if operation == "learn":
            return {"learning_task": self.learning_task(task)}
        result: dict[str, Any] = {}
        with self.store.transaction():
            state = self.state(task)
            if "expected_seq" in command and command["expected_seq"] != state.seq:
                raise FairyError("conflict", "Task changed; inspect before submitting")
            if operation not in {"report", "feedback"}:
                require_open(state)
            if operation == "request":
                result = self._request(state, command)
            elif operation == "report":
                call = state.calls.get(text_value(command["call"], "call id"))
                if call is None or call["capability"] != "host.model" or call["status"] != "pending":
                    raise FairyError("permission", "A model report needs a pending model request")
                data = text_value(command["text"], "model output", MAX_BLOB_BYTES).encode("utf-8")
                ref = self.store.put(data)
                output = {
                    "ref": ref,
                    "name": file_name(command.get("name", "result.md")),
                    "media_type": text_value(command.get("media_type", "text/markdown"), "media type"),
                }
                self._append(
                    state,
                    "observed",
                    {"call": command["call"], "status": "ok", "outputs": [output], "origin": "model"},
                )
                result = output
            elif operation == "publish":
                ref = text_value(command["ref"], "artifact reference")
                published_output = self._known_outputs(state).get(ref)
                if published_output is None:
                    raise FairyError("permission", "Artifact must be an observed output of this task")
                self.store.get(ref)
                self._append(state, "published", {**published_output, "origin": "runner"})
            elif operation == "review":
                self._review(state, command)
            elif operation == "revise":
                criteria = criteria_value(command["criteria"])
                protected = {
                    item["id"]: item
                    for item in state.spec["criteria"]
                    if item["origin"] in {"user", "policy"}
                }
                proposed = {item["id"]: item for item in criteria}
                if any(
                    proposed.get(key) != item for key, item in protected.items() if item["origin"] == "policy"
                ):
                    raise FairyError("permission", "Task strategy cannot weaken runtime policy criteria")
                if any(proposed.get(key) != item for key, item in protected.items()):
                    basis = command.get("user_basis")
                    events = self.store.events(task)
                    revised_at = max((item["seq"] for item in events if item["kind"] == "revised"), default=0)
                    if not any(
                        item["seq"] == basis and item["kind"] == "answered" and item["seq"] > revised_at
                        for item in events
                    ):
                        raise FairyError(
                            "permission",
                            "Changing explicit requirements needs a new forwarded user instruction",
                        )
                spec = {
                    **state.spec,
                    "goal": text_value(command["goal"], "goal"),
                    "criteria": criteria,
                    "assumptions": strings(command.get("assumptions", []), "assumptions"),
                }
                self._append(
                    state,
                    "revised",
                    {
                        "spec": spec,
                        "reason": text_value(command["reason"], "revision reason"),
                        "user_basis": command.get("user_basis"),
                        "origin": "model",
                    },
                )
            elif operation == "ask":
                admit_question(state)
                self._append(
                    state,
                    "asked",
                    {
                        "question": text_value(command["question"], "question"),
                        "recommendation": text_value(command["recommendation"], "recommendation"),
                        "options": strings(command.get("options", []), "question options"),
                        "origin": "model",
                    },
                )
            elif operation == "answer":
                self._append(
                    state,
                    "answered",
                    {"text": text_value(command["text"], "forwarded user answer"), "origin": "user_report"},
                )
            elif operation == "feedback":
                self._append(
                    state,
                    "feedback",
                    {
                        "text": text_value(command["text"], "feedback"),
                        "kind": text_value(command.get("kind", "observation"), "feedback kind"),
                        "origin": "user_report",
                    },
                )
            elif operation == "close":
                outcome = text_value(command["outcome"], "outcome")
                admit_close(state, outcome)
                self._append(
                    state, "closed", {"outcome": outcome, "note": command.get("note", ""), "origin": "runner"}
                )
        if operation == "close":
            return self.deliver(task)
        if operation in {"report", "feedback"} and self.state(task).outcome is not None:
            result["receipt_path"] = self.deliver(task)["receipt_path"]
        return {**result, "task": task, "seq": self.state(task).seq}

    def next(self, task: str) -> dict[str, Any]:
        state = self.state(task)
        if state.outcome is not None:
            action = "delivered"
        elif state.complete():
            action = "close"
        elif state.budget_left() == 0:
            action = "close_partial" if state.artifact else "close_failed"
        elif state.question is not None:
            action = "wait_for_answer"
        elif any(call["status"] in {"pending", "unknown"} for call in state.calls.values()):
            action = "resolve_pending"
        elif state.artifact is None:
            action = "produce"
        else:
            action = "repair" if any(issue["reviews"] for issue in state.issues()) else "review"
        return {
            "task": task,
            "seq": state.seq,
            "revision": state.revision,
            "action": action,
            "goal": state.spec["goal"],
            "criteria": state.spec["criteria"],
            "assumptions": state.spec["assumptions"],
            "effects": state.spec["effects"],
            "budget_left": state.budget_left(),
            "inputs": state.inputs,
            "artifact": state.artifact,
            "issues": state.issues(),
            "question": state.question,
            "pending": [call for call in state.calls.values() if call["status"] in {"pending", "unknown"}],
            "user_updates": [event for event in self.store.events(task) if event["kind"] == "answered"],
            "capabilities": self.catalog()["matches"],
            "capability_count": len(self.capabilities),
            "discover_capabilities_via": "capabilities --query TEXT",
            "workspace": str(self.store.home / "workspaces" / task),
        }

    def catalog(self, query: str = "", limit: int = 8) -> dict[str, Any]:
        if not 1 <= limit <= 20:
            raise FairyError("limit", "Capability lookup limit must be between 1 and 20")
        names = [name for name in sorted(self.capabilities) if query.casefold() in name.casefold()]
        return {
            "matches": [
                {
                    "name": name,
                    "effect": self.capabilities[name].effect,
                    "required": list(self.capabilities[name].required),
                    "optional": list(self.capabilities[name].optional),
                }
                for name in names[:limit]
            ],
            "total": len(names),
        }

    def inspect(self, task: str, *, history: bool = False) -> dict[str, Any]:
        state = self.state(task)
        result = {
            "task": task,
            "seq": state.seq,
            "revision": state.revision,
            "spec": state.spec,
            "outcome": state.outcome,
            "inputs": state.inputs,
            "artifacts": state.artifacts,
            "reviews": state.reviews,
            "issues": state.issues(),
            "feedback": state.feedback,
            "assets": state.assets,
            "calls": list(state.calls.values()),
        }
        if history:
            result["events"] = self.store.events(task)
        return result

    def deliver(self, task: str) -> dict[str, Any]:
        state = self.state(task)
        if state.outcome is None:
            raise FairyError("not_ready", "Close the task before exporting delivery")
        root = self.store.home / "deliveries" / task
        result = self.inspect(task)
        if state.artifact:
            name = Path(state.artifact["name"]).name
            if name in {"", ".", "..", "receipt.json"}:
                name = "artifact.bin"
            path = root / name
            atomic_write(path, self.store.get(state.artifact["ref"]))
            result["artifact_path"] = str(path)
        receipt = root / "receipt.json"
        atomic_write(receipt, canonical(result))
        return {
            "task": task,
            "seq": state.seq,
            "outcome": state.outcome,
            "artifact_path": result.get("artifact_path"),
            "receipt_path": str(receipt),
        }

    def validation_task(self, ref: str) -> str:
        package = self.library.get(ref)
        spec = {
            "request": "Validate a reusable workshop asset",
            "goal": "Check applicability, usefulness and dependencies of " + package["name"],
            "criteria": validation_criteria(),
            "budget": DEFAULT_CALL_BUDGET,
            "effects": ["read", "reason"],
            "assumptions": [],
        }
        return self._start(spec, [{"ref": ref, "name": "candidate.json"}], seed=ref)

    def learning_task(self, task: str) -> str:
        source = self.state(task)
        if source.outcome is None:
            raise FairyError("not_ready", "Learning maintenance starts after delivery")
        summary = self.inspect(task)
        ref = self.store.put(canonical(summary))
        spec = {
            "request": "Learn from actual task performance",
            "goal": (
                "Extract useful successes, failures, feedback and reusable patterns; "
                "prefer revising existing assets and allow no change"
            ),
            "criteria": criteria_value(
                [
                    {
                        "id": "grounded",
                        "description": (
                            "Every proposed improvement has observed evidence, applicability "
                            "and a concrete destination; no change is acceptable"
                        ),
                        "checker": "semantic",
                    },
                    {"id": "usable", "description": "Maintenance result is nonempty", "checker": "nonempty"},
                ]
            ),
            "budget": DEFAULT_CALL_BUDGET,
            "effects": ["read", "reason"],
            "assumptions": [],
        }
        return self._start(spec, [{"ref": ref, "name": "performance.json"}])
