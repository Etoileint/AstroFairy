from __future__ import annotations

import hashlib
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

from astrofairy import FairyError
from astrofairy._library import Library
from astrofairy._search import (
    MODEL_CACHE_REPO,
    MODEL_REVISION,
    CharTokenizer,
    FastEmbedder,
    SearchIndex,
    observations,
)
from astrofairy.tests._support import ROOT, WorkshopTest
from astrofairy.tests.test_search_contracts import CountingEmbedder, HashEmbedder

SMALL = {
    "model.onnx": b"onnx-payload",
    "model.onnx_data": b"onnx-external-data",
    "tokenizer.json": b'{"tokenizer": true}',
    "config.json": b'{"config": true}',
    "tokenizer_config.json": b'{"tokenizer_config": true}',
    "special_tokens_map.json": b'{"special_tokens": true}',
}
SMALL_HASHES = {name: hashlib.sha256(data).hexdigest() for name, data in SMALL.items()}
SMALL_SIZES = {name: len(data) for name, data in SMALL.items()}


def _cache(root: Path) -> Path:
    cache = root / "cache"
    snapshot = cache / MODEL_CACHE_REPO / "snapshots" / MODEL_REVISION
    snapshot.mkdir(parents=True)
    for name, data in SMALL.items():
        (snapshot / name).write_bytes(data)
    return cache


def _snapshot(cache: Path) -> Path:
    return cache / MODEL_CACHE_REPO / "snapshots" / MODEL_REVISION


class PrepareCountingEmbedder(HashEmbedder):
    def __init__(self) -> None:
        self.prepares = 0

    def prepare(self) -> dict[str, Any]:
        self.prepares += 1
        return {
            "model": "test-model",
            "revision": "test-revision",
            "verification": {"depth": "test-double"},
            "downloaded": False,
        }


class SearchPreparationTests(WorkshopTest):
    def approved(self, **changes: Any) -> str:
        ref = self.workshop.library.propose({**self.proposal(), **changes})
        task = self.workshop.validation_task(ref)
        self.finish(task, "asset-fitness")
        self.workshop.library.adopt(ref, task)
        return ref

    def test_empty_prepare_and_refresh_share_one_service(self) -> None:
        embedder = PrepareCountingEmbedder()
        index = SearchIndex(self.workshop.store, embedder=embedder, tokenizer=CharTokenizer())
        preparation = index.prepare()
        self.assertEqual(embedder.prepares, 1)
        self.assertEqual(preparation["model"], "test-model")
        refreshed = index.refresh()
        self.assertEqual(embedder.prepares, 2)
        self.assertEqual(refreshed["projection"]["state"], "empty")
        self.assertEqual(refreshed["assets"], 0)
        self.assertEqual(refreshed["preparation"]["model"], "test-model")
        self.assertIsNone(self.workshop.store.projection())
        page = Library(self.workshop.store, search=index).search_page("anything", refresh=True)
        self.assertEqual(embedder.prepares, 3)
        self.assertEqual(page["matches"], [])
        self.assertEqual(page["projection"]["state"], "empty")
        self.assertEqual(page["preparation"]["revision"], "test-revision")

    def test_explicit_refresh_result_survives_filters_without_matches(self) -> None:
        self.approved(summary="Personal only", tags=[])
        embedder = CountingEmbedder()
        index = SearchIndex(self.workshop.store, embedder=embedder, tokenizer=CharTokenizer())
        library = Library(self.workshop.store, search=index)
        page = library.search_page("", scope="team", refresh=True)
        self.assertEqual(page["matches"], [])
        self.assertEqual(page["total"], 0)
        self.assertEqual(page["projection"]["state"], "current")
        self.assertIn("preparation", page)
        browsed = embedder.embedded
        library.search_page("")
        self.assertEqual(embedder.embedded, browsed)

    def test_six_consumed_files_are_verified_on_every_explicit_check(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with (
            tempfile.TemporaryDirectory(dir=directory) as temporary,
            patch.multiple(
                "astrofairy._search",
                MODEL_FILES=SMALL_HASHES,
                MODEL_FILE_SIZES=SMALL_SIZES,
            ),
        ):
            cache = _cache(Path(temporary))
            embedder = FastEmbedder(cache)
            record = embedder.verify()
            self.assertEqual(set(record["files"]), set(SMALL))
            self.assertEqual(record["verification"]["depth"], "sha256")
            self.assertEqual(embedder.model_dir(), _snapshot(cache))
            original = (_snapshot(cache) / "tokenizer_config.json").read_bytes()
            corrupted = bytes([original[0] ^ 1]) + original[1:]
            (_snapshot(cache) / "tokenizer_config.json").write_bytes(corrupted)
            with self.assertRaisesRegex(FairyError, "does not match"):
                embedder.verify()
            with self.assertRaisesRegex(FairyError, "does not match"):
                embedder.model_dir()
            (_snapshot(cache) / "tokenizer_config.json").write_bytes(original)
            self.assertEqual(set(embedder.verify()["files"]), set(SMALL))

    def test_each_consumed_file_is_required(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with (
            tempfile.TemporaryDirectory(dir=directory) as temporary,
            patch.multiple(
                "astrofairy._search",
                MODEL_FILES=SMALL_HASHES,
                MODEL_FILE_SIZES=SMALL_SIZES,
            ),
        ):
            for name in SMALL:
                with self.subTest(file=name):
                    root = Path(temporary) / name.replace(".", "_")
                    root.mkdir()
                    cache = _cache(root)
                    (_snapshot(cache) / name).unlink()
                    with self.assertRaises(FairyError) as caught:
                        FastEmbedder(cache).verify()
                    self.assertEqual(caught.exception.details["stage"], "model")
                    self.assertEqual(caught.exception.details["missing"], name)
                    self.assertFalse(caught.exception.details["recovery"]["builds_index"])

    def test_doctor_observations_are_layered_and_read_only(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            absent = Path(temporary) / "absent"
            observation = observations(absent)
            self.assertEqual(observation["model"]["state"], "absent")
            self.assertEqual(observation["projection"]["state"], "not_checked")
            self.assertIn("dependencies", observation)
            self.assertEqual(len(observation["recovery"]), 3)
            self.assertFalse(absent.exists())
        with (
            tempfile.TemporaryDirectory(dir=directory) as temporary,
            patch.multiple(
                "astrofairy._search",
                MODEL_FILES=SMALL_HASHES,
                MODEL_FILE_SIZES=SMALL_SIZES,
            ),
        ):
            cache = _cache(Path(temporary))
            self.assertEqual(observations(cache)["model"]["state"], "present_unverified")
            verified = observations(cache, verify=True)["model"]
            self.assertEqual(verified["state"], "verified")
            self.assertEqual(verified["verification"]["depth"], "sha256")
            (_snapshot(cache) / "config.json").write_bytes(b"x" * SMALL_SIZES["config.json"])
            self.assertEqual(observations(cache)["model"]["state"], "present_unverified")
            self.assertEqual(observations(cache, verify=True)["model"]["state"], "invalid")

    def test_competing_preparations_serialize_on_one_cache(self) -> None:
        directory = ROOT / ".test-runs"
        directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            cache = _cache(Path(temporary))
            state = {"active": 0, "peak": 0}
            guard = threading.Lock()
            files = {
                name: {"bytes": size, "sha256": SMALL_HASHES[name]} for name, size in SMALL_SIZES.items()
            }

            def slow_verify(_self: FastEmbedder) -> dict[str, Any]:
                with guard:
                    state["active"] += 1
                    state["peak"] = max(state["peak"], state["active"])
                time.sleep(0.05)
                with guard:
                    state["active"] -= 1
                return {
                    "model": "model",
                    "revision": "revision",
                    "files": files,
                    "verification": {"depth": "sha256"},
                    "downloaded": False,
                }

            embedders = [FastEmbedder(cache), FastEmbedder(cache)]
            results: list[dict[str, Any]] = []
            threads = [
                threading.Thread(target=lambda item=item: results.append(item.prepare()))
                for item in embedders
            ]
            with patch.object(FastEmbedder, "verify", slow_verify):
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=10)
            self.assertEqual(state["peak"], 1)
            self.assertEqual(len(results), 2)

    def test_missing_or_mismatched_dependency_metadata_is_reported_separately(self) -> None:
        embedder = PrepareCountingEmbedder()
        index = SearchIndex(self.workshop.store, embedder=embedder, tokenizer=CharTokenizer())
        broken = [{"name": "lancedb", "required": "0.41.0", "installed": "0.40.0", "marker": None}]
        with (
            patch("astrofairy._search.dependency_observations", return_value=broken),
            self.assertRaises(FairyError) as caught,
        ):
            index.prepare()
        self.assertEqual(caught.exception.details["stage"], "dependencies")
        self.assertEqual(caught.exception.details["dependencies"]["lancedb"]["installed"], "0.40.0")
        with patch("astrofairy._search.dependency_observations", return_value=broken):
            observation = observations(self.workshop.store.home / "search" / "models")
        self.assertFalse(observation["dependencies"]["ready"])
        self.assertEqual(observation["model"]["state"], "absent")
