from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from astrofairy._contracts import MAX_BLOB_BYTES, canonical, digest, parse_json
from astrofairy._errors import FairyError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class Store:
    def __init__(self, home: Path) -> None:
        self.home = home.resolve()
        self.home.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.home.chmod(0o700)
        self.connection = sqlite3.connect(self.home / "workshop.sqlite3", isolation_level=None, timeout=10)
        (self.home / "workshop.sqlite3").chmod(0o600)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (version INTEGER NOT NULL);
            INSERT INTO metadata SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM metadata);
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
        if self.connection.execute("SELECT version FROM metadata").fetchone()[0] != 1:
            raise FairyError("version", "Unsupported store version")

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
