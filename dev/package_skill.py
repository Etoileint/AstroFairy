from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _validate_links(archive: zipfile.ZipFile) -> None:
    names = set(archive.namelist())
    for name in sorted(item for item in names if item.endswith(".md")):
        text = archive.read(name).decode("utf-8")
        for target in _LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path = target.split("#", 1)[0]
            if not path:
                continue
            resolved = PurePosixPath(name).parent / path
            if resolved.is_absolute() or ".." in resolved.parts:
                raise ValueError(f"Skill link escapes the package: {name} -> {target}")
            if resolved.as_posix() not in names:
                raise ValueError(f"Skill link target is absent: {name} -> {target}")


def package(output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    target = output / "fairy.zip"
    base = ROOT / "skills/fairy"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(base.rglob("*")):
            relative = path.relative_to(base)
            if (
                not path.is_file()
                or any(part.startswith(".") or part.endswith(".egg-info") for part in relative.parts)
                or any(part in {"__pycache__", "tests"} for part in relative.parts)
                or path.suffix == ".pyc"
            ):
                continue
            archive.write(path, (Path("fairy") / relative).as_posix())
    try:
        with zipfile.ZipFile(target) as archive:
            _validate_links(archive)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    arguments = parser.parse_args()
    print(package(arguments.out))


if __name__ == "__main__":
    main()
