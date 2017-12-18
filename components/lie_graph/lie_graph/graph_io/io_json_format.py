# -*- coding: utf-8 -*-

"""
Import/Export files in JSON compliant format
"""

import json

import logging as logger

from .. import __version__
from ..graph import Graph
from ..graph_axis_class import GraphAxis
from .io_helpers import _check_lie_graph_version, _open_anything


BASICTYPES = (int, float, bool, long, str, unicode)


def read_dict(dict_format):
    """
    Read graph in Python dictionary format

    :param dict_format: graph encoded as Python dictionary
    :type dict_format:  :py:dict

    :return:            Graph object
    :rtype:             Graph or GraphAxis object
    """
    err = TypeError(
        "Graph representation not a dictionary, got: {0}".format(
            type(dict_format)))
    assert isinstance(dict_format, dict), err

    # Determine graph class to use
    graph_object = Graph()
    if dict_format['graph'].get('root') is not None:
        graph_object = GraphAxis()

    # Init graph meta-data attributes
    for key, value in dict_format['graph'].items():
        setattr(graph_object, key, value)

    # Init graph nodes
    for node_key, node_value in dict_format['nodes'].items():

        # JSON objects don't accept integers as dictionary keys
        # If graph.auto_nid equals True, course node_key to integer
        if graph_object.auto_nid:
            node_key = int(node_key)

        graph_object.nodes[node_key] = node_value

    # Init graph edges
    for edge_key, edge_value in dict_format['edges'].items():
        edge_value = tuple(edge_value)
        graph_object.edges[edge_value] = dict_format['edge_attr'].get(edge_key, {})

    # Reset graph adjacency
    graph_object._set_adjacency()

    return graph_object


def read_json(json_format):
    """
    Read JSON graph format

    :param json_format: JSON encoded graph data to parse
    :type json_format:  :py:str

    :return:            Graph object
    :rtype:             Graph or GraphAxis object
    """

    # Try parsing the string using default Python json parser
    json_format = _open_anything(json_format)
    try:
        parsed = json.load(json_format)
    except IOError:
        logger.error('Unable to decode JSON string')
        return

    # Check lie_graph version and format validity
    if not _check_lie_graph_version(parsed.get('lie_graph_version')):
        return
    keywords = ['graph', 'nodes', 'edges', 'edge_attr']
    if not set(keywords).issubset(set(parsed.keys())):
        logger.error('JSON format does not contain required graph data')
        return

    return read_dict(parsed)


def write_json(graph, indent=2, encoding="utf-8", **kwargs):
    """
    Write JSON graph format

    Format description. Primary key/value pairs:
    * graph: Graph class meta-data. Serializes all class attributes of type
             int, float, bool, long, str or unicode.
    * nodes: Graph node identifiers (keys) and attributes (values)
    * edges: Graph enumerated edge identifiers
    * edge_attr: Graph edge attributes

    :param graph:    graph object to serialize
    :type graph:     Graph or GraphAxis object
    :param indent:   JSON indentation count
    :type indent:    :py:int
    :param encoding: JSON string encoding
    :type encoding:  :py:str
    :param kwargs:   additional data to be stored as file meta data
    :type kwargs:    :py:dic

    :return:         JSON encoded graph dictionary
    """

    # Init JSON format envelope
    json_format = {
        'lie_graph_version': __version__,
        'graph': {},
        'nodes': {},
        'edges': {},
        'edge_attr': {}
    }

    # Update envelope with metadata
    for key, value in kwargs.items():
        if key not in json_format:
            json_format[key] = value

    # Store graph meta data
    for key, value in graph.__dict__.items():
        if not key.startswith('_') and type(value) in BASICTYPES:
            json_format['graph'][key] = value

    # Update nodes with graph node attributes
    json_format['nodes'].update(graph.nodes.dict())

    # JSON cannot encode dictionaries with tuple as keys
    # Split the two up
    edgedata = graph.edges.dict()
    for i, edge in enumerate(edgedata):
        json_format['edges'][i] = edge
        if edgedata[edge]:
            json_format['edge_attr'][i] = edgedata[edge]

    logger.info('Encode graph in JSON format')
    return json.dumps(json_format, indent=indent, encoding=encoding)
