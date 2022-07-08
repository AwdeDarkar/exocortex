"""
graph.py
Core graph processing.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

from types import SimpleNamespace

import numpy as np

from marko.element import Element
from marko.inline import InlineElement
from marko.block import Document

from graph_tool import Graph, GraphView

class RawString(InlineElement):
    """ It seems inconsistent to have bare strings alongside elements... """

    def __init__(self, string):
        self.string = string
    
    def __str__(self):
        return self.string
    
    def __repr__(self):
        return f"<Raw String \"{self.string}\">"

def iterate_document(document: Document):
    """
    Generator that iterates depth-first top-down through a marko Document,
    doing some light decoration for consistency.
    """
    for elem in _iterate_element_td_df(document):
        yield elem

def _iterate_element_td_df(element: Element, parent: Element = None):
    if isinstance(element, str):
        element = RawString(element)
    
    if not hasattr(element, "children"):
        element.children = []
    element.parent = parent
    yield element

    for child in element.children:
        for elem in _iterate_element_td_df(child, parent = element):
            yield elem

def filter_document(document: Document, filter_type, filter_func = lambda _: True):
    """
    Get all elements matching the type of the string or list of strings filter_type
    and passing the filter function.
    """
    matching = []
    for elem in iterate_document(document):
        if isinstance(filter_type, list):
            if elem.get_type() in filter_type and filter_func(elem):
                matching.append(elem)
        else:
            if elem.get_type() == filter_type and filter_func(elem):
                matching.append(elem)
    return matching

def collect_semlinks(doc_map):
    """ Collects all semantic-style links by document """
    for name, document in doc_map.items():
        doc_map[name] = {
            "document": document,
            "links": filter_document(
                document,
                ["Link", "InternalLink", "FormatLink"],
                lambda e: hasattr(e, "predicate")
            )
        }
    return doc_map


class DocumentGraph:
    """
    A graph of a collection of documents that represents links between documents
    as edges.
    """

    def __init__(self, doc_map):
        self.graph = Graph(directed=True)
        self.vertex_map = {}
        self.edge_map = {}
        self.doc_map = doc_map

        self._props = SimpleNamespace()
        self._props.graph = SimpleNamespace()
        self._props.vertex = SimpleNamespace()
        self._props.edge = SimpleNamespace()

        self._build_graph()

    def _build_graph(self):
        self.doc_map = collect_semlinks(self.doc_map)
        vertices = self.graph.add_vertex(len(self.doc_map))
        self._props.vertex.names = self.graph.new_vertex_property("string")
        self._props.vertex.documents = self.graph.new_vertex_property("python::object")

        for name, vertex in zip(self.doc_map.keys(), vertices):
            self.vertex_map[name] = vertex
            self._props.vertex.names[vertex] = name
            self._props.vertex.documents[vertex] = self.doc_map[name]["document"]

        self._props.edge.predicates = self.graph.new_edge_property("vector<string>")
        self._props.edge.element_lists = self.graph.new_edge_property("python::object")
        for name, dct in self.doc_map.items():
            for link in dct["links"]:
                obj = link.object
                print(f"{name} -[{link.predicate}]-> {obj}")
                if obj in self.doc_map:
                    edge = self.edge_map.get((name, obj))
                    if edge is None:
                        edge = self.graph.add_edge(self.vertex_map[name], self.vertex_map[obj])
                        self.edge_map[(name, obj)] = edge
                    self._props.edge.predicates[edge] = [
                        *self._props.edge.predicates[edge],
                        link.predicate,
                    ]
                    self._props.edge.element_lists[edge] = [
                        *(self._props.edge.element_lists[edge] or []),
                        link,
                    ]
                else:
                    pass # TODO handle link to nonexistent
    
    @property
    def vertices(self):
        return self.graph.vertices()

    def predicate_masked(self, predicate):
        """ Return a masked graph using only the given predicate """
        mask = np.array([predicate in plist for plist in graph._props.edge.predicates])
        return GraphView(self.graph, efilt=mask)

from process.parse_markdown import ast_map, apple
graph = DocumentGraph(ast_map)
check = None