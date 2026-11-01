from __future__ import annotations

import io
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from astrofairy._cli import main
from astrofairy.tests._support import ROOT, WorkshopTest


class StorageErrorTests(WorkshopTest):
    def envelope(self, error: sqlite3.Error) -> dict[str, object]:
        stream = io.BytesIO()
        stdout = io.TextIOWrapper(stream, encoding="utf-8")
        with patch("astrofairy._cli._run", side_effect=error), patch("astrofairy._cli.sys.stdout", stdout):
            status = main(["schema"])
        self.assertEqual(status, 1)
        data = stream.getvalue()
        self.assertNotIn(b"sensitive", data)
        self.assertNotIn(b"confidential", data)
        result = json.loads(data)
        self.assertEqual(result["error"], "storage_failed")
        self.assertEqual(result["sqlite_code"], getattr(error, "sqlite_errorcode", None))
        self.assertEqual(result["sqlite_name"], getattr(error, "sqlite_errorname", None))
        return result

    def test_current_format_wrong_events_schema_returns_json_without_traceback(self) -> None:
        self.workshop.store.connection.executescript("DROP TABLE events; CREATE TABLE events(sensitive TEXT)")
        result = subprocess.run(
            [sys.executable, "-B", "-m", "astrofairy", "--home", str(self.home), "inspect", "fixture"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        data = json.loads(result.stdout)
        self.assertEqual((data["error"], data["sqlite_name"]), ("storage_failed", "SQLITE_ERROR"))
        self.assertNotIn("sensitive", result.stdout)
        self.assertNotIn("no such column", result.stdout)

    def test_actual_sqlite_errors_and_missing_optional_diagnostics(self) -> None:
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        for sql in (
            "SELECT confidential FROM absent",
            (
                "CREATE TABLE sensitive(value TEXT UNIQUE);"
                "INSERT INTO sensitive VALUES ('confidential');INSERT INTO sensitive VALUES ('confidential')"
            ),
        ):
            with self.subTest(sql=sql):
                try:
                    connection.executescript(sql)
                except sqlite3.Error as exc:
                    self.envelope(exc)
                else:
                    self.fail("Expected a real SQLite failure")
        result = self.envelope(sqlite3.OperationalError("sensitive exception without SQLite attributes"))
        self.assertIsNone(result["sqlite_code"])
        self.assertIsNone(result["sqlite_name"])

    def test_real_readonly_and_busy_errors_are_preserved_as_diagnostics(self) -> None:
        database = Path(self.temporary.name) / "diagnostic.sqlite3"
        writer = sqlite3.connect(database)
        self.addCleanup(writer.close)
        writer.execute("CREATE TABLE sensitive(value TEXT)")
        reader = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
        self.addCleanup(reader.close)
        with self.assertRaises(sqlite3.OperationalError) as readonly:
            reader.execute("INSERT INTO sensitive VALUES ('confidential')")
        self.assertEqual(self.envelope(readonly.exception)["sqlite_name"], "SQLITE_READONLY")
        writer.execute("BEGIN IMMEDIATE")
        competing = sqlite3.connect(database, timeout=0)
        self.addCleanup(competing.close)
        with self.assertRaises(sqlite3.OperationalError) as busy:
            competing.execute("INSERT INTO sensitive VALUES ('confidential')")
        self.assertEqual(self.envelope(busy.exception)["sqlite_name"], "SQLITE_BUSY")
        writer.rollback()
