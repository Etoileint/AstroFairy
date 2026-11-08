# ruff: noqa: INP001 - Standalone handoff tool, not an importable Python package.

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = Path(__file__).resolve().parent


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    assignment = json.loads((DIRECTORY / "assignment.json").read_text(encoding="utf-8"))
    encoded = (DIRECTORY / "candidate-manifest.json").read_bytes()
    if _digest(encoded) != assignment["candidate_manifest_sha256"]:
        raise ValueError("Candidate manifest identity differs from the assignment")
    manifest = json.loads(encoded)
    candidate = assignment["candidate_commit"]
    if manifest["candidate_commit"] != candidate:
        raise ValueError("Candidate commit differs from the assignment")
    git = shutil.which("git")
    if git is None:
        raise FileNotFoundError("Git is required to verify the candidate")
    head = subprocess.check_output([git, "rev-parse", "HEAD"], cwd=ROOT, text=True, encoding="utf-8").strip()
    ancestry = subprocess.run([git, "merge-base", "--is-ancestor", candidate, head], cwd=ROOT, check=False)
    errors = []
    if ancestry.returncode != 0:
        errors.append({"path": ".git", "error": "HEAD is not based on the assigned candidate"})
    assigned = {row["path"] for row in manifest["files"]}
    actual = subprocess.check_output(
        [git, "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
    ).decode("utf-8")
    errors.extend(
        {"path": name, "error": "unassigned source file"}
        for name in filter(None, actual.split("\0"))
        if name not in assigned
        and name not in assignment["handoff_documents"]
        and not name.startswith("handoff/")
    )
    errors.extend(
        {"path": name, "error": "obsolete file reintroduced"}
        for name in assignment["deleted_paths"]
        if (ROOT / name).exists()
    )
    overlays = set(assignment["navigation_overlays"])
    checked = 0
    for row in [*manifest["files"], *assignment["artifacts"]]:
        name = row["path"]
        if name in overlays:
            continue
        path = ROOT / name
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT) or not path.is_file():
            errors.append({"path": name, "error": "missing, linked or escaped file"})
            continue
        try:
            data = path.read_bytes()
        except OSError:
            errors.append({"path": name, "error": "unreadable file"})
            continue
        if len(data) != row["bytes"] or _digest(data) != row["sha256"]:
            errors.append({"path": name, "error": "bytes differ from the assigned identity"})
        checked += 1
    result = {
        "head": head,
        "candidate_commit": candidate,
        "candidate_manifest_sha256": _digest(encoded),
        "checked_files": checked,
        "navigation_overlays": sorted(overlays),
        "errors": errors,
        "meaning": "Source and artifact identity check only; not product or native-platform acceptance",
    }
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
