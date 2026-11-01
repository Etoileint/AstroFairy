from __future__ import annotations

import sys
import unittest
from pathlib import Path


def collected_suite(surface: Path, top: Path, pattern: str) -> unittest.TestSuite:
    surface = surface.resolve()
    expected = {path.resolve() for path in surface.rglob(pattern) if path.is_file()}
    loader = unittest.TestLoader()
    discovered = loader.discover(str(surface), pattern=pattern, top_level_dir=str(top.resolve()))
    if loader.errors:
        raise ValueError("Test discovery errors:\n" + "\n".join(loader.errors))
    cases: list[unittest.TestCase] = []

    def collect(item: unittest.TestSuite | unittest.TestCase) -> None:
        if type(item) is unittest.TestSuite:
            for child in item:
                collect(child)
        elif isinstance(item, unittest.TestCase) and not isinstance(item, unittest.FunctionTestCase):
            cases.append(item)
        else:
            raise ValueError("Only native unittest suites and module-owned TestCase instances are supported")

    collect(discovered)
    owners: set[Path] = set()
    identities: set[str] = set()
    for case in cases:
        module = sys.modules[type(case).__module__]
        if not getattr(module, "__file__", None):
            raise ValueError(f"Test has no owning module file: {case.id()}")
        owners.add(Path(module.__file__).resolve())
        if case.id() in identities:
            raise ValueError(f"Duplicate test id: {case.id()}")
        identities.add(case.id())
    if not cases or owners != expected:
        missing = sorted(str(path) for path in expected - owners)
        foreign = sorted(str(path) for path in owners - expected)
        raise ValueError(
            f"Test collection mismatch: missing={missing}, foreign={foreign}, cases={len(cases)}"
        )
    return unittest.TestSuite(cases)
