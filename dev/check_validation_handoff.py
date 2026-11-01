from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/evaluation"
FILE_FIELDS = (
    "return_report",
    "runs_file",
    "metrics_file",
    "coverage_file",
    "findings_file",
    "sources_file",
    "human_trial_kit_file",
)


def read_json(path: Path, *, max_bytes: int = 16 * 1024 * 1024) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result

    with path.open("rb") as stream:
        raw = stream.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("JSON metadata exceeds its size budget")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique)


def local_file(root: Path, name: str) -> Path:
    path = PurePosixPath(name)
    if not name or "\\" in name or path.as_posix() != name or path.is_absolute() or ".." in path.parts:
        raise ValueError("Evidence paths must stay inside their declared directory")
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Linked evidence paths are unsupported")
    target = root / name
    if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()) or not target.is_file():
        raise ValueError(f"Missing, linked or escaped file: {name}")
    return target


def fingerprint(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"bytes": path.stat().st_size, "sha256": checksum}


def check_files(root: Path, rows: list[dict[str, Any]]) -> int:
    seen = set()
    for row in rows:
        name = row["path"]
        if name in seen:
            raise ValueError("Duplicate file identity")
        seen.add(name)
        if fingerprint(local_file(root, name)) != {key: row[key] for key in ("bytes", "sha256")}:
            raise ValueError(f"File identity changed: {name}")
    return len(seen)


def check_baseline(root: Path = ROOT) -> dict[str, int]:
    baseline = read_json(PACKAGE / "baseline.json")
    result = {"baseline_files": check_files(root, baseline["files"])}
    assets = PACKAGE / "assets.json"
    if assets.is_file():
        result["handoff_files"] = check_files(ROOT, read_json(assets)["files"])
    else:
        raise ValueError("Handoff asset seal is missing")
    return result


def check_return(directory: Path) -> dict[str, Any]:
    from jsonschema import Draft202012Validator  # noqa: PLC0415 - baseline verification is stdlib-only.

    submission = read_json(local_file(directory, "submission.json"), max_bytes=1024 * 1024)
    schema = read_json(PACKAGE / "submission.schema.json")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(submission)
    baseline = read_json(PACKAGE / "baseline.json")
    if submission["source_manifest_sha256"] != baseline["source_manifest_sha256"]:
        raise ValueError("Return does not identify the assigned source snapshot")
    inventory = read_json(local_file(directory, submission["evidence_inventory"]))
    if not isinstance(inventory, list):
        raise TypeError("Evidence inventory must be an array")
    for row in inventory:
        if (
            not isinstance(row, dict)
            or set(row) != {"path", "bytes", "sha256"}
            or not isinstance(row["path"], str)
            or type(row["bytes"]) is not int
            or row["bytes"] < 0
            or not isinstance(row["sha256"], str)
            or not re.fullmatch(r"[a-f0-9]{64}", row["sha256"])
        ):
            raise ValueError("Malformed evidence identity")
    count = check_files(directory, inventory)
    indexed = {row["path"] for row in inventory}
    references = {submission[field] for field in FILE_FIELDS}
    for item in submission["work"].values():
        if item["outcome"] in {"supported", "limited"} and not item["evidence"]:
            raise ValueError("Supported or limited judgments need evidence")
        references.update(item["evidence"])
    human = submission["human_evidence"]
    if submission["work"]["P05"]["outcome"] == "supported" and not human:
        raise ValueError("P05 cannot be supported without claimed real-member evidence")
    if human:
        references.add(human)
    if references - indexed:
        raise ValueError("A referenced evidence file is not in the sealed inventory")
    for name in references:
        local_file(directory, name)
    return {
        "structure_and_file_identities": "valid",
        "evidence_files": count,
        "work": {key: item["outcome"] for key, item in submission["work"].items()},
        "meaning": "Not proof of execution, human identity, quality, authority or product acceptance",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify the F09 handoff identity and returned evidence structure"
    )
    parser.add_argument(
        "--root", type=Path, default=ROOT, help="Assigned source or extracted source snapshot"
    )
    parser.add_argument(
        "--artifacts", type=Path, help="Optional directory containing the three F09 artifacts"
    )
    parser.add_argument("--return", dest="returned", type=Path, help="Completed return directory")
    args = parser.parse_args()
    result: dict[str, Any] = check_baseline(args.root)
    if args.artifacts:
        baseline = read_json(PACKAGE / "baseline.json")
        result["artifacts"] = check_files(
            args.artifacts, [{"path": row["name"], **row} for row in baseline["artifacts"]]
        )
    if args.returned:
        result["return"] = check_return(args.returned)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
