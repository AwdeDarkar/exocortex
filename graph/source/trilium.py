"""
trilium.py
Import material from trilium.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

from pathlib import Path
from functools import cached_property
import sqlite3

from content_source import SourceHandler


class TriliumSource(SourceHandler):
    """
    Imports things from the trilium document database.

    [Trilium](https://github.com/zadam/trilium) is a self-hosted knowledgebase
    centered around hierarchical notes.

    Notes are stored in a [sqlite database](https://github.com/zadam/trilium/wiki/Document).
    """

    NAME = "trilium"

    def __init__(self):
        self.data_dir = Path("~/bench/carbon/modules/trilium/data").expanduser()

    @cached_property
    def connection(self):
        return sqlite3.connect(
            f"file:{self.data_dir / 'document.db'}?mode=ro",
            uri=True
        )

    @cached_property
    def cursor(self):
        return self.connection.cursor()

    @cached_property
    def tables(self):
        res = self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        )
        return {
            v[0]: {
                "columns": self.table_columns(v[0]),
                "row_count": self.table_count(v[0]),
            }
            for v in res.fetchall()
        }

    @cached_property
    def options(self):
        res = self.cursor.execute(
            "SELECT name, value FROM options;"
        )
        return {key: value for key, value in res.fetchall()}

    def load(self, table, cols="*"):
        res = self.cursor.execute(
            f"SELECT {', '.join(cols)} FROM {table};"
        )
        cols = [c[0] for c in res.description]
        vals = res.fetchone()
        while vals is not None:
            yield {col: val for col, val in zip(cols, vals)}
            vals = res.fetchone()

    def load_notes(self):
        res = self.cursor.execute(
                """
                SELECT notes.noteId, title, content FROM notes
                INNER JOIN note_contents on notes.noteId = note_contents.noteId
                ;
                """
        )
        cols = [c[0] for c in res.description]
        vals = res.fetchone()
        while vals is not None:
            yield {col: val for col, val in zip(cols, vals)}
            vals = res.fetchone()

    def table_columns(self, table):
        res = self.cursor.execute(
            f"SELECT * FROM {table} LIMIT 1;"
        )
        return [c[0] for c in res.description]

    def table_count(self, table):
        res = self.cursor.execute(
            f"SELECT COUNT(*) FROM {table};"
        )
        return res.fetchall()[0][0]
