from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import patch

from astrofairy import FairyError, Workshop
from astrofairy._cli import _parser, _run
from astrofairy._store import Store, sqlite_runtime
from astrofairy.tests._support import WorkshopTest


class SqliteRuntimeTests(WorkshopTest):
    def test_current_sqlite_probe_closes_connection_and_creates_no_persistent_state(self) -> None:
        connect = sqlite3.connect
        opened: list[sqlite3.Connection] = []

        def tracking(*args: Any, **kwargs: Any) -> sqlite3.Connection:
            connection = connect(*args, **kwargs)
            opened.append(connection)
            return connection

        with patch("astrofairy._store.sqlite3.connect", side_effect=tracking):
            status = sqlite_runtime()
        self.assertTrue(status["ready"])
        self.assertEqual(status["version"], sqlite3.sqlite_version)
        self.assertEqual(len(opened), 1)
        with self.assertRaises(sqlite3.ProgrammingError):
            opened[0].execute("SELECT 1")

    def test_missing_capabilities_refuse_before_new_or_existing_home_mutation(self) -> None:
        for failure in ("connect", "registration", "foreign_keys", "window", "materialized", "callback"):
            self.assert_missing_capability(failure)

    def assert_missing_capability(self, failure: str) -> None:
        connect = sqlite3.connect
        opened: list[sqlite3.Connection] = []

        class ImpairedConnection(sqlite3.Connection):
            def create_function(self, *args: Any, **kwargs: Any) -> None:
                if failure == "registration":
                    raise sqlite3.NotSupportedError("SYNTHETIC_SECRET")
                if failure == "callback":
                    args = (args[0], args[1], lambda *_: "wrong")
                super().create_function(*args, **kwargs)

            def execute(self, sql: str, parameters: Any = ()) -> sqlite3.Cursor:
                if failure == "foreign_keys" and sql == "PRAGMA foreign_keys":
                    return super().execute("SELECT 0")
                if failure == "window" and "ROW_NUMBER" in sql:
                    raise sqlite3.OperationalError("SYNTHETIC_SECRET")
                if failure == "materialized" and "AS MATERIALIZED" in sql:
                    raise sqlite3.OperationalError("SYNTHETIC_SECRET")
                return super().execute(sql, parameters)

        def impaired(*args: Any, **kwargs: Any) -> sqlite3.Connection:
            if failure == "connect":
                raise sqlite3.OperationalError("SYNTHETIC_SECRET")
            connection = connect(*args, **kwargs, factory=ImpairedConnection)
            opened.append(connection)
            return connection

        for existing in (False, True):
            with self.subTest(failure=failure, existing=existing):
                home = Path(self.temporary.name) / f"{failure}-{existing}"
                if existing:
                    home.mkdir(mode=0o750)
                    (home / "workshop.sqlite3").write_bytes(b"Preserve actual preexisting bytes")
                with patch("astrofairy._store.sqlite3.connect", side_effect=impaired):
                    doctor = _run(_parser().parse_args(["--home", str(home), "doctor"]))
                    self.assertFalse(doctor["ready"])
                    self.assertFalse(doctor["sqlite"]["ready"])
                    self.assertNotIn("SYNTHETIC_SECRET", str(doctor))
                    with self.assertRaises(FairyError) as caught:
                        Store(home)
                    self.assertEqual(caught.exception.code, "runtime_setup_required")
                    self.assertNotIn("SYNTHETIC_SECRET", str(caught.exception.as_dict()))
                if existing:
                    self.assertEqual(home.stat().st_mode & 0o777, 0o750)
                    self.assertEqual(
                        (home / "workshop.sqlite3").read_bytes(), b"Preserve actual preexisting bytes"
                    )
                    self.assertEqual(len(list(home.iterdir())), 1)
                else:
                    self.assertFalse(home.exists())
        for connection in opened:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT 1")

    def test_each_durable_connection_enforces_foreign_keys(self) -> None:
        with Workshop(self.home) as reopened:
            for workshop in (self.workshop, reopened):
                self.assertEqual(workshop.store.connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
                with self.assertRaises(sqlite3.IntegrityError):
                    workshop.store.connection.execute(
                        "INSERT INTO asset_events(ref,status,created) VALUES(?,?,?)",
                        ("0" * 64, "trial", "fixture"),
                    )
