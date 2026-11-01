from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

from astrofairy import FairyError
from astrofairy._capabilities import Capability, Context
from astrofairy._contracts import SchemaContract, canonical
from astrofairy.tests._support import WorkshopTest

DIALECT = "https://json-schema.org/draft/2020-12/schema"


def object_schema(properties: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    return {
        "$schema": DIALECT,
        "type": "object",
        "properties": properties or {},
        "additionalProperties": False,
        **extra,
    }


class ToolContractTests(WorkshopTest):
    def test_discovery_and_execution_use_same_immutable_value_contract(self) -> None:
        effects: list[object] = []

        def measure(_context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
            effects.append(parameters["count"])
            return {"outputs": [], "value": parameters["count"]}

        schema = object_schema({"count": {"type": "integer", "minimum": 1, "maximum": 3}}, required=["count"])
        self.workshop.register(
            "domain.measure",
            Capability("write", measure, description="Count one to three days", input_schema=schema),
        )
        schema["properties"]["count"]["minimum"] = -100
        details = self.workshop.describe("domain.measure")
        details["inputSchema"]["properties"]["count"]["minimum"] = -100
        summary = self.workshop.catalog("domain.measure")["matches"][0]
        self.assertNotIn("inputSchema", summary)
        self.assertEqual(
            self.workshop.describe("domain.measure")["inputSchema"]["properties"]["count"]["minimum"], 1
        )
        task = self.workshop.start("Measure")
        before = canonical(self.workshop.inspect(task, history=True))
        blobs = self.workshop.store.connection.execute("SELECT count(*) FROM blobs").fetchone()[0]
        for parameters in (
            {},
            {"count": True},
            {"count": "SYNTHETIC_SECRET"},
            {"count": 0},
            {"count": 4},
            {"count": None},
            {"count": 2, "extra": 1},
        ):
            with self.subTest(parameters=parameters), self.assertRaises(FairyError) as caught:
                self.workshop.invoke(task, "domain.measure", parameters)
            self.assertNotIn("SYNTHETIC_SECRET", json.dumps(caught.exception.as_dict()))
        self.assertEqual(canonical(self.workshop.inspect(task, history=True)), before)
        self.assertEqual(
            self.workshop.store.connection.execute("SELECT count(*) FROM blobs").fetchone()[0], blobs
        )
        self.assertEqual(effects, [])
        self.assertEqual(self.workshop.invoke(task, "domain.measure", {"count": 2.0})["status"], "ok")
        self.assertEqual(effects, [2.0])
        self.workshop.register(
            "domain.measure",
            Capability(
                "read",
                measure,
                description="A list-valued replacement",
                input_schema=object_schema(
                    {"count": {"type": "array", "items": {"type": "string"}}}, required=["count"]
                ),
            ),
            replace=True,
        )
        self.assertNotEqual(self.workshop.describe("domain.measure")["contract_ref"], summary["contract_ref"])

    def test_diagnostics_do_not_echo_dynamic_keys_or_values(self) -> None:
        contract = SchemaContract(
            object_schema(
                {"payload": {"type": "object", "additionalProperties": {"type": "integer"}}},
                required=["payload"],
            )
        )
        with self.assertRaises(FairyError) as caught:
            contract.validate({"payload": {"SYNTHETIC_SECRET_KEY": "SYNTHETIC_SECRET_VALUE"}})
        data = caught.exception.as_dict()
        self.assertNotIn("SYNTHETIC_SECRET", json.dumps(data))
        self.assertEqual(data["details"]["issues"][0]["rule"], "type")

    def test_static_refs_and_referenced_literal_data_are_checked(self) -> None:
        schema = object_schema(
            {"value": {"$ref": "#/$defs/positive"}},
            required=["value"],
            **{"$defs": {"positive": {"type": "integer", "minimum": 1}}},
        )
        contract = SchemaContract(schema)
        contract.validate({"value": 1})
        with self.assertRaises(FairyError):
            contract.validate({"value": 0})
        literal = object_schema(
            {}, examples=[{"misspelledType": "data", "$ref": "https://invalid.test/data"}]
        )
        SchemaContract(literal).validate({})
        with self.assertRaises(FairyError):
            SchemaContract({**literal, "$ref": "#/examples/0"})

    def test_nested_resource_anchor_and_recursive_static_schema_work(self) -> None:
        node = {
            "$anchor": "node",
            "type": "object",
            "properties": {"child": {"$ref": "#node"}},
            "additionalProperties": False,
        }
        schema = object_schema({"tree": {"$ref": "#node"}}, **{"$defs": {"node": node}})
        SchemaContract(schema).validate({"tree": {"child": {"child": {}}}})
        with self.assertRaises(FairyError):
            SchemaContract(schema).validate({"tree": {"child": 2}})
        nested = object_schema(
            {
                "item": {
                    "$id": "urn:local-item",
                    "type": "object",
                    "properties": {"value": {"$ref": "#/$defs/int"}},
                    "$defs": {"int": {"type": "integer"}},
                    "additionalProperties": False,
                }
            }
        )
        SchemaContract(nested).validate({"item": {"value": 3}})

    def test_reference_fragment_lexical_profile_and_safe_resolution_failures(self) -> None:
        for token in ("-1", "+0", "00", " 0", "\uff10", "1_0", "1.0", "not-an-index", "~2", "%ZZ", "%FF"):
            with self.subTest(token=token), self.assertRaises(FairyError) as caught:
                SchemaContract(object_schema({}, examples=[{}], **{"$ref": "#/examples/" + token}))
            self.assertEqual(caught.exception.code, "invalid_contract")
            self.assertNotIn(token, json.dumps(caught.exception.as_dict()))
        SchemaContract(object_schema({}, examples=[{}], **{"$ref": "#/examples/%30"})).validate({})
        SchemaContract(object_schema({}, **{"$defs": {"a/b~c": {}}, "$ref": "#/$defs/a~1b~0c"})).validate({})
        for key in ("%2F", "%7E"):
            SchemaContract(
                object_schema({}, **{"$defs": {key: {}}, "$ref": "#/$defs/" + key.replace("%", "%25")})
            ).validate({})
        with self.assertRaises(FairyError):
            SchemaContract(object_schema({}, **{"$defs": {"-1": {}}, "$ref": "#/$defs/-1"}))

    def test_model_named_tool_does_not_collide_with_host_model_operation(self) -> None:
        self.workshop.register(
            "model",
            Capability(
                "reason",
                lambda _c, _p: {"outputs": []},
                description="Distinct model-named extension",
                input_schema=object_schema(
                    {"purpose": {"type": "string"}, "refs": {"type": "array"}}, required=["purpose", "refs"]
                ),
            ),
        )
        task = self.workshop.start("Work")
        request = self.workshop.submit(task, {"op": "request", "purpose": "Explain", "refs": []})
        result = self.workshop.invoke(task, "model", {"purpose": "Explain", "refs": []})
        self.assertEqual(result["status"], "ok")
        self.assertNotEqual(request["call"], result["call"])

    def test_unknown_dynamic_deprecated_unresolved_and_foreign_refs_refused_without_io(self) -> None:
        variants = [
            object_schema({}, minimun=1),
            object_schema({}, **{"$dynamicAnchor": "x"}),
            object_schema({}, **{"$dynamicRef": "#"}),
            object_schema({}, definitions={}),
            object_schema({}, **{"$ref": "#/$defs/missing"}),
            object_schema({}, **{"$ref": "https://invalid.test/SYNTHETIC_SECRET"}),
            object_schema({}, **{"$ref": "file:///SYNTHETIC_SECRET"}),
            object_schema({}, **{"$schema": "https://invalid.test/other-dialect"}),
        ]
        with patch(
            "urllib.request.urlopen", side_effect=AssertionError("Unexpected network retrieval")
        ) as network:
            for schema in variants:
                with self.subTest(schema=schema), self.assertRaises(FairyError):
                    SchemaContract(schema)
        network.assert_not_called()

    def test_format_is_annotation_and_defaults_do_not_mutate_parameters(self) -> None:
        contract = SchemaContract(
            object_schema(
                {"date": {"type": "string", "format": "date"}, "optional": {"type": "integer", "default": 2}}
            )
        )
        parameters = {"date": "not-a-date"}
        contract.validate(parameters)
        self.assertEqual(parameters, {"date": "not-a-date"})

    def test_public_and_unexpected_failures_are_distinct_and_bounded(self) -> None:
        def public(_context: Context, _parameters: dict[str, Any]) -> dict[str, Any]:
            raise FairyError("not_ready", "Choose an active rendering profile")

        def private(_context: Context, _parameters: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError("SYNTHETIC_SECRET")

        task = self.workshop.start("Render")
        for name, handler in (("public", public), ("private", private)):
            self.workshop.register(
                name,
                Capability("read", handler, description="Fixture rendering", input_schema=object_schema()),
            )
        self.assertEqual(
            self.workshop.invoke(task, "public", {})["result"]["message"],
            "Choose an active rendering profile",
        )
        self.assertNotIn("SYNTHETIC_SECRET", json.dumps(self.workshop.invoke(task, "private", {})))
        for error in (
            FairyError("invalid", "x" * 5000),
            FairyError("invalid", "line\nbreak"),
            FairyError("INVALID_SECRET", "unsafe"),
            FairyError("invalid", "bad details", details={"x": object()}),
        ):
            self.assertEqual(error.as_dict()["error"], "invalid_diagnostic")

    def test_known_write_refusal_does_not_create_unknown_and_preflight_is_ordered(self) -> None:
        task = self.workshop.start("Write")
        for parameters in ({"path": "note.txt", "text": 3}, {"path": "../../escape", "text": "data"}):
            with self.assertRaises(FairyError):
                self.workshop.invoke(task, "text.write", parameters)
        self.assertEqual(self.workshop.state(task).calls, {})
        prepared: list[str] = []

        def preflight(_context: Context, _parameters: dict[str, Any]) -> None:
            prepared.append("checked")
            raise FairyError("invalid", "Business precondition not satisfied")

        self.workshop.register(
            "preflight",
            Capability(
                "write",
                lambda _c, _p: {"outputs": []},
                description="Non-effecting preflight fixture",
                input_schema=object_schema(),
                prepare=preflight,
            ),
        )
        readonly = self.workshop.start("Read only", effects=["read"])
        with self.assertRaises(FairyError):
            self.workshop.invoke(readonly, "preflight", {})
        self.assertEqual(prepared, [])
        with self.assertRaises(FairyError):
            self.workshop.invoke(task, "preflight", {})
        self.assertEqual(prepared, ["checked"])
        self.assertEqual(self.workshop.state(task).calls, {})

    def test_preflight_may_not_mutate_arguments(self) -> None:
        def change(_context: Context, parameters: dict[str, Any]) -> None:
            parameters["x"] = 1

        self.workshop.register(
            "changing",
            Capability(
                "write",
                lambda _c, _p: {"outputs": []},
                description="Invalid preflight fixture",
                input_schema=object_schema(),
                prepare=change,
            ),
        )
        task = self.workshop.start("Work")
        with self.assertRaises(FairyError):
            self.workshop.invoke(task, "changing", {})
        self.assertEqual(self.workshop.state(task).calls, {})

    def test_unexpected_preflight_and_deep_diagnostics_fail_safely(self) -> None:
        def failure(_context: Context, _parameters: dict[str, Any]) -> None:
            raise RuntimeError("SYNTHETIC_SECRET")

        self.workshop.register(
            "preflight.failure",
            Capability(
                "write",
                lambda _c, _p: {"outputs": []},
                description="Unexpected preflight fixture",
                input_schema=object_schema(),
                prepare=failure,
            ),
        )
        task = self.workshop.start("Work")
        with self.assertRaises(FairyError) as caught:
            self.workshop.invoke(task, "preflight.failure", {})
        self.assertNotIn("SYNTHETIC_SECRET", json.dumps(caught.exception.as_dict()))
        self.assertEqual(self.workshop.state(task).calls, {})
        value: Any = 0
        for _ in range(4096):
            value = [value]
        self.assertEqual(
            FairyError("invalid", "deep details", details={"value": value}).as_dict()["error"],
            "invalid_diagnostic",
        )
        with (
            patch("astrofairy._contracts.json.dumps", side_effect=RecursionError),
            self.assertRaises(FairyError),
        ):
            canonical({"value": 1})

    def test_post_write_and_output_schema_failure_remain_unknown_after_replacement(self) -> None:
        effects: list[str] = []

        def performed(_context: Context, _parameters: dict[str, Any]) -> dict[str, Any]:
            effects.append("effect")
            return {"outputs": [], "mode": "unexpected"}

        output = object_schema(
            {"outputs": {"type": "array"}, "mode": {"enum": ["approved"]}}, required=["outputs", "mode"]
        )
        self.workshop.register(
            "write",
            Capability(
                "write",
                performed,
                description="Output failure fixture",
                input_schema=object_schema(),
                output_schema=output,
            ),
        )
        task = self.workshop.start("Work")
        self.assertEqual(self.workshop.invoke(task, "write", {})["status"], "unknown")
        self.workshop.register(
            "write",
            Capability("write", performed, description="Replacement metadata", input_schema=object_schema()),
            replace=True,
        )
        with self.assertRaises(FairyError):
            self.workshop.invoke(task, "write", {})
        self.assertEqual(effects, ["effect"])

    def test_historical_definitions_are_task_scoped_lazy_and_survive_changes(self) -> None:
        task = self.workshop.start("Write")
        self.workshop.invoke(task, "text.write", {"path": "note.txt", "text": "data"})
        call = next(iter(self.workshop.state(task).calls.values()))
        ref = call["contract_ref"]
        original = self.workshop.inspect_contract(task, ref)
        self.assertEqual(
            original["definition"]["inputSchema"], self.workshop.describe("text.write")["inputSchema"]
        )
        self.workshop.submit(task, {"op": "close", "outcome": "cancelled"})
        self.workshop.register(
            "text.write",
            Capability(
                "write",
                lambda _c, _p: {"outputs": []},
                description="New definition",
                input_schema=object_schema(),
            ),
            replace=True,
        )
        self.assertEqual(self.workshop.inspect_contract(task, ref)["definition"], original["definition"])
        self.assertNotIn("inputSchema", json.dumps(self.workshop.inspect(task)))
        other = self.workshop.start("Unrelated")
        with self.assertRaises(FairyError):
            self.workshop.inspect_contract(other, ref)
        with self.assertRaises(TypeError):
            self.workshop.capabilities["mutable"] = self.workshop.capabilities["text.write"]

    def test_registration_rejects_duplicates_bad_names_and_oversized_definitions(self) -> None:
        capability = self.workshop.capabilities["text.write"]
        for name in ("bad name", "", "x" * 129, "host.model"):
            with self.subTest(name=name), self.assertRaises(FairyError):
                self.workshop.register(name, capability)
        with self.assertRaises(FairyError):
            self.workshop.register("text.write", capability)
        with self.assertRaises(FairyError):
            Capability("read", lambda _c, _p: {}, description="x" * 513, input_schema=object_schema())

    def test_malformed_public_details_do_not_prevent_post_write_observation(self) -> None:
        variants: list[dict[Any, Any]] = [
            {1: "number key", "label": "mixed"},
            {"control": "bad\u202evalue"},
            {"nested": {1: "number key"}},
            {"not_finite": float("nan")},
        ]
        for details in variants:
            with self.subTest(details=details):

                def faulty(
                    context: Context, _parameters: dict[str, Any], payload: dict[Any, Any] = details
                ) -> dict[str, Any]:
                    context.path("effect.txt").write_text("Actual effect", encoding="utf-8")
                    raise FairyError("invalid", "Public diagnostic", details=payload)

                self.workshop.register(
                    "bad.diagnostic",
                    Capability(
                        "write", faulty, description="Diagnostic fixture", input_schema=object_schema()
                    ),
                    replace=True,
                )
                task = self.workshop.start("Work")
                result = self.workshop.invoke(task, "bad.diagnostic", {})
                self.assertEqual(result["status"], "unknown")
                self.assertEqual(result["result"]["error"], "invalid_diagnostic")
                self.assertEqual(self.workshop.state(task).calls[result["call"]]["status"], "unknown")
                self.assertEqual(
                    (self.home / "workspaces" / task / "effect.txt").read_text(encoding="utf-8"),
                    "Actual effect",
                )
