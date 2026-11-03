from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "dev/vendor/bagit-1.9.0"
WHEELS = ROOT / "skills/fairy/scripts/wheels"
LOCK = ROOT / "skills/fairy/scripts/requirements-delivery.lock"


def fingerprint(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def require(condition: bool, message: str) -> None:  # noqa: FBT001 - validates a predicate.
    if not condition:
        raise ValueError(message)


def validate() -> dict[str, object]:
    manifest = json.loads((VENDOR / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["format"] == 1, "Unsupported vendor manifest")
    require(manifest["package"] == "bagit" and manifest["version"] == "1.9.0", "Wrong vendor identity")
    source = manifest["source"]
    output = manifest["output"]
    source_path = VENDOR / source["file"]
    wheel_path = VENDOR / output["file"]
    require(
        fingerprint(source_path) == {"bytes": source["bytes"], "sha256": source["sha256"]},
        "Vendored sdist identity mismatch",
    )
    actual = fingerprint(wheel_path)
    require(
        actual == {"bytes": output["bytes"], "sha256": output["sha256"]}, "Vendored wheel identity mismatch"
    )
    with zipfile.ZipFile(wheel_path) as archive:
        require(archive.testzip() is None, "Vendored wheel is damaged")
        names = archive.namelist()
        require("bagit.py" in names, "Vendored wheel lacks bagit.py")
        require("bagit-1.9.0.dist-info/METADATA" in names, "Vendored wheel lacks metadata")
        metadata = archive.read("bagit-1.9.0.dist-info/METADATA").decode("utf-8")
        require(
            "Name: bagit\n" in metadata and "Version: 1.9.0\n" in metadata,
            "Vendored wheel metadata identity mismatch",
        )
    copied = WHEELS / output["file"]
    require(copied.is_file() and fingerprint(copied) == actual, "Skill wheel copy differs from vendor")
    lock = LOCK.read_text(encoding="utf-8")
    require("bagit==1.9.0" in lock and output["sha256"] in lock, "Delivery lock does not bind the wheel")
    return {"package": "bagit", "version": "1.9.0", "wheel_sha256": output["sha256"]}


if __name__ == "__main__":
    print("Vendored build artifacts agree:", validate())
