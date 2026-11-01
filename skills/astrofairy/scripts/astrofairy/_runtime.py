from __future__ import annotations

import uuid
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from astrofairy._capabilities import Capability, Context, atomic_write, builtins, validate_confirmation
from astrofairy._contracts import (
    CAPABILITY_NAME,
    DEFAULT_CALL_BUDGET,
    MAX_BLOB_BYTES,
    MODEL_CAPABILITY,
    canonical,
    command_value,
    criteria_value,
    digest,
    file_name,
    integer,
    object_value,
    parse_json,
    strings,
    task_spec_value,
    text_value,
)
from astrofairy._documents import freeze
from astrofairy._errors import FairyError
from astrofairy._kernel import (
    State,
    admit_call,
    admit_close,
    admit_question,
    admit_review,
    reconciliation_for,
    replay,
    require_open,
    require_sequence,
)
from astrofairy._library import Library, validation_criteria
from astrofairy._store import Store

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping


class Workshop(AbstractContextManager["Workshop"]):
    def __init__(self, home: Path, capabilities: dict[str, Capability] | None = None) -> None:
        self._capabilities: dict[str, Capability] = {}
        for name, capability in (builtins() if capabilities is None else capabilities).items():
            self.register(name, capability)
        self.store = Store(home)
        self.library = Library(self.store)

    @property
    def capabilities(self) -> Mapping[str, Capability]:
        return MappingProxyType(self._capabilities)

    def register(self, name: str, capability: Capability, *, replace: bool = False) -> None:
        if (
            not isinstance(name, str)
            or not CAPABILITY_NAME.fullmatch(name)
            or name == MODEL_CAPABILITY
            or not isinstance(capability, Capability)
        ):
            raise FairyError("invalid_contract", "Invalid capability name or definition")
        if name in self._capabilities and not replace:
            raise FairyError("conflict", "Capability already registered; replacement must be explicit")
        capability.definition(name)
        self._capabilities[name] = capability

    def describe(self, name: str) -> dict[str, Any]:
        capability = self._capabilities.get(name)
        if capability is None:
            raise FairyError("missing", "Capability is not registered")
        definition = capability.definition(name)
        return {**definition, "contract_ref": digest(canonical(definition))}

    def __exit__(self, *_: object) -> None:
        self.store.close()

    def state(self, task: str) -> State:
        return replay(task, self.store.events(task))

    @contextmanager
    def _admitted(self, task: str, expected_seq: int | None = None) -> Iterator[State]:
        with self.store.transaction():
            state = self.state(task)
            require_sequence(state, expected_seq)
            yield state

    def _start(self, spec: dict[str, Any], inputs: list[dict[str, Any]], seed: str | None = None) -> str:
        if not self.store.connection.in_transaction:
            raise FairyError("invalid", "Task creation requires an admitted transaction")
        task = uuid.uuid4().hex
        (self.store.home / "workspaces" / task).mkdir(mode=0o700, parents=True)
        self.store.append(task, "created", {"spec": spec, "inputs": inputs, "origin": "host_report"}, 0)
        if seed is not None:
            self.store.get(seed)
            self.store.append(
                task,
                "published",
                {"ref": seed, "name": "asset.json", "media_type": "application/json", "origin": "library"},
                1,
            )
        return task

    def start(
        self,
        request: str,
        *,
        spec: dict[str, Any] | None = None,
        budget: int = DEFAULT_CALL_BUDGET,
        effects: list[str] | None = None,
        inputs: list[Path] | None = None,
    ) -> str:
        normalized = task_spec_value(request, spec, budget, effects)
        with self.store.transaction():
            captured = []
            for path in inputs or []:
                with path.open("rb") as stream:
                    data = stream.read(MAX_BLOB_BYTES + 1)
                captured.append({"ref": self.store.put(data), "name": path.name})
            return self._start(normalized, captured)

    def _append(self, state: State, kind: str, payload: dict[str, Any]) -> None:
        self.store.append(state.task, kind, payload, state.seq)

    def _request(self, state: State, command: dict[str, Any]) -> dict[str, Any]:
        purpose = text_value(command["purpose"], "work purpose")
        refs = strings(command.get("refs", []), "input references")
        for ref in refs:
            Context(self.store, state).content(ref)
        operation = MODEL_CAPABILITY + ":" + digest(canonical({"purpose": purpose, "refs": refs}))
        admit_call(state, "reason", operation)
        identity = uuid.uuid4().hex
        self._append(
            state,
            "invoked",
            {
                "id": identity,
                "capability": MODEL_CAPABILITY,
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
        parameters = object_value(parse_json(canonical(parameters).decode("utf-8")))
        handler.validate_input(parameters)
        definition = handler.definition(capability)
        encoded = canonical(parameters)
        operation = capability + ":" + digest(encoded)
        identity = uuid.uuid4().hex
        verifier_definition = None
        if handler.reconciler is not None:
            verifier = self.capabilities.get(handler.reconciler)
            if verifier is None or verifier.effect != "read":
                raise FairyError("invalid_contract", "Reconciler must be a registered read capability")
            verifier.validate_input({"call": identity})
            verifier_definition = verifier.definition(handler.reconciler)
        with self._admitted(task, expected_seq) as state:
            admit_call(state, handler.effect, operation)
            reconciles: str | None = None
            if any((call.get("reconciler") or {}).get("name") == capability for call in state.calls.values()):
                target_id = parameters.get("call")
                target = state.calls.get(target_id) if isinstance(target_id, str) else None
                if (
                    set(parameters) != {"call"}
                    or target is None
                    or handler.effect != "read"
                    or target.get("reconciler")
                    != {"name": capability, "contract_ref": digest(canonical(definition))}
                ):
                    raise FairyError(
                        "permission", "Reconciler must match the exact pinned target and contract"
                    )
                reconciles = target_id
            if handler.prepare is not None:
                try:
                    handler.prepare(Context(self.store, state), parameters)
                except FairyError:
                    raise
                except Exception as exc:
                    raise FairyError(
                        "preflight_failed", "Tool preflight failed; inspect its definition before retrying"
                    ) from exc
                if canonical(parameters) != encoded:
                    raise FairyError("invalid_contract", "Preflight must not mutate input parameters")
            contract_ref = self.store.put(canonical(definition))
            reconciler = (
                None
                if verifier_definition is None
                else {
                    "name": handler.reconciler,
                    "contract_ref": self.store.put(canonical(verifier_definition)),
                }
            )
            self._append(
                state,
                "invoked",
                {
                    "id": identity,
                    "capability": capability,
                    "effect": handler.effect,
                    "revision": state.revision,
                    "parameters": parameters,
                    "contract_ref": contract_ref,
                    "reconciler": reconciler,
                    "reconciles": reconciles,
                    "operation": operation,
                    "origin": "runner",
                },
            )
        try:
            result = object_value(handler.handler(Context(self.store, state, identity), parameters))
            handler.validate_result(result)
            outputs = result["outputs"]
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
            if reconciles is not None:
                captured = self.state(task)
                proof = reconciliation_for(captured, identity, observation)
                if proof is not None:
                    target = captured.calls[proof["target"]["call"]]
                    declared = object_value(
                        parse_json(self.store.get(target["contract_ref"]).decode("utf-8"))
                    )
                    validate_confirmation(proof, result, declared)
                    for item in proof["result"]["outputs"]:
                        self.store.get(item["ref"])
        except Exception as exc:  # noqa: BLE001 - extension failure must retain the invocation's observed state.
            observation = {
                "call": identity,
                "status": "unknown" if handler.effect == "write" else "failed",
                "outputs": [],
                "result": exc.as_dict()
                if isinstance(exc, FairyError)
                else {
                    "error": "tool_failed",
                    "message": "Tool execution failed; inspect the recorded call before retrying",
                },
                "origin": "tool",
            }
        with self.store.transaction():
            current = self.state(task)
            self._append(current, "observed", observation)
            if observation["status"] == "ok" and "asset_ref" in result:
                current = self.state(task)
                self._append(current, "asset_used", {"ref": result["asset_ref"], "origin": "runner"})
        if current.outcome is not None:
            observation["receipt_path"] = self.deliver(task)["receipt_path"]
        return observation

    def _review(
        self, state: State, command: dict[str, Any], producer: str = "model", call: str | None = None
    ) -> None:
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
            "call": call,
            "replaces": replacements,
            "evidence": evidence,
        }
        admit_review(state, review)
        self._append(state, "reviewed", review)

    def check(
        self, task: str, criterion: str | None = None, expected_seq: int | None = None
    ) -> dict[str, Any]:
        with self._admitted(task, expected_seq) as initial:
            require_open(initial)
            if initial.artifact is None:
                raise FairyError("not_ready", "No artifact to check")
            candidates = [item for item in initial.spec["criteria"] if item["checker"] != "semantic"]
            if criterion is not None:
                candidates = [item for item in candidates if item["id"] == criterion]
                if not candidates:
                    raise FairyError("invalid", "No matching mechanical criterion")
            cursor = initial.seq
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
                expected_seq=cursor,
            )
            results.append(observation)
            with self._admitted(task) as current:
                require_open(current)
                if (
                    current.artifact is None
                    or current.artifact["seq"] != initial.artifact["seq"]
                    or current.revision != initial.revision
                ):
                    raise FairyError("stale", "Artifact or task changed during the check")
                cursor = current.seq
                if observation["status"] != "ok":
                    continue
                self._review(
                    current,
                    {
                        "criterion": item["id"],
                        "verdict": observation["result"].get("verdict"),
                        "basis": observation["result"].get("basis"),
                        "evidence": [initial.artifact["ref"]],
                        "replaces": [
                            review["id"]
                            for review in current.active_reviews()
                            if review["criterion"] == item["id"]
                            and review["producer"] == "tool:" + item["checker"]
                        ],
                    },
                    "tool:" + item["checker"],
                    observation["call"],
                )
                cursor += 1
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
            return self.check(task, command.get("criterion"), command.get("expected_seq"))
        if operation == "learn":
            return {"learning_task": self.learning_task(task, command.get("expected_seq"))}
        result: dict[str, Any] = {}
        with self._admitted(task, command.get("expected_seq")) as state:
            if operation not in {"report", "feedback"}:
                require_open(state)
            if operation == "request":
                result = self._request(state, command)
            elif operation == "report":
                call = state.calls.get(text_value(command["call"], "call id"))
                if call is None or call["capability"] != MODEL_CAPABILITY or call["status"] != "pending":
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
                published_output = state.outputs.get(ref)
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
        if operation in {"report", "feedback"} and state.outcome is not None:
            result["receipt_path"] = self.deliver(task)["receipt_path"]
        return {**result, "task": task, "seq": state.seq + 1}

    def next(self, task: str) -> dict[str, Any]:
        events = self.store.events(task)
        state = replay(task, events)
        return {
            "task": task,
            "seq": state.seq,
            "revision": state.revision,
            "action": state.next_action(),
            "goal": state.spec["goal"],
            "criteria": state.spec["criteria"],
            "assumptions": state.spec["assumptions"],
            "effects": state.spec["effects"],
            "budget_left": state.budget_left(),
            "execution_settled": state.execution_settled(),
            "execution_conflicts": state.execution_conflicts(),
            "inputs": state.inputs,
            "artifact": state.artifact,
            "publish_candidate": next(reversed(state.outputs.values()), None),
            "issues": state.issues(),
            "question": state.question,
            "pending": [
                call
                for call in state.calls.values()
                if (call["status"] in {"pending", "unknown"} and not call.get("confirmation"))
                or call.get("conflicts")
            ],
            "user_updates": [event for event in events if event["kind"] == "answered"],
            "capabilities": self.catalog()["matches"],
            "capability_count": len(self.capabilities),
            "discover_capabilities_via": "capabilities --query TEXT",
            "inspect_capability_via": "capabilities --name NAME",
            "workspace": str(self.store.home / "workspaces" / task),
        }

    def catalog(self, query: str = "", limit: int = 8) -> dict[str, Any]:
        if not 1 <= limit <= 20:
            raise FairyError("limit", "Capability lookup limit must be between 1 and 20")
        names = [name for name in sorted(self.capabilities) if query.casefold() in name.casefold()]
        return {
            "matches": [
                {
                    key: value
                    for key, value in self.describe(name).items()
                    if key in {"name", "effect", "description", "contract_ref"}
                }
                for name in names[:limit]
            ],
            "total": len(names),
        }

    def inspect(self, task: str, *, history: bool = False) -> dict[str, Any]:
        events = self.store.events(task)
        result = self._inspection(replay(task, events))
        if history:
            result["events"] = events
        return result

    def _inspection(self, state: State) -> dict[str, Any]:
        return {
            "task": state.task,
            "seq": state.seq,
            "revision": state.revision,
            "spec": state.spec,
            "outcome": state.outcome,
            "execution_settled": state.execution_settled(),
            "execution_conflicts": state.execution_conflicts(),
            "inputs": state.inputs,
            "artifacts": state.artifacts,
            "reviews": state.reviews,
            "issues": state.issues(),
            "feedback": state.feedback,
            "assets": state.assets,
            "calls": list(state.calls.values()),
        }

    def inspect_contract(self, task: str, ref: str) -> dict[str, Any]:
        state = self.state(task)
        if not any(
            call["capability"] != MODEL_CAPABILITY
            and (call["contract_ref"] == ref or (call.get("reconciler") or {}).get("contract_ref") == ref)
            for call in state.calls.values()
        ):
            raise FairyError("permission", "Definition is not recorded for this task")
        definition = object_value(parse_json(self.store.get(ref).decode("utf-8")))
        return {"task": task, "seq": state.seq, "contract_ref": ref, "definition": definition}

    def deliver(self, task: str) -> dict[str, Any]:
        with self.store.transaction():
            return self._delivery(task)

    def _delivery(self, task: str) -> dict[str, Any]:
        state = self.state(task)
        if state.outcome is None:
            raise FairyError("not_ready", "Close the task before exporting delivery")
        root = self.store.home / "deliveries" / task
        result = self._inspection(state)
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
            "execution_settled": state.execution_settled(),
            "execution_conflicts": state.execution_conflicts(),
            "artifact_path": result.get("artifact_path"),
            "receipt_path": str(receipt),
        }

    def validation_task(self, ref: str) -> str:
        with self.store.transaction():
            package = self.library.get(ref)
            spec = task_spec_value(
                "Validate a reusable workshop asset",
                {
                    "goal": "Check applicability, usefulness and dependencies of " + package["name"],
                    "criteria": validation_criteria(),
                },
                effects=["read", "reason"],
            )
            return self._start(spec, [{"ref": ref, "name": "candidate.json"}], seed=ref)

    def learning_task(self, task: str, expected_seq: int | None = None) -> str:
        with self._admitted(task, expected_seq) as source:
            if source.outcome is None:
                raise FairyError("not_ready", "Learning maintenance starts after delivery")
            summary = freeze(self.store.home, self.inspect(task, history=True), task=task)
            ref = self.store.put(canonical(summary))
            spec = task_spec_value(
                "Learn from actual task performance",
                {
                    "goal": (
                        "Extract useful successes, failures, feedback and reusable patterns; "
                        "prefer revising existing assets and allow no change"
                    ),
                    "criteria": [
                        {
                            "id": "grounded",
                            "description": (
                                "Every proposed improvement has observed evidence, applicability "
                                "and a concrete destination; no change is acceptable"
                            ),
                            "checker": "semantic",
                        },
                        {
                            "id": "usable",
                            "description": "Maintenance result is nonempty",
                            "checker": "nonempty",
                        },
                    ],
                },
                effects=["read", "reason"],
            )
            return self._start(spec, [{"ref": ref, "name": "performance.json", "source_document": summary}])
