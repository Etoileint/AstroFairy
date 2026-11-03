from __future__ import annotations

import hashlib
import json
from pathlib import Path

from astrofairy._search import MODEL_FILES, MODEL_NAME, MODEL_REVISION, MODEL_SOURCE, PROFILE

ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / "dev/model_profiles"
MANIFEST = PROFILE_DIR / "multilingual-e5-large.json"


def require(condition: bool, message: str) -> None:  # noqa: FBT001 - validates a predicate.
    if not condition:
        raise ValueError(message)


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(manifest["format"] == 1, "Unsupported model profile format")
    require(manifest["model"] == MODEL_NAME, "Model profile name differs from the runtime profile")
    require(manifest["source"] == MODEL_SOURCE, "Model profile source differs from the runtime profile")
    require(
        manifest["revision"] == MODEL_REVISION,
        "Model profile revision differs from the runtime profile",
    )
    require(
        {name: item["sha256"] for name, item in manifest["files"].items()} == MODEL_FILES,
        "Model file hashes differ from the runtime profile",
    )
    api = PROFILE_DIR / manifest["api_snapshot"]
    require(api.is_file(), "Model API snapshot is missing")
    require(
        hashlib.sha256(api.read_bytes()).hexdigest() == manifest["api_snapshot_sha256"],
        "Model API snapshot identity mismatch",
    )
    embedding = PROFILE["embedding"]
    require(embedding["dimension"] == manifest["dimension"], "Profile dimension differs")
    require(embedding["model_max_tokens"] == manifest["model_max_tokens"], "Profile token budget differs")
    return {"model": MODEL_NAME, "revision": MODEL_REVISION, "files": len(MODEL_FILES)}


if __name__ == "__main__":
    print("Model profile agrees with the runtime and API snapshot:", validate())
