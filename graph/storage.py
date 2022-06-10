"""
storage.py
Global storage management for configuration and persistent memory.

This is _not_ intended for site or content storage.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

from pathlib import Path
from datetime import datetime
from collections import namedtuple
from functools import cached_property
import json


class RichPath(type(Path())):
    """
    A version of Path that includes additional helpful properties.
    """

    Times = namedtuple("Times", ["created", "modified", "accessed"])

    @cached_property
    def times(self):
        """
        Get modified, accessed, and created times as python datetime objects.

        WARNING: 'Created' time is platform dependent and may not be accurate on unix.
        """
        if self.is_dir():
            max_ctime = max(self.rglob("*"), key=lambda f: f.stat().st_ctime).stat().st_ctime
            max_mtime = max(self.rglob("*"), key=lambda f: f.stat().st_mtime).stat().st_mtime
            max_atime = max(self.rglob("*"), key=lambda f: f.stat().st_atime).stat().st_atime
        try:
            stat = self.stat()
            return RichPath.Times(
                created=datetime.fromtimestamp(max(stat.st_ctime, max_ctime)),
                modified=datetime.fromtimestamp(max(stat.st_mtime, max_mtime)),
                accessed=datetime.fromtimestamp(max(stat.st_atime, max_atime)),
            )
        except FileNotFoundError:
            return RichPath.Times(created=None, modified=None, accessed=None)
    
    @cached_property
    def size(self):
        """
        Get the size of the file in bytes.
        """
        return self.stat().st_size


STORAGE_ROOT = RichPath("~/global_projects/.storage/ex").expanduser()
""" TODO Extract this to a config """

EXOCORTEX_ROOT = RichPath(__file__).parent.parent.parent
PROJECT_ROOT = EXOCORTEX_ROOT / "exocortex"
CONTENT_ROOT = EXOCORTEX_ROOT / "content"

SITE_TEMPLATE = PROJECT_ROOT / "template-site"
SITES_ROOT = PROJECT_ROOT / "sites"
SITES_FILE = PROJECT_ROOT / "graph" / "server" / "sites.py"

SNIPPETS_TEMPLATE = PROJECT_ROOT / "template-py-snippets"


class PersistentDict(dict):
    """
    A dictionary that serializes to JSON in the background.
    """

    def __init__(self, name=None, parent=None, init={}):
        self.name = name
        self.path = STORAGE_ROOT / f"{self.name}.json"
        self.parent = parent

        if self.parent is None:
            self.paused = True
            if self.path.exists():
                with self.path.open("r") as f:
                    self.update(json.load(f))
            self.paused = False

        if init:
            self.update(init)

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            value = PersistentDict(parent=self, init=value)
        super().__setitem__(key, value)
        self.write()

    def __delitem__(self, key):
        super().__delitem__(key)
        self.write()

    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).items():
            self[key] = value

    def write(self):
        if self.parent:
            self.parent.write()

        if self.name and not self.paused:
            with self.path.open("w") as f:
                json.dump(self, f)
