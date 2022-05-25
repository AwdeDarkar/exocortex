"""
storage.py
Global storage management for configuration and persistent memory.

This is _not_ intended for site or content storage.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

from pathlib import Path
import json


STORAGE_ROOT = Path("~/global_projects/.storage/ex").expanduser()


class PersistentDict(dict):
    """
    A dictionary that serializes to JSON in the background.
    """

    def __init__(self, name):
        self.path = STORAGE_ROOT / f"{name}.json"
        self.paused = True
        if self.path.exists():
            with self.path.open("r") as f:
                self.update(json.load(f))
        self.paused = False

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.write()

    def __delitem__(self, key):
        super().__delitem__(key)
        self.write()

    def write(self):
        if not self.paused:
            with self.path.open("w") as f:
                json.dump(self, f)
