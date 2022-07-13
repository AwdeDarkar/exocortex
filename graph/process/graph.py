"""
graph.py
Core graph processing.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

from collections import namedtuple

from uuid import uuid4
import toml

import numpy as np

from marko.element import Element
from marko.inline import InlineElement
from marko.block import Document

from graph_tool import (
    Graph, GraphView, load_graph,
    draw, centrality, topology, clustering,
)
from graph_tool.draw import graph_draw

import graphene
from graphene import ObjectType, List, Field, Schema

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


class DocumentVertex:
    """
    A convenience wrapper around vertices in a DocumentGraph that makes
    properties easier to access and use.
    """

    def __init__(self, docgraph, vertex):
        self.docgraph = docgraph
        self.vertex = vertex

        self.in_degree = self.vertex.in_degree
        self.out_degree = self.vertex.out_degree
        self.is_valid = self.vertex.is_valid
    
    def __getitem__(self, propname):
        return self.docgraph.graph.vertex_properties[propname][self.vertex]
    
    def __setitem__(self, propname, value):
        self.docgraph.graph.vertex_properties[propname][self.vertex] = value
    
    def _wrap_vertex_iterator(self, iterator):
        for vertex in iterator:
            yield DocumentVertex(self.docgraph, vertex)

    def _wrap_edge_iterator(self, iterator):
        for edge in iterator:
            yield DocumentEdge(self.docgraph, edge)

    def __str__(self):
        return self.name
    
    def __repr__(self):
        return f"<DocumentVertex '{self}'>"
    
    @property
    def uuid(self):
        return self["uuids"]

    @property
    def name(self):
        return self["names"]
    
    @name.setter
    def name(self, value):
        self["names"] = value
    
    @property
    def document(self):
        return self["documents"]
    
    @document.setter
    def document(self, value):
        self["documents"] = value
    
    def all_edges(self):
        return self._wrap_edge_iterator(self.vertex.all_edges())
    
    def in_edges(self):
        return self._wrap_edge_iterator(self.vertex.in_edges())
    
    def out_edges(self):
        return self._wrap_edge_iterator(self.vertex.out_edges())
    
    def all_neighbors(self):
        return self._wrap_vertex_iterator(self.vertex.all_neighbors())
    
    def in_neighbors(self):
        return self._wrap_vertex_iterator(self.vertex.in_neighbors())
    
    def out_neighbors(self):
        return self._wrap_vertex_iterator(self.vertex.out_neighbors())
    
    def shortest_path_to(self, other, **kwargs):
        vertices, edges = topology.shortest_path(
            self.docgraph.graph,
            self.vertex,
            other.vertex,
            **kwargs,
        )
        return (
            [DocumentVertex(self.docgraph, v) for v in vertices],
            [DocumentEdge(self.docgraph, e) for e in edges],
        )


class DocumentEdge:
    """
    A convenience wrapper around edges in a DocumentGraph
    """

    def __init__(self, docgraph, edge):
        self.docgraph = docgraph
        self.edge = edge

        self.is_valid = self.edge.is_valid

    def __getitem__(self, propname):
        return self.docgraph.graph.edge_properties[propname][self.edge]
    
    def __setitem__(self, propname, value):
        self.docgraph.graph.edge_properties[propname][self.edge] = value

    def __str__(self):
        return f"'{self.source().name}' -[{','.join(self.predicates)}]-> '{self.target().name}'"
    
    def __repr__(self):
        return f"<DocumentEdge \"{self}\">"
    
    @property
    def predicates(self):
        return self["predicates"]
    
    @property
    def elements(self):
        return {
            pred: elem
            for pred, elem in zip(
                self.predicates,
                self["element_lists"]
            )
        }

    def source(self):
        return DocumentVertex(self.docgraph, self.edge.source())

    def target(self):
        return DocumentVertex(self.docgraph, self.edge.target())
    

class DocumentGraph:
    """
    A graph of a collection of documents that represents links between documents
    as edges.
    """

    calc_functions = {}

    @classmethod
    def calc_function(cls, f):
        cls.calc_functions[f.__name__] = f
        return f

    @classmethod
    def _setup_calculations(cls):
        cls.calc_function(centrality.pagerank)

    @classmethod
    def load(cls, path):
        return cls(graph=load_graph(path, fmt="gt"))

    def __init__(self, doc_map=None, graph=None):
        self.__class__._setup_calculations()
        if bool(doc_map) == bool(graph):
            raise Exception("Exactly one of `doc_map` or `graph` must be set!")
        self.graph = graph or Graph(directed=True)
        self.vertex_map = {}
        self.vertex_id_map = {}
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
            self.vertex_map[vertex.name] = vertex.vertex
            self.vertex_id_map[vertex.uuid] = vertex.vertex
        for edge in self.edges:
            self.edge_map[(
                edge.source().name,
                edge.target().name,
            )] = edge

    def _build_graph(self, doc_map):
        doc_map = collect_semlinks(doc_map)
        vertices = self.graph.add_vertex(len(doc_map))
        self.props.vertex.names = self.graph.new_vertex_property("string")
        self.props.vertex.uuids = self.graph.new_vertex_property("string")
        self.props.vertex.documents = self.graph.new_vertex_property("python::object")

        for name, vertex in zip(doc_map.keys(), vertices):
            self.vertex_map[name] = vertex
            self.props.vertex.names[vertex] = name
            self.props.vertex.uuids[vertex] = uuid4()  # TODO we need bidirection persistence...
            self.props.vertex.documents[vertex] = doc_map[name]["document"]

            self.vertex_id_map[self.props.vertex.uuids[vertex]] = vertex

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
        for vertex in self.graph.vertices():
            yield DocumentVertex(self, vertex)
    
    def __getitem__(self, name):
        return DocumentVertex(self, self.vertex_map[name])
    
    def get_vertex_by_id(self, id):
        return DocumentVertex(self, self.vertex_id_map[id])

    @property
    def edges(self):
        for edge in self.graph.edges():
            yield DocumentEdge(self, edge)
    
    @property
    def is_dag(self):
        return topology.is_DAG(self.graph)
    
    @property
    def is_planar(self):
        return topology.is_planar(self.graph)
    
    @property
    def is_tree(self):
        pass
    
    @property
    def is_connected(self):
        pass

    @property
    def disconnected_subgraphs(self):
        pass
    
    def calculate_values(self, recipes):
        for predicate, pred_recipes in recipes["predicates"].items():
            pgraph = self.predicate_masked(predicate, raw=False)
            for recipe, kwargs in pred_recipes.items():
                res = None
                if kwargs == True:
                    res = pgraph.calculate(recipe)
                elif kwargs:
                    pass

    @property
    def predicate_counts(self):
        """ Get a dictionary of all predicates with the number of times they appear """
        counts = {}
        for edge in self.edges:
            for predicate in self.props.edge.predicates[edge]:
                counts[predicate] = counts.get(predicate, 0) + 1
        return counts
    
    @property
    def predicates(self):
        """ Get a list of all unique predicates """
        return list(self.predicate_counts.keys())
    
    def predicate_masked(self, predicate, raw=False):
        """ Return a masked graph using only the given predicate(s) """
        if isinstance(predicate, list):
            mask = np.array(
                [bool(set(predicate) & set(plist)) for plist in self.props.edge.predicates]
            )
        else:
            mask = np.array([predicate in plist for plist in self.props.edge.predicates])
        if raw:
            return GraphView(self.graph, efilt=mask)
        else:
            return DocumentGraph(graph=GraphView(self.graph, efilt=mask))
    
    @property
    def pgraph_in(self):
        """ Convenience masked graph filtering on the 'in' predicate """
        return self.predicate_masked("in", raw=False)
    
    @property
    def pgraph_ref(self):
        """ Convenience masked graph filtering on the 'ref' predicate """
        return self.predicate_masked("ref", raw=False)
    
    @property
    def pgraph_embed(self):
        """ Convenience masked graph filtering on the 'embed' predicate """
        return self.predicate_masked("embed", raw=False)
    
    @property
    def pgraph_media(self):
        """ Convenience masked graph filtering on the 'media' predicate """
        return self.predicate_masked("media", raw=False)
    
    @property
    def pgraph_tags(self):
        """ Convenience masked graph filtering on the tagging predicates """
        return self.predicate_masked(["is", "has", "about", "uses", "tag"], raw=False)
    
    def vertices_in_from(self, vertex):
        yield vertex
        for neighboor in vertex.in_neighbors():
            for subv in self.vertices_in_from(neighboor):
                yield subv
    
    def subgraph_around(self, root, include_root=True):
        """ Uses the 'in' predicate to get the subgraph around a root """
        ingraph = self.pgraph_in
        root = ingraph[root.name]
        gen = (v.vertex for v in ingraph.vertices_in_from(root))
        if include_root:
            selected = set(gen)
        else:
            next(gen)
            selected = set(gen)
        return DocumentGraph(graph=GraphView(self.graph, vfilt=lambda v: v in selected))
    
    def save(self, path):
        self.graph.save(path, fmt="gt")
    
    def layout(self, kind, **kwargs):
        if kind == "sfdp":
            return draw.sfdp_layout(self.graph, **kwargs)
        elif kind == "planar":
            return draw.planar_layout(self.graph, **kwargs)
        elif kind == "fr":
            return draw.fruchterman_reingold_layout(self.graph, **kwargs)
        elif kind == "arf":
            return draw.arf_layout(self.graph, **kwargs)
        elif kind == "radial_tree":
            return draw.radial_tree_layout(self.graph, **kwargs)
        elif kind == "random":
            return draw.random_layout(self.graph, **kwargs)
        else:
            raise Exception(f"Unknown layout '{kind}'")
    
    def calculate(self, name, **kwargs):
        if name not in self.__class__.calc_functions:
            raise Exception(f"Unknown calculation '{name}'")
        return self.__class__.calc_functions[name](self.graph, **kwargs)

    def draw(self, size_calc=None, **kwargs):
        vsize = 24
        if size_calc:
            vsize = self.calculate(size_calc)
        graph_draw(
            self.graph,
            vertex_text=self.props.vertex.names,
            vertex_text_position=-1.1,
            vertex_size=vsize,

            edge_text=self.props.edge.predicates,
            edge_text_color="white",
            edge_font_size=14,
            **kwargs
        )
    
    @property
    def graphql_schema(self):
        """ Get a Graphene-generated GraphQL schema for API resolution """
        
        NodeValueObject = namedtuple("Node", ["id", "name", "document", "graph"])
        class Node(ObjectType):
            id = graphene.ID(required=True)
            name = graphene.String(required=True)
            document = graphene.JSONString(required=True)

            all_neighbors = List(lambda: Node)
            in_neighbors = List(lambda: Node)
            out_neighbors = List(lambda: Node)

            all_edges = List(lambda: Edge)
            in_edges = List(lambda: Edge)
            out_edges = List(lambda: Edge)

            @classmethod
            def from_vertex(cls, vertex: DocumentVertex):
                return NodeValueObject(
                    id=vertex.uuid,
                    name=vertex.name,
                    document="{}",  # TODO Implement
                    graph=vertex.docgraph,
                )
            
            def resolve_all_neighbors(root, info):
                return [
                    Node.from_vertex(v)
                    for v in root.graph[root.name].all_neighbors()
                ]
            
            def resolve_in_neighbors(root, info):
                return [
                    Node.from_vertex(v)
                    for v in root.graph[root.name].in_neighbors()
                ]
            
            def resolve_out_neighbors(root, info):
                return [
                    Node.from_vertex(v)
                    for v in root.graph[root.name].out_neighbors()
                ]
        
            def resolve_all_edges(root, info):
                return [
                    Edge.from_edge(e)
                    for e in root.graph[root.name].all_edges()
                ]
            
            def resolve_in_edges(root, info):
                return [
                    Edge.from_edge(e)
                    for e in root.graph[root.name].in_edges()
                ]
            
            def resolve_out_edges(root, info):
                return [
                    Edge.from_edge(e)
                    for e in root.graph[root.name].out_edges()
                ]
            
        EdgeValueObject = namedtuple("Edge", ["source", "target", "predicates", "element"])
        class Edge(ObjectType):
            source = Field(lambda: Node, required=True)
            target = Field(lambda: Node, required=True)
            predicates = List(graphene.String)
            element = graphene.JSONString(required=True)

            @classmethod
            def from_edge(cls, edge: DocumentEdge):
                return EdgeValueObject(
                    source=Node.from_vertex(edge.source()),
                    target=Node.from_vertex(edge.target()),
                    predicates=edge.predicates,
                    element="{}",  # TODO Implement
                )
        
        class FilterInput(graphene.InputObjectType):
            """ Object for filtering queries """

            @property
            def graph(this):
                graph = self
                if this.in_subgraph is not None:
                    graph = graph.subgraph_around(self[this.in_subgraph])
                if this.predicate is not None:
                    graph = graph.predicate_masked(this.predicate)
                return graph

            in_subgraph = graphene.String(required=False)
            """ If present, this filters results within the named subgraph """

            predicate = graphene.String(required=False)
            """ If present, this filters results by the given predicate """

        class Query(ObjectType):
            nodes = List(
                Node,
                filter=graphene.Argument(FilterInput, required=True, default_value=None),
            )
            node_by_name = Field(
                Node,
                name=graphene.String(required=True),
                filter=graphene.Argument(FilterInput, required=True, default_value=None),
            )
            node_by_id = Field(
                Node,
                id=graphene.ID(required=True),
                filter=graphene.Argument(FilterInput, required=True, default_value=None),
            )

            def resolve_nodes(parent, info, filter=None):
                graph = self if filter is None else filter.graph
                return [
                    Node.from_vertex(v) for v in graph.vertices
                ]

            def resolve_node_by_name(parent, info, name, filter=None):
                graph = self if filter is None else filter.graph
                print(graph.graph)
                return Node.from_vertex(graph[name])

            def resolve_node_by_id(parent, info, id, filter=None):
                graph = self if filter is None else filter.graph
                return Node.from_vertex(graph.get_vertex_by_id(id))

        return Schema(
            query=Query,
        )