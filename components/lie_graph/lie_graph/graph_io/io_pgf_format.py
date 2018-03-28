# -*- coding: utf-8 -*-

"""
file: io_pgf_format.py

Functions for reading and writing graphs defined in Propitiatory Graph Format
(.pgf) a format specific to the lie_graph module.

Graph nodes, edges and adjacency are stored as plain python dictionaries
"""
import os

import os
import pprint
import pickle
import logging as logger

from lie_graph.graph import Graph


def write_graph(graph, path=os.path.join(os.getcwd(), 'graph.gpf'), pickle_graph=False):
    """
    Export graph as Graph Python Format file

    GPF format is the modules own file format consisting out of a serialized
    or pickled nodes and edges dictionary.
    The format is feature rich wth good performance but is not portable.

    :param graph:        Graph object to export
    :type graph:         Graph instance
    :param path:         File path to write to
    :type path:          path as string
    :param pickle_graph: export graph as pickled GPF format
    :type pickle_graph:  :py:bool

    :return: Graph instance
    """

    # Export graph as pickled Graph Python Format
    if pickle_graph:

        pickle_dict = {'nodes': graph.nodes.dict(), 'edges': graph.edges.dict()}
        with open(path, "wb") as output:
            pickle.dump(pickle_dict, output)

        logger.info('Graph exported in pickled GPF format to file: {0}'.format(path))

    # Export graph as serialized Graph Python Format
    else:

        pp = pprint.PrettyPrinter(indent=2)
        with open(path, 'w') as output:

            # Export nodes as dictionary
            output.write('nodes = {0}\n'.format(pp.pformat(graph.nodes.dict())))

            # Export edges as dictionary
            output.write('edges = {0}\n'.format(pp.pformat(graph.edges.dict())))

        logger.info('Graph exported in GPF format to file: {0}'.format(path))


def read_graph(graph_file, graph=None, pickle_graph=False):
    """
    Import graph from Graph Python Format file

    GPF format is the modules own file format consisting out of a serialized
    or pickled nodes and edges dictionary.
    The format is feature rich wth good performance but is not portable.

    :param graph_file:    File path to read from
    :type graph_file:     :py:str
    :param graph:        Graph object to import to or Graph by default
    :type graph:         Graph instance
    :param pickle_graph: Import graph as pickled GPF format
    :type pickle_graph:  :py:bool
    :return:             Graph instance
    """

    if not graph:
        graph = Graph()

    # Import graph from pickled Graph Python Format
    if pickle_graph:
        
        with open(graph_file, mode='rb') as graph_file:
            pickle_dict = pickle.load(graph_file)

            if 'nodes' in pickle_dict and 'edges' in pickle_dict:
                graph.nodes._storage = pickle_dict['nodes']
                graph.edges._storage = pickle_dict['edges']

            adjacency = dict([(n, []) for n in pickle_dict['nodes']])
            for edge in pickle_dict['edges']:
                adjacency[edge[0]].append(edge[1])

            graph.adjacency._storage = adjacency

        logger.info('Graph imported from pickled GPF format file: {0}'.format(graph_file.name))

    # Import graph from serialized Graph Python Format
    else:
        with open(graph_file) as f:
            code = compile(f.read(), "GPF_file", 'exec')
            exec(code)

    return graph
