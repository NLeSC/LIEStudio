# -*- coding: utf-8 -*-

"""
file: graph_math_operations.py

Functions for performing 'set' like math operations on graphs.
"""

from .graph_helpers import _edge_list_to_adjacency


def graph_add(graph1, graph2):
    """
    Add graph2 to graph2

    Add nodes and edges in graph2 missing in graph1 to graph1 based on
    node and edge ID.

    Nodes and edges from graph2 are added to graph1 without updating the
    respective attributes. The latter can be done by calling the `update`
    function afterwards with the returned graph and graph2.

    :param graph1:  target graph
    :type graph1:   Graph
    :param graph2:  source graph
    :type graph2:   Graph
    """

    auto_nid = graph1.auto_nid
    graph1.auto_nid = False

    for node in graph2.nodes():
        if node not in graph1.nodes:
            graph1.add_node(node)

    for edge in graph2.edges():
        if edge not in graph1.edges:
            graph1.add_edge(edge, directed=False)

    graph1.auto_nid = auto_nid

    # Rebuild graph adjacency list
    adjacency = _edge_list_to_adjacency(graph1.edges.keys())
    graph1.adjacency.update(adjacency)

    return graph1


def graph_union(graph1, graph2):
    """
    Union of graph1 and graph2

    Add nodes and edges from graph1 and graph2 combined to graph1

    Nodes and edges are added without updating the respective attributes.
    The latter can be done by calling the `update` function afterwards with
    the returned graph and graph2.

    :param graph1:  target graph
    :type graph1:   Graph
    :param graph2:  source graph
    :type graph2:   Graph
    """

    auto_nid = graph1.auto_nid
    graph1.auto_nid = False

    for node in graph1.nodes.union(graph2.nodes):
        if node not in graph1.nodes:
            graph1.add_node(node)

    for edge in graph1.edges.union(graph2.edges):
        if edge not in graph1.edges:
            graph1.add_edge(edge)

    graph1.auto_nid = auto_nid

    # Rebuild graph adjacency list
    adjacency = _edge_list_to_adjacency(graph1.edges.keys())
    graph1.adjacency.update(adjacency)

    return graph1


def graph_intersection(graph):

    pass


def graph_difference(graph):

    pass


def graph_symmetric_difference(graph):

    pass


def graph_update(graph1, graph2, update_edges=True, update_nodes=True):
    """
    Update graph1 with the content of graph2

    Requires graph2 to be fully contained in graph1 based on graph topology
    measured as equality between nodes and edges assessed by node and edge ID.

    :param graph1:  target graph
    :type graph1:   Graph
    :param graph2:  source graph
    :type graph2:   Graph
    :param update_edges: update edge data
    :type update_edges:  bool
    :param update_nodes: update node data
    :type update_nodes:  bool
    """

    if graph2 in graph1:
        if update_edges:
            for edge, value in graph2.edges.items():
                graph1.edges[edge].update(value)
        if update_nodes:
            for node, value in graph2.nodes.items():
                graph1.nodes[node].update(value)

    return graph1
