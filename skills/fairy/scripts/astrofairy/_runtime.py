from __future__ import annotations

import mimetypes
import uuid
from contextlib import AbstractContextManager, contextmanager
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from astrofairy._capabilities import Capability, Context, builtins, validate_confirmation
from astrofairy._contracts import (
    CAPABILITY_NAME,
    MODEL_CAPABILITY,
    ResourcePolicy,
    canonical,
    command_value,
    content_ref,
    criteria_value,
    criterion_fingerprint,
    delivery_plan_value,
    digest,
    integer,
    member_value,
    members_value,
    object_value,
    output_value,
    parse_json,
    relative_path,
    required_roles_value,
    snapshot_value,
    strings,
    task_spec_value,
    text_value,
)
from astrofairy._delivery import deliver as deliver_bag
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
from astrofairy._limits import LIMITS
from astrofairy._pagination import encode_cursor, offset_cursor
from astrofairy._store import Store

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from pathlib import Path


class Workshop(AbstractContextManager["Workshop"]):
    def __init__(
        self,
        home: Path,
        capabilities: dict[str, Capability] | None = None,
        search: Any | None = None,
    ) -> None:
        self._capabilities: dict[str, Capability] = {}
        for name, capability in (builtins() if capabilities is None else capabilities).items():
            self.register(name, capability)
        self.store = Store(home)
        self.library = Library(self.store, search)

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

    def _checker_contracts(self) -> dict[str, str]:
        return {
            name: digest(canonical(self._capabilities[name].definition(name)))
            for name in ("content.check", "snapshot.check")
            if name in self._capabilities
        }

    def state(self, task: str) -> State:
        state = replay(task, self.store.events(task))
        state.checker_contracts = self._checker_contracts()
        return state

    def todos(self) -> list[dict[str, Any]]:
        rows = self.store.connection.execute("SELECT DISTINCT task FROM events ORDER BY task").fetchall()
        result = []
        for row in rows:
            state = self.state(str(row[0]))
            if state.learning_decisions and state.learning_decisions[-1]["decision"] == "defer":
                item = state.learning_decisions[-1]
                result.append(
                    {
                        "task": state.task,
                        "seq": item["seq"],
                        "decision": item["decision"],
                        "note": item.get("note", ""),
                        "basis": item.get("basis", ""),
                    }
                )
        return result

    def governance(self, scope: str | None = None) -> dict[str, Any]:
        return {"scope": scope, "assets": self.library.governance(scope)}

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
            data = self.store.get(seed)
            member = member_value(
                {
                    "ref": seed,
                    "path": "candidate.json",
                    "bytes": len(data),
                    "media_type": "application/json",
                    "role": "candidate",
                }
            )
            snapshot = snapshot_value([member])
            self.store.put(canonical({"format": 1, "members": snapshot["members"]}))
            self.store.append(
                task,
                "published",
                {
                    "format": 1,
                    "ref": snapshot["ref"],
                    "members": snapshot["members"],
                    "origin": "library",
                },
                1,
            )
        return task

    def start(
        self,
        request: str,
        *,
        spec: dict[str, Any] | None = None,
        resources: ResourcePolicy | None = None,
        effects: list[str] | None = None,
        inputs: list[Path] | None = None,
    ) -> str:
        normalized = task_spec_value(request, spec, resources, effects)
        scoped_governance = {
            item["ref"]
            for scope in normalized.get("governance_scope", [])
            for item in self.library.governance(scope)
        }
        if scoped_governance:
            normalized["governance"] = sorted(set(normalized.get("governance", [])) | scoped_governance)
        for ref in normalized.get("governance", []):
            if self.library.status(ref) not in {"trial", "stable"}:
                raise FairyError("not_ready", "Governance assets must be adopted before task creation")
        with self.store.transaction():
            captured = []
            total = 0
            for path in inputs or []:
                ref, size = self.store.put_file(path, limit=LIMITS.content_bytes)
                total += size
                if total > LIMITS.task_capture_bytes:
                    raise FairyError("limit", "Task capture exceeds its aggregate byte budget")
                captured.append(
                    {
                        "ref": ref,
                        "name": path.name,
                        "path": relative_path(path.name, "input path"),
                        "bytes": size,
                        "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                    }
                )
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
            admit_call(state, handler.effect, operation, counted=handler.counted)
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
                    "counted": handler.counted,
                    "origin": "runner",
                },
            )
        try:
            result = object_value(
                handler.handler(Context(self.store, state, identity, self.library.search_index), parameters)
            )
            handler.validate_result(result)
            outputs = []
            for item in result["outputs"]:
                descriptor = output_value(item)
                outputs.append({**descriptor, "bytes": self.store.length(descriptor["ref"])})
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

    def _review_target(self, state: State, criterion: dict[str, Any], selector: Any) -> dict[str, Any]:
        targets = state.current_targets(criterion)
        if not targets:
            raise FairyError("not_ready", "Criterion target is not present in the current snapshot")
        if selector is None:
            if len(targets) == 1:
                return targets[0]
            raise FairyError("invalid", "Criterion has multiple targets; specify the exact target")
        if not isinstance(selector, str):
            raise FairyError("invalid", "Review target must be a stable identifier")
        if criterion["scope"] == "content":
            matches = [target for target in targets if target["ref"] == selector]
        elif criterion["scope"] == "member":
            matches = [target for target in targets if target["member"]["path"] == selector]
        else:
            matches = [target for target in targets if target["snapshot"] == selector]
        if len(matches) != 1:
            raise FairyError("invalid", "Review target does not match one current criterion target")
        return matches[0]

    def _review(
        self,
        state: State,
        command: dict[str, Any],
        *,
        producer: str = "model",
        call: str | None = None,
        target: dict[str, Any] | None = None,
        checker_capability: str | None = None,
    ) -> None:
        if state.snapshot is None:
            raise FairyError("not_ready", "Publish a snapshot before reviewing it")
        criterion_id = text_value(command["criterion"], "criterion")
        criterion = next((item for item in state.spec["criteria"] if item["id"] == criterion_id), None)
        if criterion is None:
            raise FairyError("invalid", "Unknown criterion")
        selected = (
            target if target is not None else self._review_target(state, criterion, command.get("target"))
        )
        replaces = command.get("replaces", [])
        if not isinstance(replaces, list):
            raise FairyError("invalid", "Replacement ids must be a list")
        replacements = [integer(item, "review event id", 1) for item in replaces]
        if producer == "model":
            evidence = strings(command.get("evidence", []), "review evidence")
            if not evidence:
                if selected["scope"] == "content":
                    evidence = [selected["ref"]]
                elif selected["scope"] == "member":
                    evidence = [selected["member"]["ref"]]
                else:
                    by_path = {member["path"]: member for member in state.snapshot["members"]}
                    evidence = [by_path[path]["ref"] for path in selected["paths"]]
        else:
            evidence = []
            for ref in (
                [selected["ref"]]
                if selected["scope"] == "content"
                else [selected["member"]["ref"]]
                if selected["scope"] == "member"
                else [
                    member["ref"]
                    for member in state.snapshot["members"]
                    if member["path"] in selected["paths"]
                ]
            ):
                evidence.append(content_ref(ref))
        context = Context(self.store, state)
        for ref in evidence:
            context.content(ref)
        call_record = state.calls.get(call) if call is not None else None
        review = {
            "criterion": criterion_id,
            "criterion_fingerprint": criterion_fingerprint(criterion),
            "scope": criterion["scope"],
            "target": selected,
            "snapshot": state.snapshot["ref"],
            "verdict": text_value(command["verdict"], "verdict"),
            "basis": text_value(command["basis"], "review basis"),
            "revision": integer(command.get("revision", state.revision), "task revision", 1),
            "producer": producer,
            "call": call,
            "checker_capability": checker_capability,
            "checker_contract": call_record["contract_ref"] if call_record is not None else None,
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
            if initial.snapshot is None:
                raise FairyError("not_ready", "No snapshot to check")
            candidates = [item for item in initial.spec["criteria"] if item["checker"] != "semantic"]
            if criterion is not None:
                candidates = [item for item in candidates if item["id"] == criterion]
                if not candidates:
                    raise FairyError("invalid", "No matching mechanical criterion")
            cursor = initial.seq
            active = initial.active_reviews()
            unresolved = {failure["criterion"] for failure in initial.unresolved_failures()}
            planned = []
            reused = []
            for item in candidates:
                for target in initial.current_targets(item):
                    existing = [
                        review
                        for review in active
                        if review["criterion"] == item["id"]
                        and canonical(review["target"]) == canonical(target)
                        and review["producer"] == "tool:" + item["checker"]
                    ]
                    if existing and item["id"] not in unresolved and item["scope"] == "content":
                        reused.extend(existing)
                    else:
                        planned.append((item, target))
        results = []
        for item, target in planned:
            capability = "snapshot.check" if item["scope"] == "collection" else "content.check"
            parameters = (
                {
                    "snapshot": target["snapshot"],
                    "paths": target["paths"],
                    "checker": item["checker"],
                    "parameters": item["parameters"],
                }
                if item["scope"] == "collection"
                else {
                    "checker": item["checker"],
                    "ref": target["ref"] if item["scope"] == "content" else target["member"]["ref"],
                    "parameters": item["parameters"],
                }
            )
            observation = self.invoke(task, capability, parameters, expected_seq=cursor)
            results.append(observation)
            with self._admitted(task) as current:
                require_open(current)
                if (
                    current.snapshot is None
                    or current.snapshot["ref"] != initial.snapshot["ref"]
                    or canonical(current.spec) != canonical(initial.spec)
                ):
                    raise FairyError("stale", "Snapshot or agreement changed during the check")
                cursor = current.seq
                if observation["status"] != "ok":
                    continue
                replaced = {identity for review in current.reviews for identity in review["replaces"]}
                self._review(
                    current,
                    {
                        "criterion": item["id"],
                        "verdict": observation["result"].get("verdict"),
                        "basis": observation["result"].get("basis"),
                        "target": target.get("ref")
                        if item["scope"] == "content"
                        else target["member"]["path"]
                        if item["scope"] == "member"
                        else target["snapshot"],
                        "replaces": [
                            review["id"]
                            for review in current.reviews
                            if review["criterion"] == item["id"]
                            and review["verdict"] != "pass"
                            and review["id"] not in replaced
                        ],
                    },
                    producer="tool:" + item["checker"],
                    call=observation["call"],
                    target=target,
                    checker_capability=capability,
                )
                cursor += 1
        return {"checks": results, "reused": reused}

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
            decision = text_value(command.get("decision", "maintain"), "learning decision")
            if decision not in {"maintain", "defer", "no_change"}:
                raise FairyError("invalid", "Learning decision must be maintain, defer or no_change")
            note = text_value(command.get("note", ""), "learning note") if command.get("note") else ""
            basis = (
                text_value(command.get("basis", "Host decision after delivery"), "learning basis")
                if command.get("basis")
                else "Host decision after delivery"
            )
            with self._admitted(task, command.get("expected_seq")) as current:
                if current.outcome is None:
                    raise FairyError("not_ready", "Learning decisions follow delivery")
                record = {"decision": decision, "note": note, "basis": basis}
                reply = {"decision": decision, "task": task}
                if decision == "maintain":
                    learning = self._learning_task(current)
                    record["learning_task"] = learning
                    reply["learning_task"] = learning
                self._append(current, "learning_decision", record)
                seq = current.seq + 1
            return {**reply, "seq": seq}
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
                data = text_value(command["text"], "model output", LIMITS.blob_bytes).encode("utf-8")
                ref = self.store.put(data)
                Context(self.store, state).check_capture_limit(ref, len(data))
                output = {
                    "ref": ref,
                    "path": relative_path(command.get("path", "result.md"), "output path"),
                    "bytes": len(data),
                    "media_type": text_value(command.get("media_type", "text/markdown"), "media type"),
                }
                self._append(
                    state,
                    "observed",
                    {"call": command["call"], "status": "ok", "outputs": [output], "origin": "model"},
                )
                result = output
            elif operation == "publish":
                members = members_value(command["members"])
                available: dict[tuple[str, str, str], int] = {
                    (item["ref"], item["path"], item["media_type"]): item["bytes"] for item in state.outputs
                }
                for snapshot in state.snapshots:
                    for item in snapshot["members"]:
                        available[(item["ref"], item["path"], item["media_type"])] = item["bytes"]
                for member in members:
                    key = (member["ref"], member["path"], member["media_type"])
                    if key not in available or available[key] != member["bytes"]:
                        raise FairyError(
                            "permission",
                            "Every member must be an observed output or explicit snapshot member",
                        )
                    if self.store.length(member["ref"]) != member["bytes"]:
                        raise FairyError("integrity", "Member byte count does not match stored content")
                snapshot = snapshot_value(members)
                self.store.put(canonical({"format": 1, "members": snapshot["members"]}))
                self._append(
                    state,
                    "published",
                    {
                        "format": 1,
                        "ref": snapshot["ref"],
                        "members": snapshot["members"],
                        "origin": "runner",
                    },
                )
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
                    user_basis = command.get("user_basis")
                    events = self.store.events(task)
                    revised_at = max((item["seq"] for item in events if item["kind"] == "revised"), default=0)
                    if not any(
                        item["seq"] == user_basis and item["kind"] == "answered" and item["seq"] > revised_at
                        for item in events
                    ):
                        raise FairyError(
                            "permission",
                            "Changing explicit requirements needs a new forwarded user instruction",
                        )
                governance: list[str] = list(state.spec.get("governance", []))
                if "governance" in command:
                    governance = [
                        content_ref(item, "governance asset reference") for item in command["governance"]
                    ]
                governance_scope = list(state.spec.get("governance_scope", []))
                if "governance_scope" in command:
                    governance_scope = task_spec_value(
                        "scope", {"governance_scope": command["governance_scope"]}
                    )["governance_scope"]
                    governance = sorted(
                        set(governance)
                        | {
                            item["ref"]
                            for scope in governance_scope
                            for item in self.library.governance(scope)
                        }
                    )
                for ref in governance:
                    if self.library.status(ref) not in {"trial", "stable"}:
                        raise FairyError(
                            "not_ready",
                            "Governance assets must be adopted before revision",
                        )
                spec = {
                    **state.spec,
                    "goal": text_value(command["goal"], "goal"),
                    "criteria": criteria,
                    "assumptions": strings(command.get("assumptions", []), "assumptions"),
                    "required_roles": required_roles_value(command["required_roles"])
                    if "required_roles" in command
                    else state.spec.get("required_roles", []),
                    "governance": governance,
                    "governance_scope": governance_scope,
                    "provisional": False,
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

    def _record_delivery_progress(self, task: str, member: dict[str, Any]) -> None:
        with self.store.transaction():
            state = self.state(task)
            self._append(state, "delivery_progress", {"member": member})

    def prepare_delivery(self, task: str, plan: Any, expected_seq: int | None = None) -> dict[str, Any]:
        incoming = delivery_plan_value(plan)
        state = self.state(task)
        require_open(state)
        require_sequence(state, expected_seq)
        if state.delivery_plan is None:
            with self.store.transaction():
                current = self.state(task)
                if current.delivery_plan is not None:
                    raise FairyError("conflict", "A delivery plan was recorded concurrently; retry")
                self._append(current, "delivery_planned", {"members": incoming["members"]})
            state = self.state(task)
        else:
            recorded = {item["path"]: item for item in state.delivery_plan["members"]}
            if any(
                item["path"] not in recorded or recorded[item["path"]] != item for item in incoming["members"]
            ):
                raise FairyError(
                    "conflict",
                    "The recorded delivery plan is fixed; change it through an explicit new task",
                )
        if state.delivery_plan is None:
            raise FairyError("integrity", "Delivery plan was not recorded")
        desired = state.delivery_plan["members"]
        context = Context(self.store, state)
        completed: list[str] = sorted(state.delivery_progress)
        members: list[dict[str, Any]] = []
        reused: list[str] = []
        for index, item in enumerate(desired):
            absolute = context.path(item["path"])
            state = self.state(task)
            progress: dict[str, Any] | None = state.delivery_progress.get(item["path"])
            candidates = [
                output
                for output in state.outputs
                if output["path"] == item["path"] and output["media_type"] == item["media_type"]
            ]
            output: dict[str, Any] | None
            if progress is not None:
                output = progress
            elif absolute.is_file():
                ref, _size = self.store.hash_file(absolute)
                matches = [candidate for candidate in candidates if candidate["ref"] == ref]
                output = matches[0] if matches else None
            elif candidates:
                output = candidates[-1]
            else:
                raise FairyError(
                    "missing",
                    "prepare-delivery member file is missing",
                    details={
                        "task": task,
                        "seq": self.state(task).seq,
                        "completed": completed,
                        "remaining": [entry["path"] for entry in desired[index:]],
                    },
                )
            if output is not None:
                reused.append(item["path"])
            else:
                observation = self.invoke(
                    task,
                    "file.capture",
                    {"path": item["path"], "media_type": item["media_type"]},
                )
                if observation["status"] != "ok" or not observation["outputs"]:
                    result = object_value(observation.get("result", {}))
                    raw_code = result.get("error")
                    raw_message = result.get("message")
                    code = raw_code if isinstance(raw_code, str) else "tool_failed"
                    message = raw_message if isinstance(raw_message, str) else "Member capture failed"
                    raise FairyError(
                        code,
                        message,
                        details={
                            "task": task,
                            "seq": self.state(task).seq,
                            "completed": completed,
                            "remaining": [entry["path"] for entry in desired[index:]],
                        },
                    )
                output = observation["outputs"][0]
            member = {
                "ref": output["ref"],
                "path": output["path"],
                "bytes": output["bytes"],
                "media_type": output["media_type"],
                "role": item["role"],
            }
            if item["path"] not in state.delivery_progress:
                self._record_delivery_progress(task, member)
            if item["path"] not in completed:
                completed.append(item["path"])
            members.append(member)
        snapshot = snapshot_value(members)
        current = self.state(task)
        if current.snapshot is not None and canonical(current.snapshot["members"]) == canonical(
            snapshot["members"]
        ):
            published = {"snapshot": current.snapshot, "reused": True}
        else:
            published = self.submit(task, {"op": "publish", "members": members})
        checked = self.submit(task, {"op": "check"})
        return {
            "task": task,
            "seq": self.state(task).seq,
            "members": members,
            "reused_members": reused,
            "published": published,
            "checks": checked.get("checks", []),
            "reused_checks": checked.get("reused", []),
            "next": self.next(task),
        }

    def _publish_members(self, state: State) -> list[dict[str, Any]]:
        required = state.spec.get("required_roles", [])
        members: dict[str, dict[str, Any]] = {}
        if state.snapshot is not None:
            for member in state.snapshot["members"]:
                members[member["path"]] = {
                    key: member[key] for key in ("ref", "path", "bytes", "media_type", "role")
                }
        for output in state.outputs:
            role = members.get(output["path"], {}).get("role", required[0] if len(required) == 1 else "main")
            members[output["path"]] = {**output, "role": role}
        return [members[path] for path in sorted(members)]

    def _review_payload(
        self,
        state: State,
        criterion: dict[str, Any],
        targets: list[dict[str, Any]],
        failure: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if not targets:
            return None
        if criterion["checker"] != "semantic":
            return {"op": "check", "criterion": criterion["id"], "expected_seq": state.seq}
        target = targets[0]
        if target["scope"] == "content":
            selector = target["ref"]
            evidence = [target["ref"]]
        elif target["scope"] == "member":
            selector = target["member"]["path"]
            evidence = [target["member"]["ref"]]
        else:
            selector = target["snapshot"]
            snapshot = state.snapshot
            by_path = {} if snapshot is None else {member["path"]: member for member in snapshot["members"]}
            evidence = [by_path[path]["ref"] for path in target["paths"] if path in by_path]
        payload: dict[str, Any] = {
            "op": "review",
            "criterion": criterion["id"],
            "target": selector,
            "verdict": "pass",
            "basis": "<explain the concrete comparison; change the verdict if it is not a pass>",
            "evidence": evidence,
            "expected_seq": state.seq,
        }
        if failure is not None:
            payload["replaces"] = [failure["id"]]
        return payload

    def _payload(self, state: State, action: str) -> dict[str, Any] | None:
        if action == "prepare_delivery":
            if state.delivery_plan is None:
                return None
            return {"members": state.delivery_plan["members"]}
        if action == "refine":
            return {
                "op": "revise",
                "goal": state.spec["goal"],
                "criteria": state.spec["criteria"],
                "assumptions": state.spec["assumptions"],
                "required_roles": state.spec.get("required_roles", []),
                "governance": state.spec.get("governance", []),
                "reason": "<explain the task-specific refinement>",
                "expected_seq": state.seq,
            }
        if action == "produce":
            return {
                "op": "request",
                "purpose": "<state the concrete work unit>",
                "refs": [item["ref"] for item in state.inputs] + state.spec.get("governance", []),
                "expected_seq": state.seq,
            }
        if action == "publish":
            members = self._publish_members(state)
            if not members:
                return None
            return {"op": "publish", "members": members, "expected_seq": state.seq}
        if action in {"review", "repair"}:
            failures = state.unresolved_failures()
            if failures:
                criterion = next(
                    (item for item in state.spec["criteria"] if item["id"] == failures[0]["criterion"]),
                    None,
                )
                if criterion is not None:
                    payload = self._review_payload(
                        state, criterion, failures[0]["current_targets"], failures[0]
                    )
                    if payload is not None:
                        return payload
            for issue in state.issues():
                if not issue["criterion"]["required"]:
                    continue
                payload = self._review_payload(state, issue["criterion"], issue["targets"])
                if payload is not None:
                    return payload
            members = self._publish_members(state)
            return {"op": "publish", "members": members, "expected_seq": state.seq} if members else None
        if action == "check":
            return {"op": "check", "expected_seq": state.seq}
        if action == "close":
            return {"op": "close", "outcome": "complete", "expected_seq": state.seq}
        if action == "close_partial":
            return {
                "op": "close",
                "outcome": "partial",
                "note": "<state the concrete gap>",
                "expected_seq": state.seq,
            }
        if action == "close_failed":
            return {
                "op": "close",
                "outcome": "failed",
                "note": "<state the specific blocker>",
                "expected_seq": state.seq,
            }
        if action == "resolve_pending":
            for call in state.calls.values():
                if call["status"] not in {"pending", "unknown"} or call.get("confirmation"):
                    continue
                if call["capability"] == MODEL_CAPABILITY:
                    return {
                        "op": "report",
                        "call": call["id"],
                        "path": "result.md",
                        "text": "<actual result>",
                        "expected_seq": state.seq,
                    }
                if call.get("reconciler"):
                    return {
                        "op": "invoke",
                        "capability": call["reconciler"]["name"],
                        "parameters": {"call": call["id"]},
                        "expected_seq": state.seq,
                    }
                return None
        return None

    def _completion(self, state: State) -> dict[str, Any]:
        return {
            "complete": state.complete(),
            "provisional_refined": not state.spec.get("provisional", False),
            "snapshot_ref": None if state.snapshot is None else state.snapshot["ref"],
            "required_roles": state.spec.get("required_roles", []),
            "missing_roles": state.missing_roles(),
            "governance": state.spec.get("governance", []),
            "missing_governance": state.missing_governance(),
            "delivery_plan": state.delivery_plan,
            "missing_delivery_members": state.missing_delivery_members(),
            "required_criteria": [
                criterion["id"] for criterion in state.spec["criteria"] if criterion["required"]
            ],
            "open_issues": [
                {
                    "criterion": issue["criterion"]["id"],
                    "reason": issue["reason"],
                    "targets": issue["targets"],
                }
                for issue in state.issues()
            ],
            "unresolved_failures": [
                {"id": failure["id"], "criterion": failure["criterion"]}
                for failure in state.unresolved_failures()
            ],
            "question_pending": state.question is not None,
            "execution_settled": state.execution_settled(),
        }

    def _recovery(self, state: State) -> dict[str, Any]:
        return {
            "task": state.task,
            "seq": state.seq,
            "revision": state.revision,
            "workspace": str(self.store.home / "workspaces" / state.task),
            "snapshot_ref": None if state.snapshot is None else state.snapshot["ref"],
            "delivery_plan": state.delivery_plan,
            "delivery_progress": sorted(state.delivery_progress),
            "pending_calls": [
                call["id"]
                for call in state.calls.values()
                if call["status"] in {"pending", "unknown"} and not call.get("confirmation")
            ],
            "read_via": "read DOCUMENT --task TASK --pointer /FIELD",
        }

    def next(self, task: str) -> dict[str, Any]:
        events = self.store.events(task)
        state = replay(task, events)
        state.checker_contracts = self._checker_contracts()
        action = state.next_action()
        return {
            "stage_packet_version": 1,
            "task": task,
            "seq": state.seq,
            "revision": state.revision,
            "action": action,
            "payload": self._payload(state, action),
            "inspect_command": f"inspect {task} --history" if action == "inspect_conflict" else None,
            "completion": self._completion(state),
            "recovery": self._recovery(state),
            "goal": state.spec["goal"],
            "criteria": state.spec["criteria"],
            "assumptions": state.spec["assumptions"],
            "provisional": state.spec.get("provisional", False),
            "required_roles": state.spec.get("required_roles", []),
            "governance": state.spec.get("governance", []),
            "missing_governance": state.missing_governance(),
            "role_coverage": state.role_coverage(),
            "missing_roles": state.missing_roles(),
            "effects": state.spec["effects"],
            "budget_left": state.budget_left(),
            "resources": state.resource_status(),
            "resource_warning": state.resource_status()["warning"],
            "execution_settled": state.execution_settled(),
            "execution_conflicts": state.execution_conflicts(),
            "inputs": state.inputs,
            "outputs": state.outputs,
            "snapshot": state.snapshot,
            "delivery_plan": state.delivery_plan,
            "delivery_progress": sorted(state.delivery_progress),
            "missing_delivery_members": state.missing_delivery_members(),
            "publish_candidate": state.outputs[-1] if state.outputs else None,
            "issues": state.issues(),
            "unresolved_failures": state.unresolved_failures(),
            "learning": {
                "decision": state.learning_decisions[-1] if state.learning_decisions else None,
                "decided": bool(state.learning_decisions),
                "todos": (
                    [state.learning_decisions[-1]]
                    if state.learning_decisions and state.learning_decisions[-1]["decision"] == "defer"
                    else []
                ),
                "options": ["maintain", "defer", "no_change"],
                "payload": (
                    {
                        "op": "learn",
                        "decision": "no_change",
                        "note": "<state the concrete learning decision>",
                        "basis": "<cite actual feedback, correction or repetition>",
                        "expected_seq": state.seq,
                    }
                    if state.outcome is not None
                    else None
                ),
            },
            "question": state.question,
            "pending": [
                call
                for call in state.calls.values()
                if (call["status"] in {"pending", "unknown"} and not call.get("confirmation"))
                or call.get("conflicts")
            ],
            "user_updates": [event for event in events if event["kind"] == "answered"],
            "capabilities": self.catalog(limit=LIMITS.catalog_default_limit)["matches"],
            "capability_count": len(self.capabilities),
            "discover_capabilities_via": "capabilities --query TEXT",
            "inspect_capability_via": "capabilities --name NAME",
            "workspace": str(self.store.home / "workspaces" / task),
        }

    def catalog(
        self, query: str = "", limit: int = LIMITS.catalog_default_limit, cursor: str | None = None
    ) -> dict[str, Any]:
        if not 1 <= limit <= LIMITS.catalog_max_limit:
            raise FairyError(
                "limit",
                f"Capability lookup limit must be between 1 and {LIMITS.catalog_max_limit}",
            )
        names = [name for name in sorted(self.capabilities) if query.casefold() in name.casefold()]
        identity = {
            "query": digest(query.encode("utf-8")),
            "catalog": digest(canonical(names)),
        }
        offset = 0 if cursor is None else offset_cursor(cursor, fields=identity)
        page = names[offset : offset + limit]
        result: dict[str, Any] = {
            "matches": [
                {
                    key: value
                    for key, value in self.describe(name).items()
                    if key in {"name", "effect", "description", "contract_ref"}
                }
                for name in page
            ],
            "total": len(names),
        }
        if offset + len(page) < len(names):
            result["next_cursor"] = encode_cursor({"offset": offset + len(page), **identity})
        return result

    def inspect(self, task: str, *, history: bool = False) -> dict[str, Any]:
        events = self.store.events(task)
        state = replay(task, events)
        state.checker_contracts = self._checker_contracts()
        result = self._inspection(state)
        if history:
            result["events"] = events
        return result

    def _inspection(self, state: State) -> dict[str, Any]:
        return {
            "task": state.task,
            "seq": state.seq,
            "revision": state.revision,
            "spec": state.spec,
            "resources": state.resource_status(),
            "outcome": state.outcome,
            "execution_settled": state.execution_settled(),
            "execution_conflicts": state.execution_conflicts(),
            "inputs": state.inputs,
            "snapshots": state.snapshots,
            "snapshot": state.snapshot,
            "delivery_plan": state.delivery_plan,
            "delivery_progress": sorted(state.delivery_progress),
            "missing_delivery_members": state.missing_delivery_members(),
            "governance": state.spec.get("governance", []),
            "missing_governance": state.missing_governance(),
            "learning_decisions": state.learning_decisions,
            "role_coverage": state.role_coverage(),
            "missing_roles": state.missing_roles(),
            "reviews": state.reviews,
            "issues": state.issues(),
            "unresolved_failures": state.unresolved_failures(),
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
        return self._delivery(task)

    def _delivery(self, task: str) -> dict[str, Any]:
        state = self.state(task)
        return deliver_bag(self.store.home, state, self.store, self._inspection(state))

    def validation_task(self, ref: str) -> str:
        with self.store.transaction():
            package = self.library.get(ref)
            size = self.store.length(ref)
            spec = task_spec_value(
                "Validate a reusable workshop asset",
                {
                    "goal": "Check applicability, usefulness and dependencies of " + package["name"],
                    "criteria": validation_criteria(ref),
                    "required_roles": ["candidate"],
                },
                effects=["read", "reason"],
            )
            return self._start(
                spec,
                [
                    {
                        "ref": ref,
                        "name": "candidate.json",
                        "path": "candidate.json",
                        "bytes": size,
                        "media_type": "application/json",
                    }
                ],
                seed=ref,
            )

    def learning_task(self, task: str, expected_seq: int | None = None) -> str:
        command: dict[str, Any] = {"op": "learn", "decision": "maintain"}
        if expected_seq is not None:
            command["expected_seq"] = expected_seq
        return text_value(self.submit(task, command)["learning_task"], "learning task")

    def _learning_task(self, source: State) -> str:
        if not self.store.connection.in_transaction:
            raise FairyError("invalid", "Learning task creation requires an admitted transaction")
        summary = freeze(self.store.home, self.inspect(source.task, history=True), task=source.task)
        data = canonical(summary)
        ref = self.store.put(data)
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
                        "scope": "collection",
                    },
                    {
                        "id": "usable",
                        "description": "Maintenance result is nonempty",
                        "checker": "nonempty",
                        "scope": "collection",
                    },
                ],
            },
            effects=["read", "reason"],
        )
        return self._start(
            spec,
            [
                {
                    "ref": ref,
                    "name": "performance.json",
                    "path": "performance.json",
                    "bytes": len(data),
                    "media_type": "application/json",
                    "source_document": summary,
                }
            ],
        )
