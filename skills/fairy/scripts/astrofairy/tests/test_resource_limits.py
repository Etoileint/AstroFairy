from __future__ import annotations

from astrofairy import FairyError
from astrofairy._contracts import SchemaContract, schema, text_value
from astrofairy._limits import LIMITS
from astrofairy.tests._support import WorkshopTest, mock_capability


class ResourceLimitTests(WorkshopTest):
    def test_limits_manifest_is_the_single_typed_source(self) -> None:
        manifest = LIMITS.manifest()
        budgets = {item["budget"] for item in manifest}
        self.assertTrue({"B03", "B06", "B07", "B08", "B09", "B10", "B11", "B12", "B13"} <= budgets)
        self.assertTrue({"B14", "B15", "B16", "B18", "B19", "B20", "B21", "B22", "B23"} <= budgets)
        self.assertTrue({"B24", "B25", "B26", "B27", "B28", "B29", "B30", "B31", "B32"} <= budgets)
        self.assertTrue({"B33", "B34", "B35", "B36", "B37", "B38", "B39", "B40", "B41"} <= budgets)
        for item in manifest:
            self.assertTrue(item["field"])
            self.assertTrue(item["unit"])
            self.assertTrue(item["consumer"])
            self.assertEqual(item["value"], getattr(LIMITS, item["field"]))
        self.assertEqual(schema()["resource_limits"], manifest)

    def test_text_fields_and_schemas_have_independent_budgets(self) -> None:
        self.assertEqual(len(text_value("x" * LIMITS.text_field_bytes, "field")), LIMITS.text_field_bytes)
        with self.assertRaises(FairyError):
            text_value("x" * (LIMITS.text_field_bytes + 1), "field")
        base = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
        }
        with self.assertRaises(FairyError):
            SchemaContract({**base, "description": "x" * LIMITS.schema_bytes})
        small = SchemaContract(base)
        self.assertEqual(small.schema["type"], "object")

    def test_capability_catalog_pages_with_an_opaque_cursor(self) -> None:
        for index in range(LIMITS.catalog_default_limit + 2):
            self.workshop.register(
                f"extra.tool{index:02d}",
                mock_capability("read", lambda _context, _parameters: {"outputs": []}),
            )
        first = self.workshop.catalog()
        self.assertEqual(len(first["matches"]), LIMITS.catalog_default_limit)
        self.assertIn("next_cursor", first)
        second = self.workshop.catalog(cursor=first["next_cursor"])
        self.assertTrue(second["matches"])
        self.assertEqual(len(first["matches"]) + len(second["matches"]), first["total"])
        first_names = {item["name"] for item in first["matches"]}
        second_names = {item["name"] for item in second["matches"]}
        self.assertFalse(first_names & second_names)
        with self.assertRaises(FairyError):
            self.workshop.catalog(cursor="not-a-cursor")

    def test_search_page_uses_the_fifty_result_ordinary_default(self) -> None:
        from astrofairy._cli import _parser  # noqa: PLC0415 - parser is the CLI field authority.

        arguments = _parser().parse_args(["--home", str(self.home), "assets", "search"])
        self.assertEqual(arguments.limit, LIMITS.search_page_default_limit)
        arguments = _parser().parse_args(["--home", str(self.home), "capabilities"])
        self.assertEqual(arguments.limit, LIMITS.catalog_default_limit)
