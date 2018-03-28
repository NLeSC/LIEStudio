# -*- coding: utf-8 -*-

"""
file: using_nodes.py

Exemplified description on the node handling philosophy of lie_graph package.
"""

from lie_graph import Graph

## Adding nodes to a graph

# A graph is a collection of nodes connected using edges. In lie_graph, nodes
# can be any arbitrary piece of data as long as it is hashable such as: text,
# numbers, images, files or even Python functions or other objects.
# Nodes are added to the graph using the 'add_node' for a single node or
# 'add_nodes' for multiple nodes at once. The functionality for adding nodes
# is similar to most other graph packages including NetworkX.

# Node storage
# The lie_graph uses flexible storage drivers to store node and edge
# information. The default driver stores information as a Python dictionary but
# this may well be a driver that stores information in a high-performance data
# store. The store driver API enforces key/value storage in which the node
# identifier is the key and node attributes the value.
# A graph natively supports the storage of multiple node attributes and
# therefor most node related functions expect a node value to behave in a
# Python dictionary like fashion.

# Node identifiers
# The node key serves as the identifiers (nid) and may be any hashable object
# except None. It is important to ensure that node identifiers are unique
# because the node storage by default do not store node identifiers in a
# hierarchical way. Identical node IDs derived from different dictionaries or
# hierarchical data constructs for instance will no longer be unique.
# The 'add_node(s)' methods will raise a GraphException when a duplicate nid is
# encountered. To ensure unique nids, the Graph class will assign a unique nid
# automatically when the Graph.auto_nid attribute is set to True (by default).
# This automatically incremented integer will function as primary node ID.

# Node attributes
# Any additional key/value pair used as input to the 'add_node' or 'add_nodes'
# method will be added to the node value dictionary as attribute.

# A few examples of using the 'add_node' method and how data will be stored in
# a dictionary like fashion.
#
# add_node()  auto_nid=False:
# this option is not possible
#
# add_node('node')  auto_nid=False:
# {'node': {}}
#
# add_node('node', rank=3)  auto_nid=False:
# {'node': {'rank': 3}}
#
# add_node(rank=3)  auto_nid=False:
# {'rank': {'value': 3}}
#
# add_node()  auto_nid=True:
# {1: {}}
#
# add_node('node')  auto_nid=True  node_data_tag='key':
# {1: {'key': 'node'}}
#
# add_node('node', rank=3)  auto_nid=True  node_data_tag='key':
# {1: {'key': 'node', 'rank': 3}}
#
# add_node(rank=3)  auto_nid=True:
# {1: {'rank': 3}}


graph = Graph()
graph.add_node()

print(graph['n'])
print(graph.keys())