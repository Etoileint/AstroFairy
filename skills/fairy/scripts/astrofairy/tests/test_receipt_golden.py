from __future__ import annotations

import hashlib
import json
from pathlib import Path

from astrofairy import Workshop
from astrofairy._capabilities import Capability
from astrofairy._contracts import RECEIPT_PROJECTION_FORMAT, canonical
from astrofairy._delivery import _receipt
from astrofairy._kernel import replay
from astrofairy.tests._support import LiteralSearch, WorkshopTest

FIXTURE = Path(__file__).parent / "fixtures/receipt-projection-2.json"


class ReceiptGoldenTests(WorkshopTest):
    def test_frozen_events_produce_the_committed_receipt_bytes(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture["format"], 1)
        state = replay(fixture["task"], fixture["events"])
        self.assertEqual(RECEIPT_PROJECTION_FORMAT, 2)
        self.assertFalse(state.live_checkers)
        self.assertEqual(state.checker_contracts, {})
        inspection = self.workshop._inspection(state)
        receipt = _receipt(state, inspection)
        encoded = canonical(receipt)
        self.assertEqual(encoded, canonical(fixture["receipt"]["body"]))
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), fixture["receipt"]["canonical_sha256"])

    def test_changed_live_checkers_do_not_change_the_historical_receipt(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        receipt = fixture["receipt"]["body"]
        with Workshop(self.home, search=LiteralSearch(self.home)) as other:
            shared = other.capabilities["snapshot.check"]
            other.register(
                "snapshot.check",
                Capability(
                    shared.effect,
                    shared.handler,
                    description="Changed checker definition",
                    input_schema=shared.input_schema,
                ),
                replace=True,
            )
            historical = replay(fixture["task"], fixture["events"])
            self.assertFalse(historical.live_checkers)
            self.assertEqual(historical.checker_contracts, {})
            rebuilt = _receipt(historical, other._inspection(historical))
            self.assertEqual(canonical(rebuilt), canonical(receipt))
