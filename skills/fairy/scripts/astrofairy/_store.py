from __future__ import annotations

import hashlib
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from astrofairy._contracts import (
    MAX_CONTENT_BYTES,
    STREAM_CHUNK_BYTES,
    canonical,
    content_ref,
    digest,
    parse_json,
    strings,
)
from astrofairy._errors import FairyError
from astrofairy._limits import LIMITS

if TYPE_CHECKING:
    from collections.abc import Iterator

STORE_VERSION = 10


def _transaction_failure(
    exc: sqlite3.Error,
    *,
    stage: str,
    certainty: str,
    rollback: dict[str, Any] | None = None,
) -> FairyError:
    details: dict[str, Any] = {
        "transaction": stage,
        "commit": certainty,
        "committed": False if certainty == "not_committed" else "unknown",
        "sqlite_code": getattr(exc, "sqlite_errorcode", None),
        "sqlite_name": getattr(exc, "sqlite_errorname", None),
    }
    if rollback:
        details["rollback"] = rollback
    if certainty == "unknown":
        message = "The recorded-state transaction could not be confirmed; inspect before retrying"
    elif stage == "begin":
        message = "The recorded-state transaction could not begin"
    else:
        message = "The recorded-state transaction failed and was rolled back"
    return FairyError("storage_failed", message, details=details)


def _search_text(name: str, summary: str, tags: str) -> str:
    return " ".join([name, summary, *strings(parse_json(tags), "asset tags")]).casefold()


def _connect(database: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(database, isolation_level=None, timeout=LIMITS.sqlite_busy_seconds)
    try:
        connection.row_factory = sqlite3.Row
        connection.create_function("astrofairy_search_text", 3, _search_text, deterministic=True)
        connection.execute("PRAGMA foreign_keys = ON")
        row = connection.execute("PRAGMA foreign_keys").fetchone()
        if row is None or row[0] != 1:
            raise sqlite3.NotSupportedError("Foreign-key enforcement is unavailable")
    except BaseException:
        connection.close()
        raise
    return connection


def sqlite_runtime() -> dict[str, Any]:
    try:
        connection = _connect(":memory:")
        try:
            row = connection.execute(
                "WITH capability AS MATERIALIZED (SELECT astrofairy_search_text(?, ?, ?) AS text) "
                "SELECT ROW_NUMBER() OVER (), text FROM capability",
                ("probe", "Straße", canonical(["ÉTUDE"]).decode("utf-8")),
            ).fetchone()
            if row is None or tuple(row) != (1, "probe strasse étude"):
                raise sqlite3.NotSupportedError("SQLite capability control failed")
        finally:
            connection.close()
    except sqlite3.Error:
        return {
            "ready": False,
            "version": sqlite3.sqlite_version,
            "error": "runtime_setup_required",
            "message": (
                "Use a Python/SQLite build with window functions, materialized CTEs, "
                "deterministic callbacks and foreign keys"
            ),
        }
    return {"ready": True, "version": sqlite3.sqlite_version}


class Store:
    def __init__(self, home: Path) -> None:
        runtime = sqlite_runtime()
        if not runtime["ready"]:
            raise FairyError(runtime["error"], runtime["message"], details={"sqlite": runtime})
        self.home = home.resolve()
        if os.path.lexists(self.home / "restore.pending"):
            raise FairyError("incomplete_restore", "Restore did not finish; preserve this directory")
        self.home.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.home.chmod(0o700)
        database = self.home / "workshop.sqlite3"
        try:
            descriptor = os.open(database, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            fresh = False
        else:
            os.close(descriptor)
            fresh = True
        self.connection = _connect(database)
        try:
            if not fresh:
                self._require_version()
            self._initialize()
            database.chmod(0o600)
        except BaseException:
            self.connection.close()
            raise

    def _require_version(self) -> None:
        try:
            columns = self.connection.execute("PRAGMA table_info(metadata)").fetchall()
            if [(row["name"], row["type"], row["notnull"], row["pk"]) for row in columns] != [
                ("version", "INTEGER", 1, 0)
            ]:
                raise FairyError("version", "Unsupported store metadata; use a fresh home")
            rows = self.connection.execute("SELECT version, typeof(version) FROM metadata").fetchall()
            if len(rows) != 1 or tuple(rows[0]) != (STORE_VERSION, "integer"):
                raise FairyError("version", "Unsupported store version; use a fresh home")
        except sqlite3.DatabaseError as exc:
            raise FairyError("version", "Unreadable store metadata; use a fresh home") from exc

    def _initialize(self) -> None:
        self.connection.executescript("""
            BEGIN IMMEDIATE;
            CREATE TABLE IF NOT EXISTS metadata (version INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS blobs (ref TEXT PRIMARY KEY, data BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS events (
                task TEXT NOT NULL, seq INTEGER NOT NULL, kind TEXT NOT NULL,
                payload TEXT NOT NULL, created TEXT NOT NULL, previous TEXT NOT NULL,
                hash TEXT NOT NULL, PRIMARY KEY(task, seq)
            );
            CREATE TABLE IF NOT EXISTS assets (
                ref TEXT PRIMARY KEY REFERENCES blobs(ref), scope TEXT NOT NULL,
                name TEXT NOT NULL, version INTEGER NOT NULL, kind TEXT NOT NULL,
                summary TEXT NOT NULL, tags TEXT NOT NULL, base TEXT,
                UNIQUE(scope, name, version)
            );
            CREATE TABLE IF NOT EXISTS asset_events (
                seq INTEGER PRIMARY KEY, ref TEXT NOT NULL REFERENCES assets(ref),
                status TEXT NOT NULL, validation_task TEXT, created TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS asset_event_lookup ON asset_events(ref, seq DESC);
            CREATE TABLE IF NOT EXISTS search_projection (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                epoch TEXT NOT NULL, generation INTEGER NOT NULL,
                profile TEXT NOT NULL, table_name TEXT NOT NULL,
                lance_version INTEGER NOT NULL, updated TEXT NOT NULL
            );
        """)
        self.connection.execute(
            "INSERT INTO metadata SELECT ? WHERE NOT EXISTS (SELECT 1 FROM metadata)", (STORE_VERSION,)
        )
        self.connection.execute("COMMIT")

    def close(self) -> None:
        self.connection.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        try:
            self.connection.execute("BEGIN IMMEDIATE")
        except sqlite3.Error as exc:
            raise _transaction_failure(exc, stage="begin", certainty="not_committed") from exc
        try:
            yield
        except BaseException as exc:
            certainty = "not_committed"
            rollback: dict[str, Any] = {}
            try:
                self.connection.execute("ROLLBACK")
            except sqlite3.Error as retry:
                certainty = "unknown"
                rollback = {
                    "sqlite_code": getattr(retry, "sqlite_errorcode", None),
                    "sqlite_name": getattr(retry, "sqlite_errorname", None),
                }
            else:
                rollback = {"state": "rolled_back"}
            if isinstance(exc, FairyError):
                details = dict(exc.details or {})
                details.setdefault("commit", certainty)
                details.setdefault("committed", False if certainty == "not_committed" else "unknown")
                details.setdefault("rollback", rollback)
                exc.details = details
                raise
            if isinstance(exc, sqlite3.Error):
                raise _transaction_failure(exc, stage="body", certainty=certainty, rollback=rollback) from exc
            raise
        try:
            self.connection.execute("COMMIT")
        except sqlite3.Error as exc:
            active = self.connection.in_transaction
            certainty = "not_committed" if active else "unknown"
            commit_rollback: dict[str, Any] = {}
            if active:
                try:
                    self.connection.execute("ROLLBACK")
                except sqlite3.Error as retry:
                    certainty = "unknown"
                    commit_rollback = {
                        "sqlite_code": getattr(retry, "sqlite_errorcode", None),
                        "sqlite_name": getattr(retry, "sqlite_errorname", None),
                    }
                else:
                    commit_rollback = {"state": "rolled_back"}
            raise _transaction_failure(
                exc, stage="commit", certainty=certainty, rollback=commit_rollback
            ) from exc

    def put(self, data: bytes) -> str:
        if len(data) > LIMITS.blob_bytes:
            raise FairyError("limit", "Content exceeds the blob budget")
        ref = digest(data)
        self.connection.execute("INSERT OR IGNORE INTO blobs VALUES (?, ?)", (ref, data))
        return ref

    def get(self, ref: str) -> bytes:
        row = self.connection.execute("SELECT data FROM blobs WHERE ref = ?", (ref,)).fetchone()
        if row is None:
            raise FairyError("missing", "Unknown content reference")
        data = bytes(row[0])
        if digest(data) != ref:
            raise FairyError("integrity", "Stored content digest does not match")
        return data

    def length(self, ref: str) -> int:
        row = self.connection.execute("SELECT length(data) FROM blobs WHERE ref = ?", (ref,)).fetchone()
        if row is None:
            raise FairyError("missing", "Unknown content reference")
        return int(row[0])

    def hash_ref(self, ref: str) -> str:
        row = self.connection.execute(
            "SELECT rowid, length(data) FROM blobs WHERE ref = ?", (ref,)
        ).fetchone()
        if row is None:
            raise FairyError("missing", "Unknown content reference")
        digest_state = hashlib.sha256()
        size = 0
        with self.connection.blobopen("blobs", "data", int(row[0])) as blob:
            while chunk := blob.read(LIMITS.stream_chunk_bytes):
                size += len(chunk)
                digest_state.update(chunk)
        if size != int(row[1]) or digest_state.hexdigest() != ref:
            raise FairyError("integrity", "Stored content digest does not match")
        return ref

    def projection(self) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM search_projection WHERE id = 1").fetchone()
        return None if row is None else dict(row)

    def set_projection(
        self,
        *,
        epoch: str,
        generation: int,
        profile: str,
        table_name: str,
        lance_version: int,
    ) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO search_projection"
            "(id, epoch, generation, profile, table_name, lance_version, updated) "
            "VALUES (1, ?, ?, ?, ?, ?, ?)",
            (
                epoch,
                generation,
                profile,
                table_name,
                lance_version,
                datetime.now(UTC).isoformat(),
            ),
        )

    def hash_file(self, path: Path, *, limit: int = MAX_CONTENT_BYTES) -> tuple[str, int]:
        digest_state = hashlib.sha256()
        size = 0
        with path.open("rb") as source:
            while chunk := source.read(STREAM_CHUNK_BYTES):
                size += len(chunk)
                if size > limit:
                    raise FairyError("limit", "Content exceeds its byte budget")
                digest_state.update(chunk)
        return digest_state.hexdigest(), size

    def put_file(self, path: Path, *, limit: int = MAX_CONTENT_BYTES) -> tuple[str, int]:
        if self.connection.in_transaction:
            return self._put_file(path, limit)
        with self.transaction():
            return self._put_file(path, limit)

    def _put_file(self, path: Path, limit: int) -> tuple[str, int]:
        descriptor, temporary = tempfile.mkstemp(prefix=".capture-", dir=self.home)
        digest_state = hashlib.sha256()
        size = 0
        try:
            with os.fdopen(descriptor, "wb") as output, path.open("rb") as source:
                while chunk := source.read(STREAM_CHUNK_BYTES):
                    size += len(chunk)
                    if size > limit:
                        raise FairyError("limit", "Content exceeds its byte budget")
                    digest_state.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            ref = digest_state.hexdigest()
            existing = self.connection.execute(
                "SELECT rowid, length(data) FROM blobs WHERE ref = ?", (ref,)
            ).fetchone()
            if existing is None:
                self.connection.execute("INSERT INTO blobs(ref, data) VALUES (?, zeroblob(?))", (ref, size))
                row = self.connection.execute("SELECT rowid FROM blobs WHERE ref = ?", (ref,)).fetchone()
                if row is None:
                    raise FairyError("integrity", "Captured content row was not created")
                rowid = int(row[0])
            else:
                if int(existing[1]) != size:
                    raise FairyError("integrity", "Stored content length does not match its digest")
                rowid = int(existing[0])
            with (
                Path(temporary).open("rb") as source,
                self.connection.blobopen("blobs", "data", rowid) as target,
            ):
                while chunk := source.read(STREAM_CHUNK_BYTES):
                    target.write(chunk)
            return ref, size
        finally:
            Path(temporary).unlink(missing_ok=True)

    def copy_to_file(self, ref: str, target: Path) -> int:
        content_ref(ref)
        row = self.connection.execute(
            "SELECT rowid, length(data) FROM blobs WHERE ref = ?", (ref,)
        ).fetchone()
        if row is None:
            raise FairyError("missing", "Unknown content reference")
        size = int(row[1])
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary = tempfile.mkstemp(prefix=".copy-", dir=target.parent)
        digest_state = hashlib.sha256()
        try:
            with (
                os.fdopen(descriptor, "wb") as output,
                self.connection.blobopen("blobs", "data", row[0], readonly=True) as source,
            ):
                while chunk := source.read(STREAM_CHUNK_BYTES):
                    digest_state.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if digest_state.hexdigest() != ref:
                raise FairyError("integrity", "Copied content digest does not match")
            Path(temporary).chmod(0o600)
            Path(temporary).replace(target)
            target.chmod(0o600)
            return size
        finally:
            Path(temporary).unlink(missing_ok=True)

    def events(self, task: str) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT * FROM events WHERE task = ? ORDER BY seq", (task,)).fetchall()
        previous = ""
        events = []
        for seq, row in enumerate(rows, 1):
            event = {
                "task": task,
                "seq": row["seq"],
                "kind": row["kind"],
                "payload": parse_json(row["payload"]),
                "created": row["created"],
                "previous": row["previous"],
            }
            if row["seq"] != seq or row["previous"] != previous or digest(canonical(event)) != row["hash"]:
                raise FairyError("integrity", "Event chain verification failed")
            events.append(event)
            previous = row["hash"]
        return events

    def append(self, task: str, kind: str, payload: dict[str, Any], expected_seq: int) -> None:
        row = self.connection.execute(
            "SELECT seq, hash FROM events WHERE task = ? ORDER BY seq DESC LIMIT 1", (task,)
        ).fetchone()
        current = row["seq"] if row else 0
        if current != expected_seq:
            raise FairyError("conflict", "Task changed; inspect before retrying")
        event = {
            "task": task,
            "seq": current + 1,
            "kind": kind,
            "payload": payload,
            "created": datetime.now(UTC).isoformat(),
            "previous": row["hash"] if row else "",
        }
        self.connection.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                task,
                event["seq"],
                kind,
                canonical(payload).decode("utf-8"),
                event["created"],
                event["previous"],
                digest(canonical(event)),
            ),
        )

    def tasks(self) -> list[str]:
        return [row[0] for row in self.connection.execute("SELECT DISTINCT task FROM events ORDER BY task")]
