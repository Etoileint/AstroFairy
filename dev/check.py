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
    entry = ROOT / "skills/astrofairy/SKILL.md"
    if entry.stat().st_size > config["budgets"]["skill_bytes"]:
        errors.append("Skill entry exceeds its context budget; move conditional detail behind references")
    core_lines = sum(
        len((ROOT / path).read_text(encoding="utf-8").splitlines())
        for path in config["budgets"]["core_files"]
    )
    if core_lines > config["budgets"]["core_lines"]:
        errors.append("Core exceeds its reviewed size budget; inspect responsibility placement")
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
    print("Tests, typing, style, document references and growth budgets passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
