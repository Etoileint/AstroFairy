from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from astrofairy._contracts import MAX_BLOB_BYTES, canonical, digest, parse_json, strings
from astrofairy._errors import FairyError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

STORE_VERSION = 7


def _search_text(name: str, summary: str, tags: str) -> str:
    return " ".join([name, summary, *strings(parse_json(tags), "asset tags")]).casefold()


def _connect(database: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(database, isolation_level=None, timeout=10)
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
        """)
        self.connection.execute(
            "INSERT INTO metadata SELECT ? WHERE NOT EXISTS (SELECT 1 FROM metadata)", (STORE_VERSION,)
        )
        self.connection.execute("COMMIT")

    def close(self) -> None:
        self.connection.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.connection.execute("COMMIT")
        except BaseException:
            self.connection.execute("ROLLBACK")
            raise

    def put(self, data: bytes) -> str:
        if len(data) > MAX_BLOB_BYTES:
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
