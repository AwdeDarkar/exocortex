"""
test_source.py
Testing content source.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

from content_source import SourceHandler


class TestSource(SourceHandler):
    """
    A testing handler.

    With some longer documentation below.
    """

    NAME = "test"


class MoreTests(SourceHandler):
    """
    Have some longer documentation, with more words.

    With some longer documentation below.
    """

    NAME = "other"
