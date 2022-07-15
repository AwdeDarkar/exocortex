"""
tree_transformer.py
Converting Marko ASTs to rich, easily-usable forms.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

from typing import List


class Node:
    """ AST Node """

    element_handlers = {}

    @classmethod
    def element_handler(cls, handler):
        cls.element_handlers[handler.__name__] = handler
        return cls
    
    @classmethod
    def get_custom_handler(cls, snake_type):
        if hasattr(cls, f"handle_{snake_type}"):
            return getattr(cls, f"handle_{snake_type}")
        return None
    
    @classmethod
    def convert_tree(cls, tree):
        if isinstance(tree, str):
            return tree
        handler = cls.get_custom_handler(tree.get_type(True))\
                  or Node.element_handlers.get(tree.get_type())
        if handler is None:
            print(f"No handler for type '{tree.get_type()}'")
            return Node(tree)
        return handler(tree)

    def __init__(self, element):
        self.element = element
        self.parent: Node = None
        self.children: List[Node] = []

        if hasattr(element, "children"):
            for c in element.children:
                child = self.convert_tree(c)
                if isinstance(child, Node):
                    child.parent = self
                self.children.append(child)
    
    def __lt__(self, node):
        """ TODO This is for dev only, remove when done """
        self.children.append(node)
    
    @property
    def root(self):
        if self.parent is None:
            return self
        return self.parent.root
    
    @property
    def nodes_top_down_depth_first(self):
        """ A Generator that does a top-down, depth-first iteration of this and child nodes """
        yield self
        for child in self.children:
            for n in child.nodes_top_down_depth_first:
                yield n

    @property
    def nodes_bottom_up_depth_first(self):
        """ A Generator that does a bottom-up, depth-first iteration of this and child nodes """
        for child in self.children:
            for n in child.nodes_bottom_depth_first:
                yield n
        yield self

    @property
    def nodes_top_down_breadth_first(self):
        """ A Generator that does a top-down, breadth-first iteration of this and child nodes """
        yield self
        has_more = not not self.children
        child_iterators = [c.nodes_top_down_breadth_first for c in self.children]
        while has_more:
            has_more = False
            for iterator in child_iterators:
                node = next(iterator)
                if node:
                    has_more = True
                    yield node


@Node.element_handler
class Document(Node):
    """ Root document """
    pass

@Node.element_handler
class Heading(Node):
    @classmethod
    def handle_raw_text(cls, txt):
        pass

from process.parse_markdown import apple

check = Node.convert_tree(apple.ast)