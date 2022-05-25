"""
source/__init__.py
Content source management utilities.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

from pathlib import Path
import importlib
import sys

from .content_source import SourceHandler

old_path = sys.path
sys.path = sys.path[:]
sys.path.insert(0, str(Path(__file__).parent))

for modpath in (Path(__file__).parent).iterdir():
    if modpath.is_file() and modpath.name not in ["__init__.py", "content_source.py"]:
        spec = importlib.util.spec_from_file_location(modpath.stem, modpath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        names = [name for name in module.__dict__ if not name.startswith("_")]
        globals().update({name: getattr(module, name) for name in names})

sys.path = old_path

SourceHandler.register_handlers()
