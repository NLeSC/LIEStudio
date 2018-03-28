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

Reference: https://en.wikipedia.org/wiki/Trivial_Graph_Format
"""

import sys

if sys.version_info[0] < 3:
    import StringIO
else:
    from io import StringIO

from lie_graph.graph import Graph
from lie_graph.graph_io.io_helpers import coarse_type, open_anything


def read_tgf(tgf, graph=None, node_key_tag=None, edge_key_tag=None):
    """
    Read graph in Trivial Graph Format

    TGF format dictates that nodes to be listed in the file first with each
    node on a new line. A '#' character signals the end of the node list and
    the start of the edge list.

    Node and edge ID's can be integers, float or strings. They are parsed
    automatically to their most likely format.
    Simple node and edge labels are supported in TGF as all characters that
    follow the node or edge ID's. They are parsed and stored in the Graph
    node and edge data stores using the graphs default or custom
    'node_key_tag' and 'edge_key_tag'.

    TGF data is imported into a default Graph object if no custom Graph
    instance is provided. The graph behaviour and the data import process is
    influenced and can be controlled using a (custom) Graph class.

    A few important notes:
    * Default Graphs have auto_nid enabled which means that all node ID's and
      corresponding edges are assigned using an automatically incremented
      integer ID. Custom node labels are ignored although stored in the node
      and/or edge data.
    * TGF format always defines edges in a directed fashion. This is enforced
      even for custom graphs.

    :param tgf:             TGF graph data.
    :type tgf:              File, string, stream or URL
    :param graph:           Graph object to import TGF data in
    :type graph:            :lie_graph:Graph
    :param node_key_tag:   Data key to use for parsed node labels.
    :type node_key_tag:    :py:str
    :param edge_key_tag:   Data key to use for parsed edge labels.
    :type edge_key_tag:    :py:str

    :return:                Graph object
    :rtype:                 :lie_graph:Graph
    """

    tgf_file = open_anything(tgf)
    if not isinstance(graph, Graph):
        graph = Graph()

    # Define node/edge data labels
    if node_key_tag:
        graph.node_key_tag = node_key_tag
    if edge_key_tag:
        graph.edge_key_tag = edge_key_tag

    # TGF defines edges in a directed fashion. Enforce but restore later
    default_directionality = graph.is_directed
    graph.is_directed = True

    # Start parsing. First extract nodes
    nodes = True
    node_dict = {}
    for line in tgf_file.readlines():

        line = line.strip()
        if len(line):

            # Reading '#' character means switching from node
            # definition to edges
            if line.startswith('#'):
                nodes = False
                continue

            # Coarse string to types
            line = [coarse_type(n) for n in line.split()]

            # Parse nodes
            if nodes:

                attr = {}
                # Has node data
                if len(line) > 1:
                    attr = {graph.node_key_tag: ' '.join(line[1:])}
                nid = graph.add_node(line[0], **attr)
                node_dict[line[0]] = nid

            # Parse edges
            else:
                e1 = node_dict[line[0]]
                e2 = node_dict[line[1]]

                attr = {}
                # Has edge data
                if len(line) > 2:
                    attr = {graph.edge_key_tag: ' '.join(line[2:])}
                graph.add_edge(e1, e2, **attr)

    tgf_file.close()

    # Restore directionality
    graph.is_directed = default_directionality

    return graph


def write_tgf(graph, node_key_tag=None, edge_key_tag=None):
    """
    Export a graph in Trivial Graph Format

    .. note::
    TGF graph export uses the Graph iternodes and iteredges methods to retrieve
    nodes and edges and 'get' the data labels. The behaviour of this process is
    determined by the single node/edge mixin classes and the ORM mapper.

    :param graph:         Graph object to export
    :type graph:          :lie_graph:Graph
    :param node_key_tag: node data key
    :type node_key_tag:  :py:str
    :param edge_key_tag: edge data key
    :type edge_key_tag:  :py:str

    :return:              TGF graph representation
    :rtype:               :py:str
    """

    # Define node and edge data tags to export
    node_key_tag = node_key_tag or graph.node_key_tag
    edge_key_tag = edge_key_tag or graph.edge_key_tag

    # Create empty file buffer
    string_buffer = StringIO.StringIO()

    # Export nodes
    for node in graph.iternodes():
        string_buffer.write('{0} {1}\n'.format(node.nid, node.get(node_key_tag, default='')))

    # Export edges
    string_buffer.write('#\n')
    for edge in graph.iteredges():
        e1, e2 = edge.nid
        string_buffer.write('{0} {1} {2}\n'.format(e1, e2, edge.get(edge_key_tag, default='')))

    # Reset buffer cursor
    string_buffer.seek(0)
    return string_buffer.read()
