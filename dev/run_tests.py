from __future__ import annotations

import sys
import unittest
from pathlib import Path

from dev._testing import collected_suite


def main(arguments: list[str]) -> int:
    surface, top, pattern = arguments
    try:
        suite = collected_suite(Path(surface), Path(top), pattern)
    except (ImportError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
