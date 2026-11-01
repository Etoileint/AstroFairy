from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from dev.check import ROOT

CASE = "import unittest\nclass Cases(unittest.TestCase):\n    def test_case(self):\n        pass\n"


class ExecutionTests(unittest.TestCase):
    def fixture(self, files: dict[str, str]) -> subprocess.CompletedProcess[str]:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            root = Path(temporary)
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-B", "-m", "dev.run_tests", str(root / "cases"), str(root), "test*.py"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

    def test_nested_unimportable_tests_are_refused(self) -> None:
        result = self.fixture(
            {"cases/__init__.py": "", "cases/test_ok.py": CASE, "cases/nested/test_lost.py": CASE}
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("test_lost.py", result.stderr)
        self.assertIn("missing=", result.stderr)

    def test_standard_fixtures_and_nested_tests_execute(self) -> None:
        source = """import unittest
calls = []
def setUpModule():
    calls.append("module")
class Cases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        calls.append("class")
    def test_fixtures(self):
        self.assertEqual(calls, ["module", "class"])
"""
        result = self.fixture(
            {
                "cases/__init__.py": "",
                "cases/test_ok.py": source,
                "cases/nested/__init__.py": "",
                "cases/nested/test_more.py": CASE,
            }
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ran 2 tests", result.stderr)

    def test_collected_failures_execute(self) -> None:
        result = self.fixture(
            {"cases/__init__.py": "", "cases/test_fail.py": CASE.replace("pass", "self.fail()")}
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAILED (failures=1)", result.stderr)

    def test_missing_zero_foreign_and_duplicate_cases_are_refused(self) -> None:
        variants = [
            (
                "import unittest\ndef load_tests(loader, tests, pattern):\n    return unittest.TestSuite()\n",
                {},
            ),
            ("import unittest\n", {}),
            ("from helper import Cases\n", {"helper.py": CASE}),
            (
                CASE
                + "\ndef load_tests(loader, tests, pattern):\n"
                + "    return unittest.TestSuite([tests, tests])\n",
                {},
            ),
            ("raise RuntimeError('broken import')\n", {}),
        ]
        for source, extra in variants:
            with self.subTest(source=source):
                result = self.fixture({"cases/__init__.py": "", "cases/test_case.py": source, **extra})
                self.assertNotEqual(result.returncode, 0, result.stderr)

    def test_custom_execution_containers_and_function_cases_are_refused(self) -> None:
        for hook in (
            (
                "class Custom(unittest.TestSuite):\n"
                "    def run(self, result, debug=False):\n        return result\n"
                "def load_tests(loader, tests, pattern):\n    return Custom([tests])\n"
            ),
            (
                "def load_tests(loader, tests, pattern):\n"
                "    return unittest.TestSuite([unittest.FunctionTestCase(lambda: None)])\n"
            ),
        ):
            with self.subTest(hook=hook):
                result = self.fixture({"cases/__init__.py": "", "cases/test_case.py": CASE + hook})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Only native unittest suites", result.stderr)

    def test_skipped_cases_count_as_collected_and_remain_visible(self) -> None:
        result = self.fixture(
            {
                "cases/__init__.py": "",
                "cases/test_case.py": CASE.replace(
                    "    def test_case", "    @unittest.skip('intentional')\n    def test_case"
                ),
            }
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skipped=1", result.stderr)
