from __future__ import annotations

import unittest
from unittest.mock import patch

from dev.check_review_preparation import frozen_files, load, validate


class ReviewBaselineTests(unittest.TestCase):
    def test_historical_inventory_is_checked_against_git_not_live_repairs(self) -> None:
        inventory, catalog = load()
        self.assertEqual(validate(inventory, catalog, snapshots=False), [])
        frozen = frozen_files(inventory["baseline_commit"])
        path = "skills/astrofairy/scripts/astrofairy/_kernel.py"
        with patch("dev.check_review_preparation.frozen_files", return_value={**frozen, path: b"altered"}):
            self.assertTrue(any(path in error for error in validate(inventory, catalog, snapshots=False)))
        with patch("dev.check_review_preparation.frozen_files", return_value={**frozen, "extra.py": b""}):
            self.assertIn(
                "Frozen commit files differ from the registered inventory",
                validate(inventory, catalog, snapshots=False),
            )
