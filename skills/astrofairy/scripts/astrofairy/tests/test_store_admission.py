from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

from astrofairy import FairyError, Workshop
from astrofairy.tests._support import WorkshopTest

if TYPE_CHECKING:
    from collections.abc import Callable


def tracked_connection(
    connect: Callable[..., sqlite3.Connection], opened: list[sqlite3.Connection]
) -> Callable[..., sqlite3.Connection]:
    def track(*args: object, **kwargs: object) -> sqlite3.Connection:
        result = connect(*args, **kwargs)
        opened.append(result)
        return result

    return track


class StoreAdmissionTests(WorkshopTest):
    def test_unsupported_metadata_refused_before_any_schema_or_content_change(self) -> None:
        variants = [
            "",
            "CREATE TABLE metadata(version INTEGER NOT NULL)",
            "CREATE TABLE metadata(version INTEGER NOT NULL); INSERT INTO metadata VALUES (1)",
            "CREATE TABLE metadata(version INTEGER NOT NULL); INSERT INTO metadata VALUES (3)",
            "CREATE TABLE metadata(version INTEGER NOT NULL); INSERT INTO metadata VALUES (4)",
            "CREATE TABLE metadata(version INTEGER NOT NULL); INSERT INTO metadata VALUES (5)",
            "CREATE TABLE metadata(version INTEGER NOT NULL); INSERT INTO metadata VALUES (6)",
            "CREATE TABLE metadata(version INTEGER NOT NULL); INSERT INTO metadata VALUES (999)",
            "CREATE TABLE metadata(version INTEGER NOT NULL); INSERT INTO metadata VALUES (2),(2)",
            "CREATE TABLE metadata(wrong INTEGER NOT NULL); INSERT INTO metadata VALUES (2)",
            "CREATE TABLE metadata(version TEXT NOT NULL); INSERT INTO metadata VALUES ('2')",
            "CREATE TABLE metadata(version INTEGER); INSERT INTO metadata VALUES (NULL)",
        ]
        for index, sql in enumerate(variants):
            with self.subTest(sql=sql):
                home = Path(self.temporary.name) / str(index)
                home.mkdir()
                database = home / "workshop.sqlite3"
                connection = sqlite3.connect(database)
                connection.executescript(
                    "CREATE TABLE sentinel(value TEXT); INSERT INTO sentinel VALUES ('keep');"
                )
                connection.executescript(sql)
                connection.close()
                before = database.read_bytes()
                opened: list[sqlite3.Connection] = []
                track = tracked_connection(sqlite3.connect, opened)
                with (
                    patch("astrofairy._store.sqlite3.connect", side_effect=track),
                    self.assertRaises(FairyError) as caught,
                ):
                    Workshop(home)
                self.assertEqual(caught.exception.code, "version")
                self.assertEqual(database.read_bytes(), before)
                self.assertEqual(sorted(path.name for path in home.iterdir()), [database.name])
                for failed in opened:
                    with self.assertRaises(sqlite3.ProgrammingError):
                        failed.execute("SELECT 1")

    def test_existing_empty_file_is_not_a_new_store(self) -> None:
        home = Path(self.temporary.name) / "empty"
        home.mkdir()
        database = home / "workshop.sqlite3"
        database.touch()
        with self.assertRaises(FairyError):
            Workshop(home)
        self.assertEqual(database.read_bytes(), b"")

    def test_new_store_and_reopen_use_only_current_epoch(self) -> None:
        version = self.workshop.store.connection.execute("SELECT version FROM metadata").fetchall()
        self.assertEqual([tuple(row) for row in version], [(7,)])
        task = self.workshop.start("Current epoch")
        self.produce(task)
        with Workshop(self.home) as reopened:
            self.assertEqual(reopened.state(task).spec["goal"], "Current epoch")
