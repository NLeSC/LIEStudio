# -*- coding: utf-8 -*-

"""
#Graph module

###Basic graph structure
A graph represented by a Graph class is an object that stores nodes, edges and
adjacency information in seperate DictStorage classes. A DictStorage class is a
subclass of the standard Python dictionary and collections MutableMappings
Abstract Base Class (ABC).

The nodes and edges DictStorage objects store node and edge attributes respectivly
based on the node ID (nid).
The graph DictStorage object stores node adjacency and is the primary store for
the graph topology.

###Node ID
The node ID or nid for short is the unique identifier of a node and derived edges
in the graph. The nid itself can be any hasable object except None. Set auto_nid
to True in the graph to ensure all added nodes are automatically assigned a unique
auto incremented integer ID.


###Graph directionality
A graph is undirected by default storing an two edges for every connected node,
one in each direction.
Change the graph is_directed attribute to True will ensure that every every newly
added edge is directed. Directed and undirected edges can be mixed in the same
graph.

###Graph query and iteration
The graph module has a rich palet of functions to query and analyze graphs.
For performance reasons, most of these will return node or edge IDs. New Graph
object representing a node and/or edge selection can returned using one of the
following Graph methods:

 * getnodes: return subgraph based on one or more nodes
 * getedges: return subgraph based on one or more edges
 * iternodes: iterate over nodes in the graph. Uses getnodes
 * iteredges: iterate over edges in the graph. Uses getedges
 * query_nodes: return subgraph based on a query over node attributes
 * query_edges: return subgraph based on a query over edge attributes

The subgraphs returned by these methods are implemented as a dictionary view over
the keys in the nodes and edges DictStorage objects.
By default this means that the subgraphs are fully isolated from the parent graph.
Returning a single node using getnodes will have no neigbors.
This may not be desirable in circumstances where you want a view over nodes but
retain connectivity with nodes outside of the view. This behaviour is enabled by
switching the Graph is_masked to False.
"""

import os

__module__ = 'lie_graph'
__docformat__ = 'restructuredtext'
__version__ = '{major:d}.{minor:d}'.format(major=0, minor=1)
__author__ = 'Marc van Dijk'
__status__ = 'pre-release beta1'
__date__ = '15 april 2016'
__licence__ = 'Apache Software License 2.0'
__url__ = 'https://github.com/NLeSC/LIEStudio'
__copyright__ = "Copyright (c) VU University, Amsterdam"
__rootpath__ = os.path.dirname(__file__)
__all__ = ['Graph', 'GraphAxis', 'GraphORM']

# Component imports
from .graph import Graph
from .graph_axis.graph_axis_class import GraphAxis
from .graph_orm import GraphORM
