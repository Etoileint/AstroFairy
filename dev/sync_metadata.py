from __future__ import annotations

import argparse
import ast
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render(root: Path) -> dict[Path, bytes]:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    runtime = root / project["tool"]["setuptools"]["packages"]["find"]["where"][0] / "astrofairy"
    tree = ast.parse((runtime / "_version.py").read_text(encoding="utf-8"))
    version = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)
    )
    match = re.fullmatch(r"(\d+\.\d+\.\d+)(?:(a|b|rc)(\d+))?", version)
    if match is None:
        raise ValueError("Package version cannot be expressed as a plugin semantic version")
    base, suffix, number = match.groups()
    plugin_version = base + (
        "-" + {"a": "alpha", "b": "beta", "rc": "rc"}[suffix] + "." + number if suffix else ""
    )
    metadata = project["project"]
    author = metadata["authors"][0]["name"]
    plugin = {
        "name": metadata["name"],
        "version": plugin_version,
        "description": metadata["description"],
        "author": {"name": author},
        "license": metadata["license"],
        "skills": ["./skills/astrofairy"],
    }
    marketplace = {
        "name": metadata["name"],
        "owner": {"name": author},
        "plugins": [{"name": metadata["name"], "source": "./", "description": metadata["description"]}],
    }
    return {
        root / ".claude-plugin/plugin.json": (json.dumps(plugin, ensure_ascii=False, indent=2) + "\n").encode(
            "utf-8"
        ),
        root / ".claude-plugin/marketplace.json": (
            json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8"),
        root / "skills/astrofairy/LICENSE": (root / "LICENSE").read_bytes(),
    }


def sync(root: Path, *, check: bool) -> list[str]:
    drift = []
    for path, expected in render(root).items():
        if path.exists() and path.read_bytes() == expected:
            continue
        drift.append(str(path.relative_to(root)))
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
    return drift


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Keep plugin metadata and bundled license in sync with their sources"
    )
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    drift = sync(ROOT, check=arguments.check)
    if arguments.check and drift:
        print("Generated metadata drift: " + ", ".join(drift))
        return 1
    print("Generated metadata is current" if not drift else "Generated " + ", ".join(drift))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
