from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package(output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    target = output / "astrofairy.zip"
    base = ROOT / "skills/astrofairy"
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
            archive.write(path, (Path("astrofairy") / relative).as_posix())
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    arguments = parser.parse_args()
    print(package(arguments.out))


if __name__ == "__main__":
    main()
