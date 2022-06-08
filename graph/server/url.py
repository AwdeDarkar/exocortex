"""
url.py
Semantic-triple-based URL parsing.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

from pathlib import Path

from lark import Lark
from lark.visitors import Visitor

from storage import PROJECT_ROOT


def make_parser():
    """ Creates a lark parser for the URL grammar """
    with (PROJECT_ROOT / "graph" / "server" / "pathparser.lark").open("r") as f:
        return Lark(f.read())


class VisitorResolver(Visitor):
    """ Resolves the parsed tree into semantic information """

    parser = make_parser()

    @classmethod
    def parse(cls, string):
        tree = cls.parser.parse(string)
        res = cls()
        res.visit_topdown(tree)
        return res

    def __init__(self):
        super().__init__()
        self.semantic_target = {}
        self.siteview = None
        self.viewmask = None
    
    @property
    def bundle(self):
        if self.siteview != "bundle":
            return None
        return self.semantic_target["object"]

    def path(self, tree):
        print(tree.data)
        print(tree.children)

    def site(self, tree):
        self.siteview = str(tree.children[0])

    def page(self, tree):
        print(f"Page: {tree.children[0]}")
        if "object" in self.semantic_target and self.semantic_target["object"] is None:
            self.semantic_target["object"] = str(tree.children[0])

    def view(self, tree):
        self.viewmask = tree.children[0]

    def cluster(self, tree):
        print(tree.data)
        print(tree.children[0])

    def semantic(self, tree):
        print(tree.data)
        print(tree.children)

    def predicate(self, tree):
        print(f"Predicate: {tree.data}")
        self.semantic_target["predicate"] = "ref" if not tree.children else str(tree.children[0])

    def subject(self, tree):
        print(tree.data)
        print(tree.children)

    def object(self, tree):
        print(f"Object: {tree.data}")
        self.semantic_target["object"] = None