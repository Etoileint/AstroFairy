from __future__ import annotations

import ast
import fnmatch
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {
    ".git",
    ".venv",
    ".fairy",
    ".test-runs",
    ".evaluation",
    ".reference",
    ".tools",
    ".tmp",
    ".cache",
    "build",
    "dist",
    "__pycache__",
}
# Frozen design/review records stay bound to their Git baseline; their relative source links are historical.
HISTORICAL_DOC_ROOTS = (
    "docs/reviews",
    "docs/optimization/2026-11-plan",
    "docs/optimization/2026-11-use-feedback",
    "docs/optimization/2026-11-implementation/handoff",
)


def project_files() -> list[Path]:
    result = []
    for base, directories, files in os.walk(ROOT):
        directories[:] = [
            name for name in directories if name not in IGNORED and not name.endswith(".egg-info")
        ]
        result.extend(Path(base) / name for name in files)
    return result


def structural_checks() -> list[str]:
    config = tomllib.loads((ROOT / "governance.toml").read_text(encoding="utf-8"))
    errors = []
    surfaces = {ROOT / surface["path"] for surface in config["tests"]["surfaces"]}
    if (ROOT / "tests").exists():
        errors.append("Tests belong to their owner; root tests/ is forbidden")
    errors.extend(
        f"Declared test surface is missing or empty: {surface.relative_to(ROOT)}"
        for surface in surfaces
        if not surface.is_dir() or not list(surface.rglob(config["tests"]["pattern"]))
    )
    for path in project_files():
        if path.suffix == ".py":
            source = path.read_text(encoding="utf-8")
            ast.parse(source, filename=str(path))
            if re.search(r"#\s*type:\s*ignore\s*(?:$|#)", source, re.MULTILINE):
                errors.append(f"Bare typing suppression: {path.relative_to(ROOT)}")
            if fnmatch.fnmatchcase(path.name, config["tests"]["pattern"]) and not any(
                path.is_relative_to(surface) for surface in surfaces
            ):
                errors.append(f"Unregistered test: {path.relative_to(ROOT)}")
        if path.suffix == ".md":
            if any(path.is_relative_to(ROOT / root) for root in HISTORICAL_DOC_ROOTS):
                continue
            source = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
            for raw_target in re.findall(r"\]\(([^)]+)\)", source):
                target = raw_target.split("#", 1)[0].strip("<>")
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                if target.startswith("/") or not (path.parent / target).exists():
                    errors.append(
                        f"Broken or absolute document reference in {path.relative_to(ROOT)}: {target}"
                    )
    return errors


def main() -> int:
    errors = structural_checks()
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    config = tomllib.loads((ROOT / "governance.toml").read_text(encoding="utf-8"))
    commands = [
        ["-m", "dev.run_tests", surface["path"], surface["top"], config["tests"]["pattern"]]
        for surface in config["tests"]["surfaces"]
    ] + config["checks"]["commands"]
    for arguments in commands:
        result = subprocess.run([sys.executable, *arguments], cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
    core_lines = sum(
        len((ROOT / path).read_text(encoding="utf-8").splitlines())
        for path in config["architecture"]["core_files"]
    )
    skill_bytes = (ROOT / "skills/fairy/SKILL.md").stat().st_size
    print(f"Architecture metrics: skill_bytes={skill_bytes} core_lines={core_lines}; reviewed, not capped.")
    print("Tests, typing, style and document references passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
