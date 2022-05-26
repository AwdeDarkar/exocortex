"""
raw_clips.py
Import web clips from a local directory

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

from pathlib import Path
from functools import cached_property

from content_source import SourceHandler


class MaoXianSource(SourceHandler):
    """
    Imports web clips from MaoXian.

    See <https://github.com/mika-cn/maoxian-web-clipper>.

    They are in a markdown format and have identifying information in a
    json block at the very top.
    """

    NAME = "webmx"
