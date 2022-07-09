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

from graph_tool import Graph, GraphView, load_graph

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

    @classmethod
    def load(cls, path):
        return cls(graph=load_graph(path, fmt="gt"))

    def __init__(self, doc_map=None, graph=None):
        if bool(doc_map) == bool(graph):
            raise Exception("Exactly one of `doc_map` or `graph` must be set!")
        self.graph = graph or Graph(directed=True)
        self.vertex_map = {}
        self.edge_map = {}

        class _edge_props():
            def __setattr__(_, name, value):
                self.graph.edge_properties[name] = value
            
            def __getattr__(_, name):
                return self.graph.edge_properties[name]

        class _vertex_props():
            def __setattr__(_, name, value):
                self.graph.vertex_properties[name] = value
            
            def __getattr__(_, name):
                return self.graph.vertex_properties[name]

        class _graph_props():
            def __setattr__(_, name, value):
                self.graph.graph_properties[name] = value
            
            def __getattr__(_, name):
                return self.graph.graph_properties[name]

        class _graph_props():
            """ Some convenience classes to make internal PropertyMaps easier """
            edge = _edge_props()
            vertex = _vertex_props()
            graph = _graph_props()

        self.props = _graph_props()

        if doc_map:
            self._build_graph(doc_map)
        else:
            self._populate_map()
        
    def _populate_map(self):
        for vertex in self.vertices:
            self.vertex_map[self.props.vertex.names[vertex]] = vertex
        for edge in self.edges:
            self.edge_map[(
                self.props.vertex.names[edge.source()],
                self.props.vertex.names[edge.target()]
            )] = edge

    def _build_graph(self, doc_map):
        doc_map = collect_semlinks(doc_map)
        vertices = self.graph.add_vertex(len(doc_map))
        self.props.vertex.names = self.graph.new_vertex_property("string")
        self.props.vertex.documents = self.graph.new_vertex_property("python::object")

        for name, vertex in zip(doc_map.keys(), vertices):
            self.vertex_map[name] = vertex
            self.props.vertex.names[vertex] = name
            self.props.vertex.documents[vertex] = doc_map[name]["document"]

        self.props.edge.predicates = self.graph.new_edge_property("vector<string>")
        self.props.edge.element_lists = self.graph.new_edge_property("python::object")
        for name, dct in doc_map.items():
            for link in dct["links"]:
                obj = link.object
                if obj in doc_map:
                    edge = self.edge_map.get((name, obj))
                    if edge is None:
                        edge = self.graph.add_edge(self.vertex_map[name], self.vertex_map[obj])
                        self.edge_map[(name, obj)] = edge
                    self.props.edge.predicates[edge] = [
                        *self.props.edge.predicates[edge],
                        link.predicate,
                    ]
                    self.props.edge.element_lists[edge] = [
                        *(self.props.edge.element_lists[edge] or []),
                        link,
                    ]
                else:
                    pass # TODO handle link to nonexistent

    @property
    def vertices(self):
        return self.graph.vertices()

    @property
    def edges(self):
        return self.graph.edges()

    def predicate_masked(self, predicate):
        """ Return a masked graph using only the given predicate """
        mask = np.array([predicate in plist for plist in graph.props.edge.predicates])
        return GraphView(self.graph, efilt=mask)
    
    def save(self, path):
        self.graph.save(path, fmt="gt")

from process.parse_markdown import ast_map, apple
graph = DocumentGraph(doc_map=ast_map)
check = None