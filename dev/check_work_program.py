from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate(path: Path) -> dict[str, int]:
    program = json.loads(path.read_text(encoding="utf-8"))
    source = path.parent / program["source"]
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != program["source_sha256"]:
        raise ValueError("Original assessment identity differs from the declared baseline")
    assessment = json.loads(raw)
    work = {item["id"]: item for item in program["work"]}
    if len(work) != len(program["work"]):
        raise ValueError("Duplicate work identity")
    for item in work.values():
        if item["status"] not in {"planned", "active", "awaiting_evidence", "technical_verified", "accepted"}:
            raise ValueError("Unknown work status")
        if item["status"] in {"technical_verified", "accepted"} and not item["evidence"]:
            raise ValueError("Verified work needs evidence")
        if any(not (path.parent / name).is_file() for name in item["evidence"]):
            raise ValueError("Missing work evidence")
    routes = program["routes"]
    expected = {item["id"].split("-")[0] for item in assessment["checks"]}
    if set(routes) != expected or any(not targets or set(targets) - set(work) for targets in routes.values()):
        raise ValueError("Incomplete original-round routing")
    counts = {}
    for surface in ("checks", "requirements", "scenarios", "object_dispositions"):
        objects = assessment[surface]
        for item in objects:
            identity = item["id"]
            if surface == "checks":
                rounds = [identity.split("-")[0]]
            elif surface == "object_dispositions":
                rounds = [item["latest_q08_record"]["round"]]
            else:
                rounds = re.findall(r"R[0-9]{2}", item["evidence_rounds"])
            if not rounds or any(round_id not in routes for round_id in rounds):
                raise ValueError(f"Unrouted original object: {identity}")
        counts[surface] = len(objects)
    notes = {note for item in work.values() for note in item.get("notes", [])}
    if notes != {item["id"] for item in assessment["other_notes"]}:
        raise ValueError("Original notes lack an explicit work destination")
    repairs = json.loads((path.parent / program["repairs"]).read_text(encoding="utf-8"))
    original = {
        item["id"] for item in assessment["confirmed_open_findings"] + assessment["open_boundary_candidates"]
    }
    if {item["id"] for item in repairs["findings"]} != original:
        raise ValueError("Repair ledger differs from the original finding set")
    if work["P00"]["status"] in {"technical_verified", "accepted"} and any(
        item["status"] != "verified" for item in repairs["findings"]
    ):
        raise ValueError("Repair work cannot bypass an unfinished finding")
    if type(program["product_accepted"]) is not bool:
        raise TypeError("Product acceptance must be boolean")
    if program["product_accepted"] and any(item["status"] != "accepted" for item in work.values()):
        raise ValueError("Product acceptance cannot bypass unfinished work")
    return {**counts, "notes": len(notes), "workstreams": len(work)}


if __name__ == "__main__":
    print(
        "Original scope routed; this does not prove product acceptance:",
        validate(ROOT / "docs/repairs/work-program.json"),
    )
