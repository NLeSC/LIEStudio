# -*- coding: utf-8 -*-

"""
file: io_dict_format.py

Functions for exporting and importing graphs to and from Python dictionary
objects
"""

from lie_graph.graph import Graph, GraphException
from lie_graph.graph_axis.graph_axis_class import GraphAxis
from lie_graph.graph_io.io_helpers import flatten_nested_dict, resolve_root_node


def read_dict(dictionary, graph=None, node_key_tag=None, edge_key_tag=None, valuestring='value'):
    """
    Parse (hierarchical) dictionary data structure to a graph

    :param dictionary:      dictionary
    :type dictionary:       :py:dict
    :param graph:           Graph object to import dictionary data in
    :type graph:            :lie_graph:Graph
    :param node_key_tag:   Data key to use for parsed node labels.
    :type node_key_tag:    :py:str
    :param edge_key_tag:   Data key to use for parsed edge labels.
    :type edge_key_tag:    :py:str
    :param valuestring:     Data key to use for dictionary values.
    :type valuestring:      :py:str

    :return:                GraphAxis object
    :rtype:                 :lie_graph:GraphAxis
    """

    assert isinstance(dictionary, dict), TypeError("Requires dictionary, got: {0}".format(type(dictionary)))

    if not isinstance(graph, Graph):
        graph = GraphAxis()

    # Define node/edge data labels
    if node_key_tag:
        graph.node_key_tag = node_key_tag
    if edge_key_tag:
        graph.edge_key_tag = edge_key_tag

    rootnid = graph.add_node('root')
    graph.root = rootnid

    # Sub function to recursively walk the dictionary and add key,value pairs
    # as new nodes.
    def _walk_dict(dkey, dvalue, rnid):

        nid = graph.add_node(dkey)
        graph.add_edge(rnid, nid)

        if isinstance(dvalue, dict):
            for k, v in sorted(dvalue.items()):
                _walk_dict(k, v, nid)
        else:
            node = graph.getnodes(nid)
            node.set(valuestring, dvalue)

    for key, value in sorted(dictionary.items()):
        _walk_dict(key, value, rootnid)

    return graph


def write_dict(graph, keystring=None, valuestring=None, nested=True, sep='.', default=None, root_nid=None,
               include_root=False):
    """
    Export a graph to a (nested) dictionary

    Convert graph representation of the dictionary tree into a dictionary
    using a nested or flattened representation of the dictionary hierarchy.

    In a flattened representation, the keys are concatenated using the `sep`
    separator.
    Dictionary keys and values are obtained from the node attributes using
    `keystring` and `valuestring`.  The keystring is set to graph node_key_tag
    by default.

    :param graph:        Graph object to export
    :type graph:         :lie_graph:GraphAxis
    :param nested:       return a nested or flattened dictionary
    :type nested:        :py:bool
    :param sep:          key separator used in flattening the dictionary
    :type sep:           :py:str
    :param keystring:    key used to identify dictionary 'key' in node
                         attributes
    :type keystring:     :py:str
    :param valuestring:  key used to identify dictionary 'value' in node
                         attributes
    :type valuestring:   :py:str
    :param default:      value to use when node value was not found using
                         valuestring.
    :type default:       mixed
    :param include_root: Include the root node in the hierarchy
    :type include_root:  :py:bool
    :param root_nid:     Root node ID in graph hierarchy

    :rtype:              :py:dict
    """

    # No nodes, return empty dict
    if graph.empty():
        return {}

    # Resolve the root node (if any) for hierarchical data structures
    if root_nid:
        assert root_nid in graph.nodes, GraphException('Root node ID {0} not in graph'.format(root_nid))
    else:
        root_nid = resolve_root_node(graph)
        assert root_nid is not None, GraphException('Unable to resolve root node ID')

    # Resolve node dictionary attributes for key/value
    keystring = keystring or graph.node_key_tag
    valuestring = valuestring or graph.node_value_tag

    # Construct the dictionary traversing the graph hierarchy
    def _walk_dict(node, target_dict):

        if node.isleaf:
            target_dict[node.get(keystring)] = node.get(valuestring, default=default)
        else:
            target_dict[node.get(keystring)] = {}
            for cid in node.children(return_nids=True):
                child = node.getnodes(cid)
                _walk_dict(child, target_dict[node.get(keystring)])

    # Include root node
    graph_dict = {}
    root = graph.getnodes(root_nid)
    rootkey = root.get(keystring, default='root')
    if include_root:
        graph_dict[rootkey] = {}

    # In case root is a leaf node
    if root.isleaf:
        graph_dict[root.get(keystring)] = root.get(valuestring, default=default)

    # Traverse root descendants
    for child_node in root.children():
        _walk_dict(child_node, graph_dict.get(rootkey, graph_dict))

    # Flatten the dictionary if needed
    if not nested:
        graph_dict = flatten_nested_dict(graph_dict, sep=sep)

    return graph_dict
