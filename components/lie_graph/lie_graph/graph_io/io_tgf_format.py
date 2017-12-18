# -*- coding: utf-8 -*-

"""
file: io_tgf_format.py

Functions for reading and writing graphs defined in Trivial Graph Format (.tgf)
a simple text-based file format for describing graphs. It consists of a list of
node definitions, which map node IDs to labels, followed by a list of edges,
which specify node pairs and an optional edge label. Node IDs can be arbitrary
identifiers, whereas labels for both nodes and edges are plain strings.

The graph may be interpreted as a directed or undirected graph.
For directed graphs, to specify the concept of bi-directionality in an edge,
one may either specify two edges (forward and back) or differentiate the edge
by means of a label.
"""

import logging as logger

from ..graph import Graph
from .io_helpers import _coarse_type


def read_tgf(tgf, edge_data_label='label'):
    """
    Read graph in Trivial Graph Format

    TGF format dictates that nodes to be listed in the file first
    with each node on a new line. A '#' character signals the end
    of the node list and the start of the edge list.

    Node and edge ID's can be integers, float or strings.
    They are mapped against the Graphs internal node ID (nid).
    If edges connect nodes that do not exist, an error is logged
    and the edge is skipped.

    :param tgf: TGF graph data.
    :type tgf: File, string, stream or URL
    :param edge_data_label: Graph edge metadata dictionary key to
           use for parsed edge labels. 'label' by default.
    :type edge_data_label: string
    :return: Graph object
    """

    with open(tgf) as tgf_file:

        nodes = True
        node_dict = {}

        # Initiate new empty graph
        graph = Graph()

        # Start parsing file lines. First extract nodes
        for line in tgf_file.readlines():

            line = line.strip()
            if len(line):

                # Reading '#' character means switching from node
                # definition to edges
                if line.startswith('#'):
                    nodes = False
                    continue

                # Coarse string to types
                line = [_coarse_type(n) for n in line.split()]

                # Parse nodes
                if nodes:
                    if len(line) > 1:
                        attr = ' '.join([repr(e) for e in line[1:]])
                        nid = graph.add_node(line[0], tgf=attr)
                    else:
                        nid = graph.add_node(line[0])
                    node_dict[line[0]] = nid

                # Parse edges
                else:
                    e1 = node_dict[line[0]]
                    e2 = node_dict[line[1]]
                    for node in (e1, e2):
                        if node not in graph.nodes:
                            logger.error('Node {0} in edge {1}-{2} not in graph. Skipping edge'.format(node, e1, e2))
                            continue

                    attr = None
                    if len(line) > 2:
                        attr = {edge_data_label: ' '.join([str(e) for e in line[2:]])}
                    graph.add_edge(e1, e2, attr=attr)

    return graph
