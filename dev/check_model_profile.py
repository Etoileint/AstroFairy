from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from astrofairy._search import (
    MODEL_FILE_SIZES,
    MODEL_FILES,
    MODEL_NAME,
    MODEL_REVISION,
    MODEL_SOURCE,
    PROFILE,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / "dev/model_profiles"
MANIFEST = PROFILE_DIR / "multilingual-e5-large.json"
SEARCH_LOCK = ROOT / "skills/fairy/scripts/requirements-search.lock"
SEARCH_SNAPSHOTS = ROOT / "dev/search_snapshots"

# Fixed audit obligations for the committed FastEmbed 0.9.1 consumer sources.
# A dependency upgrade or consumer source change reopens this audit explicitly;
# the mutable manifest declaration is verified against this set, never trusted
# as the set itself.
FIXED_CONSUMPTION = frozenset(
    {
        "model.onnx",
        "model.onnx_data",
        "tokenizer.json",
        "tokenizer_config.json",
        "config.json",
        "special_tokens_map.json",
    }
)


def require(condition: bool, message: str) -> None:  # noqa: FBT001 - validates a predicate.
    if not condition:
        raise ValueError(message)


def _locked_versions(search_lock: Path) -> dict[str, str]:
    versions = {}
    for line in search_lock.read_text(encoding="utf-8").splitlines():
        match = re.match(r"([A-Za-z0-9_.-]+)==([^\s;\\]+)", line)
        if match is not None:
            versions[match.group(1).lower().replace("_", "-")] = match.group(2)
    return versions


def _official_wheel_hashes(snapshot: Path, version: str) -> dict[str, str]:
    metadata = json.loads(snapshot.read_bytes())
    require(metadata.get("info", {}).get("version") == version, "Consumer snapshot version mismatch")
    hashes = {}
    for item in metadata.get("urls", []):
        if not isinstance(item, dict):
            continue
        if item.get("packagetype") != "bdist_wheel" or item.get("yanked"):
            continue
        digest = item.get("digests", {}).get("sha256")
        filename = item.get("filename")
        if isinstance(digest, str) and isinstance(filename, str):
            hashes[filename] = digest
    require(bool(hashes), "Consumer snapshot publishes no usable wheel")
    return hashes


def _consumer_audit(profile_dir: Path, manifest: dict[str, Any], version: str) -> dict[str, Any]:
    audit = manifest["consumer_audit"]
    require(audit.get("package") == "fastembed", "Consumer audit names an unexpected package")
    consumer_path = profile_dir / audit["manifest"]
    require(consumer_path.is_file(), "Consumer audit manifest is missing")
    try:
        consumer = json.loads(consumer_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise ValueError(f"Consumer audit manifest is unreadable: {exc}") from exc
    require(consumer.get("format") == 1, "Unsupported consumer audit format")
    require(consumer.get("package") == "fastembed", "Consumer audit package mismatch")
    require(consumer.get("version") == version, "Consumer audit version differs from the locked package")
    require(
        (audit.get("version"), audit.get("wheel_sha256"))
        == (consumer.get("version"), consumer.get("wheel_sha256")),
        "Model profile consumer identity differs from the audit manifest",
    )
    return consumer


def _consumed_from_sources(consumer: dict[str, Any], consumer_path: Path) -> set[str]:
    consumed: set[str] = set()
    for relative, recorded in consumer["sources"].items():
        source = consumer_path.parent / relative
        require(source.is_file(), f"Consumer source is missing: {relative}")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        require(digest == recorded["sha256"], f"Consumer source changed without re-audit: {relative}")
        text = source.read_text(encoding="utf-8")
        observed = {name for name in FIXED_CONSUMPTION if name in text}
        declared = set(recorded.get("consumes", []))
        require(
            declared == observed,
            f"Consumer declaration disagrees with the fixed source: {relative}",
        )
        consumed |= observed
    require(
        consumed >= FIXED_CONSUMPTION,
        "Fixed consumer sources no longer read every audited model file",
    )
    return consumed


def validate(root: Path | None = None) -> dict[str, object]:
    base = ROOT if root is None else root
    manifest_path = MANIFEST if root is None else base / "dev/model_profiles/multilingual-e5-large.json"
    profile_dir = manifest_path.parent
    search_lock = SEARCH_LOCK if root is None else base / "skills/fairy/scripts/requirements-search.lock"
    snapshots = SEARCH_SNAPSHOTS if root is None else base / "dev/search_snapshots"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest["format"] == 1, "Unsupported model profile format")
    require(manifest["model"] == MODEL_NAME, "Model profile name differs from the runtime profile")
    require(manifest["source"] == MODEL_SOURCE, "Model profile source differs from the runtime profile")
    require(
        manifest["revision"] == MODEL_REVISION,
        "Model profile revision differs from the runtime profile",
    )
    declared = {
        name: {"bytes": item["bytes"], "sha256": item["sha256"]} for name, item in manifest["files"].items()
    }
    require(
        {name: item["sha256"] for name, item in declared.items()} == MODEL_FILES,
        "Model file hashes differ from the runtime profile",
    )
    require(
        {name: item["bytes"] for name, item in declared.items()} == MODEL_FILE_SIZES,
        "Model file sizes differ from the runtime profile",
    )
    require(
        PROFILE["embedding"]["files"] == MODEL_FILES,
        "Runtime profile does not consume the audited file set",
    )
    locked = _locked_versions(search_lock)
    version = str(locked.get("fastembed"))
    require(manifest.get("fastembed") == version, "Model profile fastembed differs from the locked package")
    consumer = _consumer_audit(profile_dir, manifest, version)
    official = _official_wheel_hashes(snapshots / f"fastembed-{version}.source", version)
    wheel = str(consumer.get("wheel_sha256"))
    require(
        official.get(str(consumer.get("wheel_filename"))) == wheel,
        "Consumer audit wheel is not an official artifact of the locked version",
    )
    consumed = _consumed_from_sources(consumer, profile_dir / manifest["consumer_audit"]["manifest"])
    classified = dict(consumer.get("consumed_files", {}))
    require(
        set(classified) == consumed == set(MODEL_FILES) == set(PROFILE["embedding"]["files"]),
        "Consumer audit, runtime constants and model profile disagree on the consumed file set",
    )
    require(
        set(classified.values()) <= {"required", "optional_but_fixed"},
        "Consumer audit uses an unknown presence policy",
    )
    for name in ("onnxruntime", "tokenizers"):
        require(
            locked.get(name) == manifest[name],
            f"Model profile {name} differs from the locked search dependency",
        )
    require(
        PROFILE["embedding"]["fastembed"] == version,
        "Runtime profile fastembed version differs from the lock",
    )
    api = profile_dir / manifest["api_snapshot"]
    require(api.is_file(), "Model API snapshot is missing")
    require(
        hashlib.sha256(api.read_bytes()).hexdigest() == manifest["api_snapshot_sha256"],
        "Model API snapshot identity mismatch",
    )
    siblings = {
        item["rfilename"]
        for item in json.loads(api.read_text(encoding="utf-8")).get("siblings", [])
        if isinstance(item, dict) and isinstance(item.get("rfilename"), str)
    }
    require(set(MODEL_FILES) <= siblings, "The fixed revision does not publish every consumed file")
    embedding = PROFILE["embedding"]
    require(embedding["dimension"] == manifest["dimension"], "Profile dimension differs")
    require(embedding["model_max_tokens"] == manifest["model_max_tokens"], "Profile token budget differs")
    return {
        "model": MODEL_NAME,
        "revision": MODEL_REVISION,
        "files": len(MODEL_FILES),
        "consumer": f"fastembed=={version}",
        "consumer_wheel": wheel[:12],
    }


if __name__ == "__main__":
    print("Model profile agrees with the runtime, consumer audit, lock and API snapshot:", validate())
