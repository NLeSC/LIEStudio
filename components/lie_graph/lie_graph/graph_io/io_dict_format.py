# -*- coding: utf-8 -*-

from lie_graph.graph_helpers import GraphException
from lie_graph.graph import Graph
from lie_graph.graph_axis.graph_axis_class import GraphAxis
from lie_graph.graph_io.io_helpers import flatten_nested_dict


def read_dict(dictionary, graph=None, node_data_tag=None, edge_data_tag=None, valuestring='value'):
    """
    Parse (hierarchical) dictionary data structure to a graph

    :param dictionary:      dictionary
    :type dictionary:       :py:dict
    :param graph:           Graph object to import dictionary data in
    :type graph:            :lie_graph:Graph
    :param node_data_tag:   Data key to use for parsed node labels.
    :type node_data_tag:    :py:str
    :param edge_data_tag:   Data key to use for parsed edge labels.
    :type edge_data_tag:    :py:str
    :param valuestring:     Data key to use for dictionary values.
    :type valuestring:      :py:str

    :return:                GraphAxis object
    :rtype:                 :lie_graph:GraphAxis
    """

    assert isinstance(dictionary, dict), \
        TypeError("Requires dictionary, got: {0}".format(type(dictionary)))

    if not isinstance(graph, Graph):
        graph = GraphAxis()

    # Define node/edge data labels
    if node_data_tag:
        graph.node_data_tag = node_data_tag
    if edge_data_tag:
        graph.edge_data_tag = edge_data_tag

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


def write_dict(graph, keystring=None, valuestring='value', nested=True, sep='.', default=None, include_root=False):
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

    :rtype:              :py:dict
    """

    # Graph should inherit from Graph baseclass
    if not isinstance(graph, GraphAxis):
        raise GraphException('Graph {0} not a valid "GraphAxis" object'.format(type(graph)))

    # No nodes, return empty dict
    if graph.empty():
        return {}

    # Root node should be defined
    assert graph.root is not None, 'Graph has no root node defined'
    assert graph.root in graph.nodes(), 'Graph root node {0} not in graph'.format(graph.root)

    # Resolve node dictionary attributes for value
    keystring = keystring or graph.node_data_tag

    # Construct the dictionary traversing the graph hierarchy
    def _walk_dict(node, target_dict):

        if node.isleaf:
            target_dict[node.get(keystring)] = node.get(valuestring, default=default)
        else:
            target_dict[node.get(keystring)] = {}
            for child in node.children():
                _walk_dict(child, target_dict[node.get(keystring)])

    # Include root node
    graph_dict = {}
    root = graph.getnodes(graph.root)
    rootkey = root.get(keystring, default='root')
    if include_root:
        graph_dict[rootkey] = {}

    for child_node in graph.children():
        _walk_dict(child_node, graph_dict.get(rootkey, graph_dict))

    # Flatten the dictionary if needed
    if not nested:
        graph_dict = flatten_nested_dict(graph_dict, sep=sep)

    return graph_dict
