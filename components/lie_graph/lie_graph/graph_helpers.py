# -*- coding: utf-8 -*-

import copy
import logging as logger

from graph_storage_drivers.graph_dict import DictStorage


def adjacency_to_edges(nodes, adjacency, node_source):
    """
    Construct edges for nodes based on adjacency.

    Edges are created for every node in `nodes` based on the neighbors of
    the node in adjacency if the neighbor node is also in `node_source`.
    The source of adjacency information would normally be self.graph and
    self.nodes for `node_source`. However, `node_source may` also equal
    `nodes` to return edges for the isolated graph.

    :param nodes:       nodes to return edges for
    :type nodes:        list
    :param adjacency:   node adjacency (self.graph)
    :type adjacency:    dict
    :param node_source: other nodes to consider when creating edges
    :type node_source:  list
    """

    edges = []
    for node in nodes:
        edges.extend([tuple([node, e]) for e in adjacency[node] if e in node_source])

    return edges


def edge_list_to_adjacency(edges):
    """
    Create adjacency dictionary based on a list of edges

    :param edges: edges to create adjacency for
    :type edges:  list
    """

    adjacency = dict([(n, []) for n in edge_list_to_nodes(edges)])
    for edge in edges:
        adjacency[edge[0]].append(edge[1])

    return adjacency


def edge_list_to_nodes(edges):
    """
    Create a list of nodes from a list of edges

    :param edges: edges to create nodes for
    :type edges:  list
    """

    return list(set(sum(edges, ())))


def make_edges(nodes, directed=True):
    """
    Create an edge tuple from two nodes either directed
    (first to second) or undirected (two edges, both ways).

    :param nodes:    nodes to create edges for
    :type nodes:     list or tuple
    :param directed: greate directed edge or not
    :type directed:  bool
    """

    edges = [tuple(nodes)]
    if not directed:
        edges.append(nodes[::-1])

    return edges


def renumber_id(graph, start):
    """
    Renumber all node ID's in the graph from a new start ID and adjust edges
    accordingly. Useful when duplicating a graph substructure.
    If the graph uses auto_nid, the node nid is also changed.

    :param graph:   Graph object to renumber
    :type graph:    Graph object
    :param start:   New start number to renumber from
    :type start:    :py:int
    :return:        Renumber graph and mapping of old to new ID
    :rtype:         Graph object, :py:dict
    """

    start = copy.copy(start)
    mapper = {}
    for nid, value in sorted(graph.nodes.items()):
        mapper[value['_id']] = start

        # Renumber
        value['_id'] = start
        if graph.auto_nid:
            value['nid'] = start

        start += 1

    # Update nid if auto_nid
    if graph.auto_nid:
        newnodes = {v: graph.nodes[k] for k, v in mapper.items()}
        graph.nodes = DictStorage(newnodes)

    # Update edges.
    newedges = {}
    for eid, edge in graph.edges.items():
        newedges[(mapper.get(eid[0], eid[0]), mapper.get(eid[1], eid[1]))] = edge
    graph.edges = DictStorage(newedges)

    # Set new auto_nid counter and update adjacency
    graph._nodeid = start
    graph._set_adjacency()

    return graph, mapper


def graph_directionality(graph):
    """
    Return a graph overall directionality as 'directional', 'undirectional'
    or 'mixed'

    :param graph: Graph to asses directionality of

    :return:      'directional', 'undirectional' or 'mixed'
    :rtype:       :py:str
    """

    edge_directionality = []
    for node, adj in graph.adjacency.items():
        edge_directionality.extend([node in graph.adjacency[n] for n in adj])

    if all(edge_directionality):
        return 'undirectional'
    elif any(edge_directionality):
        return 'mixed'
    else:
        return 'directional'


def graph_to_undirectional(graph):
    """
    Convert a directional graph or graph of mixed directionality to a
    undirectional graph by creating the missing edges and copying the
    edge data from the directional counterpart

    :param graph: Graph to correct directionality for

    :return:      Undirectional graph
    """

    for node, adj in graph.adjacency.items():
        for n in adj:
            if not node in graph.adjacency[n]:
                print('Missing edge from {0} to {1}. Create'.format(n, node))
                graph.add_edge(n, node, attr=graph.edges.get((node, n)))

    # Adjust graph is_directed labels to False
    graph.is_directed = False

    return graph


class GraphException(Exception):
    """
    Graph Exception class.
    Logs the exception as critical before raising.
    """

    def __init___(self, message='', *args, **kwargs):
        logger.critical(message)
        Exception.__init__(self, *args, **kwargs)
