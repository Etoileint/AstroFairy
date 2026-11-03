from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast

from astrofairy._contracts import canonical, digest, object_value, parse_json
from astrofairy._errors import FairyError
from astrofairy._limits import LIMITS
from astrofairy._pagination import encode_cursor, offset_cursor

if TYPE_CHECKING:
    from collections.abc import Iterator

    from astrofairy._store import Store

MODEL_NAME = "intfloat/multilingual-e5-large"
MODEL_SOURCE = "Qdrant/multilingual-e5-large-onnx"
MODEL_REVISION = "ac6781cd1cf88b8306a536d7c9d18a5bd57cc14b"
MODEL_FILES = {
    "model.onnx": "1c09780c907c8a91a77a6ab1fd231f79e090d2907ca431223703dfebeed3d36c",
    "model.onnx_data": "0cf1883fee81c63819a44e2ba0efa51d4043d9759685a4ebebbde97e0623d15c",
    "tokenizer.json": "f59925fcb90c92b894cb93e51bb9b4a6105c5c249fe54ce1c704420ac39b81af",
}
MODEL_DIMENSION = 1024
MODEL_MAX_TOKENS = 512
MODEL_CACHE_REPO = "models--Qdrant--multilingual-e5-large-onnx"
CHUNK_TOKENS = 480
CANDIDATE_POOL = LIMITS.candidate_pool

PROFILE: dict[str, Any] = {
    "format": 1,
    "backend": {
        "name": "lancedb",
        "version": "0.41.0",
        "fusion": {
            "method": "weighted_rrf",
            "k": 60,
            "full_text_weight": 2.0,
            "vector_weight": 1.0,
        },
        "vector_query": "exact",
        "fts": {
            "base_tokenizer": "icu",
            "stem": False,
            "remove_stop_words": False,
            "ascii_folding": False,
        },
    },
    "embedding": {
        "model": MODEL_NAME,
        "source": MODEL_SOURCE,
        "revision": MODEL_REVISION,
        "files": MODEL_FILES,
        "fastembed": "0.9.1",
        "onnxruntime": "1.31.1",
        "tokenizers": "0.23.3",
        "dimension": MODEL_DIMENSION,
        "normalize": True,
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
        "model_max_tokens": MODEL_MAX_TOKENS,
    },
    "chunking": {
        "max_tokens": CHUNK_TOKENS,
        "structural": "paragraphs+workflow-steps",
        "fields": [
            "name",
            "summary",
            "tags",
            "applicability",
            "dependencies",
            "invalidation",
            "inputs",
            "parameters",
            "steps",
            "body",
            "evidence",
        ],
    },
}
PROFILE_ID = digest(canonical(PROFILE))


class Embedder(Protocol):
    dimension: int

    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class Tokenizer(Protocol):
    def split(self, text: str, max_tokens: int) -> list[str]: ...


class FastTokenizer:
    def __init__(self, path: Path) -> None:
        try:
            from tokenizers import Tokenizer as TokenizerImpl  # noqa: PLC0415 - lazy search dependency.
        except Exception as exc:
            raise FairyError("search_not_ready", "Prepare the locked tokenizer dependency") from exc
        self._tokenizer = TokenizerImpl.from_file(str(path))
        self._tokenizer.no_truncation()

    def split(self, text: str, max_tokens: int) -> list[str]:
        if not text.strip():
            return []
        encoding = self._tokenizer.encode(text, add_special_tokens=False)
        offsets = [(start, end) for start, end in encoding.offsets if end > start]
        if not offsets:
            return []
        if len(offsets) <= max_tokens:
            return [text]
        result = []
        for start in range(0, len(offsets), max_tokens):
            window = offsets[start : start + max_tokens]
            begin, end = window[0][0], window[-1][1]
            if end > begin:
                result.append(text[begin:end])
        return result


class CharTokenizer:
    def split(self, text: str, max_tokens: int) -> list[str]:
        return [text[start : start + max_tokens] for start in range(0, len(text), max_tokens) if text]


class FastEmbedder:
    dimension = MODEL_DIMENSION

    def __init__(self, cache_dir: Path, *, threads: int = 2) -> None:
        self.cache_dir = cache_dir
        self.threads = threads
        self._model: Any | None = None
        self._verified_dir: Path | None = None

    def model_dir(self) -> Path:
        if self._verified_dir is not None:
            return self._verified_dir
        path = self.cache_dir / MODEL_CACHE_REPO / "snapshots" / MODEL_REVISION
        if not path.is_dir():
            raise FairyError(
                "search_not_ready",
                "Prepare the fixed multilingual retrieval model before searching",
                details={
                    "model": MODEL_NAME,
                    "revision": MODEL_REVISION,
                    "prepare_via": "assets search --refresh",
                },
            )
        for name, expected in MODEL_FILES.items():
            file = path / name
            if not file.is_file():
                raise FairyError(
                    "search_not_ready",
                    "The fixed model revision is incomplete; prepare it explicitly",
                    details={"model": MODEL_NAME, "revision": MODEL_REVISION, "missing": name},
                )
            try:
                with file.open("rb") as stream:
                    actual = hashlib.file_digest(stream, "sha256").hexdigest()
            except OSError as exc:
                raise FairyError(
                    "search_not_ready",
                    "The fixed model revision could not be read; prepare it explicitly",
                    details={"model": MODEL_NAME, "revision": MODEL_REVISION, "file": name},
                ) from exc
            if actual != expected:
                raise FairyError(
                    "search_not_ready",
                    "The fixed model revision does not match the locked files",
                    details={"model": MODEL_NAME, "revision": MODEL_REVISION, "file": name},
                )
        self._verified_dir = path
        return path

    def prepare(self) -> dict[str, Any]:
        try:
            from huggingface_hub import snapshot_download  # noqa: PLC0415 - lazy search dependency.
        except Exception as exc:
            raise FairyError("search_not_ready", "Prepare the locked model download dependency") from exc
        self.cache_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = self.cache_dir / MODEL_CACHE_REPO / "snapshots" / MODEL_REVISION
        if path.is_dir():
            try:
                return {
                    "model": MODEL_NAME,
                    "revision": MODEL_REVISION,
                    "path": str(self.model_dir()),
                }
            except FairyError:
                self._verified_dir = None
        try:
            downloaded = snapshot_download(
                repo_id=MODEL_SOURCE,
                revision=MODEL_REVISION,
                cache_dir=str(self.cache_dir),
                allow_patterns=[
                    "model.onnx",
                    "model.onnx_data",
                    "tokenizer.json",
                    "config.json",
                    "tokenizer_config.json",
                    "special_tokens_map.json",
                ],
                local_files_only=False,
                force_download=path.is_dir(),
            )
        except Exception as exc:
            raise FairyError(
                "search_not_ready",
                "The fixed multilingual model could not be prepared; retry the explicit refresh",
                details={"model": MODEL_NAME, "revision": MODEL_REVISION},
            ) from exc
        if Path(downloaded) != path:
            raise FairyError(
                "search_not_ready",
                "The prepared model is not the fixed revision",
                details={"model": MODEL_NAME, "revision": MODEL_REVISION},
            )
        return {
            "model": MODEL_NAME,
            "revision": MODEL_REVISION,
            "path": str(self.model_dir()),
        }

    def _load(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from fastembed import TextEmbedding  # noqa: PLC0415 - lazy search dependency.
        except Exception as exc:
            raise FairyError("search_not_ready", "Prepare the locked FastEmbed dependency") from exc
        path = self.model_dir()
        try:
            self._model = TextEmbedding(
                model_name=MODEL_NAME,
                cache_dir=str(self.cache_dir),
                threads=self.threads,
                specific_model_path=str(path),
                local_files_only=True,
            )
        except Exception as exc:
            raise FairyError(
                "search_not_ready",
                "Prepare the fixed multilingual retrieval model before searching",
                details={"model": MODEL_NAME, "prepare_via": "assets search --refresh"},
            ) from exc
        return self._model

    def tokenizer_path(self) -> Path:
        return self.model_dir() / "tokenizer.json"

    def _normalize(self, vector: Any) -> list[float]:
        try:
            import numpy as np  # noqa: PLC0415 - lazy search dependency.
        except Exception as exc:
            raise FairyError("search_not_ready", "Prepare the locked numeric dependency") from exc
        values = np.asarray(vector, dtype=np.float32)
        if values.shape != (self.dimension,):
            raise FairyError("search_not_ready", "Embedding model produced an unexpected dimension")
        norm = float(np.linalg.norm(values))
        if not np.isfinite(values).all() or norm == 0:
            raise FairyError("search_not_ready", "Embedding model produced an invalid vector")
        return cast("list[float]", (values / norm).tolist())

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        return [self._normalize(vector) for vector in model.embed([f"passage: {text}" for text in texts])]

    def embed_query(self, text: str) -> list[float]:
        model = self._load()
        vector = next(iter(model.embed([f"query: {text}"])))
        return self._normalize(vector)


@dataclass(frozen=True)
class _Chunk:
    text: str
    locator: str


def _structural_parts(text: str) -> list[str]:
    return [part for part in re.split(r"\n\s*\n", text) if part.strip()]


def _chunks_for_text(text: str, tokenizer: Tokenizer, locator: str) -> list[_Chunk]:
    result = []
    for part in _structural_parts(text):
        for index, chunk in enumerate(tokenizer.split(part, CHUNK_TOKENS)):
            result.append(_Chunk(chunk, locator if index == 0 else f"{locator}#{index}"))
    return result


def chunks_from_package(package: dict[str, Any]) -> list[tuple[str, str]]:
    name = str(package.get("name", ""))
    summary = str(package.get("summary", ""))
    tags = " ".join(str(tag) for tag in package.get("tags", []))
    kind = str(package.get("kind", ""))
    scope = str(package.get("scope", ""))
    evidence = package.get("evidence", [])
    evidence_text = "\n".join(
        f"{item.get('source')}: {item.get('note')}"
        for item in evidence
        if isinstance(item, dict) and item.get("source") and item.get("note")
    )
    content = package.get("content")
    parts: list[tuple[str, str]] = []
    if kind == "workflow" and isinstance(content, dict):
        inputs = content.get("inputs", [])
        parameters = content.get("parameters", {})
        overview = (
            f"Name: {name}\nSummary: {summary}\nTags: {tags}\nKind: {kind}\nScope: {scope}\n"
            f"Inputs: {inputs}\nParameters: {parameters}\nEvidence:\n{evidence_text}"
        )
        parts.append((overview, "overview"))
        for index, step in enumerate(content.get("steps", [])):
            if isinstance(step, dict):
                parts.append(
                    (
                        (
                            f"Step {index + 1}: {step.get('instruction', '')}\n"
                            f"Completion: {step.get('done', '')}"
                        ),
                        f"content.steps.{index}",
                    )
                )
    else:
        body = content if isinstance(content, str) else canonical(content).decode("utf-8")
        parts.append(
            (
                (
                    f"Name: {name}\nSummary: {summary}\nTags: {tags}\nKind: {kind}\nScope: {scope}\n"
                    f"Evidence:\n{evidence_text}\nBody:\n{body}"
                ),
                "content",
            )
        )
    parts.extend(
        (f"{field}: {canonical(package[field]).decode('utf-8')}", field)
        for field in ("applicability", "dependencies", "invalidation")
        if field in package
    )
    return parts


def _chunks(package: dict[str, Any], tokenizer: Tokenizer) -> list[_Chunk]:
    result: list[_Chunk] = []
    for text, locator in chunks_from_package(package):
        result.extend(_chunks_for_text(text, tokenizer, locator))
    return result


class _EmbeddingCache:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, isolation_level=None)
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS embeddings "
            "(key TEXT PRIMARY KEY, profile TEXT NOT NULL, vector TEXT NOT NULL, dimension INTEGER NOT NULL)"
        )
        path.chmod(0o600)

    def close(self) -> None:
        self.connection.close()

    def get(self, key: str, profile: str) -> list[float] | None:
        row = self.connection.execute(
            "SELECT vector FROM embeddings WHERE key = ? AND profile = ?", (key, profile)
        ).fetchone()
        if row is None:
            return None
        value = json.loads(row[0])
        if not isinstance(value, list) or not all(isinstance(item, (int, float)) for item in value):
            raise FairyError("integrity", "Embedding cache entry is invalid")
        return [float(item) for item in value]

    def put(self, key: str, profile: str, vector: list[float]) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO embeddings(key, profile, vector, dimension) VALUES (?, ?, ?, ?)",
            (key, profile, json.dumps(vector, separators=(",", ":")), len(vector)),
        )


def _read_snapshot(store: Store) -> dict[str, Any]:
    path = store.home / "workshop.sqlite3"
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, isolation_level=None)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        generation = int(connection.execute("SELECT COALESCE(MAX(seq), 0) FROM asset_events").fetchone()[0])
        pointer_row = connection.execute("SELECT * FROM search_projection WHERE id = 1").fetchone()
        pointer = None if pointer_row is None else dict(pointer_row)
        heads = [
            dict(row)
            for row in connection.execute(
                "WITH active AS ("
                " SELECT a.ref, a.scope, a.name, a.version, a.kind, a.summary, a.tags,"
                " e.seq AS adoption, e.status"
                " FROM assets a JOIN asset_events e ON e.ref = a.ref"
                " WHERE e.status IN ('trial', 'stable')"
                " AND e.seq = (SELECT MAX(x.seq) FROM asset_events x WHERE x.ref = a.ref)),"
                " ranked AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY scope, name"
                " ORDER BY adoption DESC) AS rank FROM active)"
                " SELECT ref, scope, name, version, kind, summary, tags, adoption, status"
                " FROM ranked WHERE rank = 1 ORDER BY scope, name"
            ).fetchall()
        ]
        connection.execute("ROLLBACK")
        return {"generation": generation, "pointer": pointer, "heads": heads}
    finally:
        connection.close()


class SearchIndex:
    def __init__(
        self,
        store: Store,
        *,
        embedder: Embedder | None = None,
        tokenizer: Tokenizer | None = None,
        model_cache: Path | None = None,
        profile: dict[str, Any] | None = None,
    ) -> None:
        self.store = store
        self.profile = PROFILE if profile is None else profile
        self.profile_id = digest(canonical(self.profile))
        self.model_cache = (
            model_cache
            or Path(os.environ.get("ASTROFAIRY_MODEL_CACHE", str(store.home / "search" / "models")))
        ).resolve()
        self.embedder = embedder or FastEmbedder(self.model_cache)
        self._tokenizer = tokenizer
        self.search_dir = store.home / "search"

    def _not_ready(self, message: str, **details: Any) -> FairyError:
        return FairyError(
            "search_not_ready",
            message,
            details={**details, "prepare_via": "assets search --refresh"},
        )

    def _tokenizer_for_search(self) -> Tokenizer:
        if self._tokenizer is not None:
            return self._tokenizer
        provider = getattr(self.embedder, "tokenizer_path", None)
        path = provider() if callable(provider) else None
        if path is None or not Path(path).is_file():
            raise self._not_ready(
                "Prepare the fixed tokenizer before building the retrieval projection",
                model=MODEL_NAME,
            )
        self._tokenizer = FastTokenizer(path)
        return self._tokenizer

    @contextmanager
    def _lock(self) -> Iterator[None]:
        try:
            from filelock import FileLock, Timeout  # noqa: PLC0415 - lazy native lock.
        except Exception as exc:
            raise self._not_ready("Prepare the locked native file lock dependency") from exc
        self.search_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        lock = FileLock(
            str(self.search_dir / "projection.lock"),
            timeout=30,
            mode=0o600,
            fallback_to_soft=False,
            preserve_lock_file=True,
        )
        try:
            lock.acquire()
        except Timeout as exc:
            raise self._not_ready("Retrieval projection is busy; retry after the current process") from exc
        try:
            yield
        finally:
            lock.release()

    def _lance(self) -> Any:
        try:
            import lancedb  # noqa: PLC0415 - lazy search dependency.
        except Exception as exc:
            raise self._not_ready("Prepare the locked LanceDB dependency") from exc
        self.search_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        return lancedb.connect(str(self.search_dir / "lance"))

    def _table(self, pointer: dict[str, Any]) -> Any:
        try:
            table = self._lance().open_table(pointer["table_name"])
            table.checkout(int(pointer["lance_version"]))
            return table
        except Exception as exc:
            raise self._not_ready(
                "The recorded retrieval projection is unavailable; rebuild it",
                generation=pointer["generation"],
            ) from exc

    def _ensure_fts(self, table: Any) -> None:
        try:
            from lancedb.index import FTS  # noqa: PLC0415 - lazy search dependency.
        except Exception as exc:
            raise self._not_ready("Prepare the locked LanceDB FTS support") from exc
        indices = table.list_indices()
        if any("text" in str(getattr(index, "columns", index)) for index in indices):
            return
        table.create_index(
            "text",
            config=FTS(
                base_tokenizer="icu",
                stem=False,
                remove_stop_words=False,
                ascii_folding=False,
            ),
        )

    def refresh(self) -> dict[str, Any]:
        with self._lock():
            snapshot = _read_snapshot(self.store)
            generation = int(snapshot["generation"])
            heads = snapshot["heads"]
            pointer = snapshot["pointer"]
            if not heads:
                with self.store.transaction():
                    self.store.connection.execute("DELETE FROM search_projection WHERE id = 1")
                return {"generation": generation, "assets": 0, "chunks": 0, "ready": True}
            prepare = getattr(self.embedder, "prepare", None)
            prepared = prepare() if callable(prepare) else None
            tokenizer = self._tokenizer_for_search()
            chunks: list[tuple[str, str, _Chunk]] = []
            for head in heads:
                package = object_value(parse_json(self.store.get(head["ref"]).decode("utf-8")))
                chunks.extend((head["ref"], head["scope"], chunk) for chunk in _chunks(package, tokenizer))
            if not chunks:
                raise self._not_ready("The retrieval projection has no searchable content")
            if (
                pointer is not None
                and pointer["generation"] == generation
                and pointer["profile"] == self.profile_id
            ):
                try:
                    table = self._table(pointer)
                    if table.count_rows() == len(chunks):
                        self._ensure_fts(table)
                        with self.store.transaction():
                            self.store.set_projection(
                                epoch=pointer["epoch"],
                                generation=generation,
                                profile=self.profile_id,
                                table_name=pointer["table_name"],
                                lance_version=table.version,
                            )
                        return {
                            "generation": generation,
                            "assets": len(heads),
                            "chunks": len(chunks),
                            "ready": True,
                            "table": pointer["table_name"],
                            "version": table.version,
                            "model": prepared,
                        }
                except FairyError:
                    pass
            cache = _EmbeddingCache(self.search_dir / "embeddings.sqlite3")
            try:
                vectors: list[list[float]] = []
                pending: list[tuple[int, str]] = []
                for index, (_ref, _scope, chunk) in enumerate(chunks):
                    key = digest(canonical({"profile": self.profile_id, "text": chunk.text}))
                    cached = cache.get(key, self.profile_id)
                    if cached is not None and len(cached) == self.embedder.dimension:
                        vectors.append(cached)
                    else:
                        vectors.append([])
                        pending.append((index, chunk.text))
                if pending:
                    embedded = self.embedder.embed_passages([text for _index, text in pending])
                    if len(embedded) != len(pending):
                        raise self._not_ready("Embedding model returned an incomplete batch")
                    for (index, text), vector in zip(pending, embedded, strict=True):
                        if len(vector) != self.embedder.dimension:
                            raise self._not_ready("Embedding model produced an unexpected dimension")
                        vectors[index] = vector
                        key = digest(canonical({"profile": self.profile_id, "text": text}))
                        cache.put(key, self.profile_id, vector)
            finally:
                cache.close()
            rows = []
            for index, (ref, scope, chunk) in enumerate(chunks):
                head = next(item for item in heads if item["ref"] == ref)
                rows.append(
                    {
                        "asset_ref": ref,
                        "scope": scope,
                        "name": head["name"],
                        "kind": head["kind"],
                        "summary": head["summary"],
                        "version": int(head["version"]),
                        "text": chunk.text,
                        "locator": chunk.locator,
                        "chunk_index": index,
                        "source_generation": generation,
                        "profile": self.profile_id,
                        "vector": vectors[index],
                    }
                )
            db = self._lance()
            base = f"assets_g{generation}_{self.profile_id[:12]}"
            table_name = base
            try:
                table = db.open_table(table_name)
                if table.count_rows() != len(rows):
                    table_name = f"{base}_{uuid.uuid4().hex[:6]}"
                    table = db.create_table(table_name, data=rows)
                    self._ensure_fts(table)
            except Exception:  # noqa: BLE001 - any LanceDB reuse failure falls back to a new table.
                table = db.create_table(table_name, data=rows)
                self._ensure_fts(table)
            version = int(table.version)
            epoch = pointer["epoch"] if pointer is not None else uuid.uuid4().hex
            with self.store.transaction():
                self.store.set_projection(
                    epoch=epoch,
                    generation=generation,
                    profile=self.profile_id,
                    table_name=table_name,
                    lance_version=version,
                )
            return {
                "generation": generation,
                "assets": len(heads),
                "chunks": len(rows),
                "ready": True,
                "table": table_name,
                "version": version,
                "model": prepared,
            }

    def page(
        self,
        query: str,
        limit: int = LIMITS.search_default_limit,
        scope: str | None = None,
        kind: str | None = None,
        *,
        cursor: str | None = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        if refresh:
            self.refresh()
        if cursor is not None and refresh:
            raise FairyError("invalid", "A cursor cannot be combined with an explicit refresh")
        snapshot = _read_snapshot(self.store)
        generation = int(snapshot["generation"])
        heads = [
            head
            for head in snapshot["heads"]
            if (scope is None or head["scope"] == scope) and (kind is None or head["kind"] == kind)
        ]
        if not heads:
            return {"matches": [], "total": 0}
        pointer = snapshot["pointer"]
        if pointer is None:
            raise self._not_ready(
                "The retrieval projection has not been built for the current asset generation",
                generation=generation,
            )
        if int(pointer["generation"]) != generation:
            raise self._not_ready(
                "The retrieval projection is behind the current asset generation",
                generation=generation,
                projected_generation=pointer["generation"],
            )
        if pointer["profile"] != self.profile_id:
            raise self._not_ready(
                "The retrieval projection uses a different model profile",
                profile=self.profile_id,
            )
        identity = {
            "query": digest(query.encode("utf-8")),
            "scope": scope,
            "kind": kind,
            "generation": generation,
            "profile": pointer["profile"],
            "table": pointer["table_name"],
            "version": int(pointer["lance_version"]),
            "epoch": pointer["epoch"],
        }
        offset = 0 if cursor is None else offset_cursor(cursor, fields=identity)
        if not query.strip():
            total = len(heads)
            rows = [
                {
                    "ref": head["ref"],
                    "name": head["name"],
                    "scope": head["scope"],
                    "kind": head["kind"],
                    "summary": head["summary"],
                    "version": int(head["version"]),
                    "score": None,
                    "match": None,
                    "locator": None,
                    "source_generation": generation,
                    "profile": pointer["profile"],
                    "table_version": int(pointer["lance_version"]),
                    "index_epoch": pointer["epoch"],
                }
                for head in heads[offset : offset + limit]
            ]
        else:
            table = self._table(pointer)
            vector = self.embedder.embed_query(query)
            refs = [head["ref"] for head in heads]

            def quote(value: str) -> str:
                return "'" + value.replace("'", "''") + "'"

            clauses = [f"asset_ref IN ({','.join(quote(ref) for ref in refs)})"]
            if scope is not None:
                clauses.append(f"scope = {quote(scope)}")
            if kind is not None:
                clauses.append(f"kind = {quote(kind)}")

            def path_rows(searcher: Any) -> list[dict[str, Any]]:
                try:
                    return cast(
                        "list[dict[str, Any]]",
                        searcher.where(" AND ".join(clauses), prefilter=True).limit(CANDIDATE_POOL).to_list(),
                    )
                except Exception as exc:
                    raise self._not_ready(
                        "The retrieval projection could not complete the hybrid query",
                        generation=generation,
                    ) from exc

            full_text = path_rows(table.search(query, query_type="fts"))
            vectors = path_rows(table.search(vector, query_type="vector"))
            heads_by_ref = {head["ref"]: head for head in heads}
            fusion = self.profile["backend"]["fusion"]
            rrf_k = float(fusion["k"])
            weights = {
                "full_text": float(fusion["full_text_weight"]),
                "vector": float(fusion["vector_weight"]),
            }
            path_data: dict[str, tuple[list[str], dict[str, dict[str, Any]]]] = {}
            for path, raw_rows in (("full_text", full_text), ("vector", vectors)):
                ordered_refs: list[str] = []
                best_chunks: dict[str, dict[str, Any]] = {}
                for raw in raw_rows:
                    ref = raw.get("asset_ref")
                    if not isinstance(ref, str) or ref not in heads_by_ref:
                        continue
                    if ref not in best_chunks:
                        ordered_refs.append(ref)
                        best_chunks[ref] = raw
                path_data[path] = (ordered_refs, best_chunks)
            scores: dict[str, float] = {}
            for path in ("full_text", "vector"):
                for rank, ref in enumerate(path_data[path][0], 1):
                    scores[ref] = scores.get(ref, 0.0) + weights[path] / (rrf_k + rank)
            ordered: list[dict[str, Any]] = []
            for ref in sorted(
                scores,
                key=lambda item: (
                    -scores[item],
                    heads_by_ref[item]["name"],
                    heads_by_ref[item]["scope"],
                ),
            ):
                raw = path_data["full_text"][1].get(ref) or path_data["vector"][1][ref]
                ordered.append(
                    {
                        "ref": ref,
                        "name": heads_by_ref[ref]["name"],
                        "scope": heads_by_ref[ref]["scope"],
                        "kind": heads_by_ref[ref]["kind"],
                        "summary": heads_by_ref[ref]["summary"],
                        "version": int(heads_by_ref[ref]["version"]),
                        "score": scores[ref],
                        "match": raw.get("text"),
                        "locator": raw.get("locator"),
                        "source_generation": generation,
                        "profile": pointer["profile"],
                        "table_version": int(pointer["lance_version"]),
                        "index_epoch": pointer["epoch"],
                    }
                )
            total = len(ordered)
            rows = ordered[offset : offset + limit]
        result: dict[str, Any] = {"matches": rows, "total": total}
        if offset + len(rows) < total:
            result["next_cursor"] = encode_cursor({"offset": offset + len(rows), **identity})
        return result

    def search(
        self,
        query: str,
        limit: int = LIMITS.search_default_limit,
        scope: str | None = None,
        kind: str | None = None,
        *,
        refresh: bool = False,
    ) -> list[dict[str, Any]]:
        return cast(
            "list[dict[str, Any]]",
            self.page(query, limit=limit, scope=scope, kind=kind, refresh=refresh)["matches"],
        )


def status() -> dict[str, Any]:
    checks: dict[str, str | None] = {}
    for name in ("lancedb", "fastembed", "onnxruntime", "tokenizers", "numpy"):
        try:
            from importlib.metadata import version  # noqa: PLC0415 - diagnosis must not import search stacks.

            checks[name] = version(name)
        except Exception:  # noqa: BLE001 - an absent optional search dependency is reported, not raised.
            checks[name] = None
    return {
        "backend": "lancedb",
        "model": MODEL_NAME,
        "revision": MODEL_REVISION,
        "profile": PROFILE_ID,
        "dependencies": checks,
        "ready": all(value is not None for value in checks.values()),
    }


def invalidate(home: Path) -> None:
    search = home / "search"
    shutil.rmtree(search / "lance", ignore_errors=True)
    (search / "embeddings.sqlite3").unlink(missing_ok=True)
