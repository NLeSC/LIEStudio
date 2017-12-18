# -*- coding: utf-8 -*-

"""
Graph axis methods

Class for traversing and querying (sub)graph hierarchy with respect to a root
node.

TODO: Some of the axis methods don't work for directed graphs
"""

from .graph import Graph
from .graph_helpers import GraphException
from .graph_axis_methods import *


class GraphAxis(Graph):
    """
    Graph axis based hierarchy query methods relative to a root node.
    The methods in the class wrap the axis functions in graph_axis_methods
    defining the node ID (nid) the root node and returning the query results
    as new (sub)grah by default.

    This class is combined with the base Graph class to yield the GraphAxis
    class overloading some base methods to enforce root node definition and
    nid selection.
    """

    @property
    def nid(self):
        """
        Return the node ID (nid) of the current node

        When using single node graph objects this method will return the nid of
        the given node, in multi-node graphs it will return the first nid in
        the keys list and in empty graphs it will return None.
        """

        if self.root is None:
            raise GraphException('Graph node descendancy requires a root node')

        nids = list(self.nodes.keys())
        if len(nids):
            return nids[0]
        return None

    def ancestors(self, node=None, include_self=False, return_nids=False):
        """
        Return the ancestors of the source node

        :param node:         source node to start search from
        :type node:          mixed
        :param include_self: include source nid in results
        :type include_self:  bool
        :param return_nids:  return a list of node ID's (nid) instead of a new
                             graph object representing the selection
        :type return_nids:   bool
        """

        nid = node or self.nid
        anc = node_ancestors(self, nid, self.root, include_self=include_self)

        if return_nids:
            return sorted(anc)
        return self.getnodes(anc)

    def children(self, node=None, include_self=False, return_nids=False):
        """
        Return the children of the source node.

        :param node:         source node to start search from
        :type node:          mixed
        :param include_self: include source nid in results
        :type include_self:  bool
        :param return_nids:  return a list of node ID's (nid) instead of a new
                             graph object representing the selection
        :type return_nids:   bool

        :rtype:              Graph object or :py:list
        """

        nid = node or self.nid
        nch = node_children(self, nid, self.root, include_self=include_self)

        if return_nids:
            return sorted(nch)
        return self.getnodes(nch)

    def descendants(self, node=None, include_self=False, return_nids=False):
        """
        Return all descendants nodes to the source node

        :param node:         source node to start search from
        :type node:          mixed
        :param include_self: include source nid in results
        :type include_self:  bool
        :param return_nids:  return a list of node ID's (nid) instead of a new
                             graph object representing the selection
        :type return_nids:   bool
        """

        nid = node or self.nid
        nds = node_descendants(self, nid, self.root, include_self=include_self)

        if return_nids:
            return sorted(nds)
        return self.getnodes(nds)

    def leaves(self, include_root=False, return_nids=False):
        """
        Return all leaf nodes in the (sub)graph

        Leaf nodes are identified as those nodes having one edge only.
        This equals one adjacency node in a undirectional graph and
        no adjacency nodes in a directed graph.

        :param include_root: include the root node if it is a leaf
        :type include_root:  bool

        :return:             leaf node nids
        :rtype:              list
        :param return_nids:  return a list of node ID's (nid) instead of a new
                             graph object representing the selection
        :type return_nids:   bool
        """
        if self.is_directed:
            leaves = [node for node in self.nodes()
                      if len(self.adjacency[node]) == 0]
        else:
            leaves = [node for node in self.nodes()
                      if len(self.adjacency[node]) == 1]
        if not include_root and self.root in leaves:
            leaves.remove(self.root)

        if return_nids:
            return sorted(leaves)
        return self.getnodes(leaves)

    def neighbors(self, node=None, return_nids=False):
        """
        Return de neighbor nodes of the node.

        ..  note:: if the current graph is a subgraph view (is_view == True) of
                   the parent graph than only the neighbor nodes represented by
                   the subgraph will be considered.

        :param node:         node to return neighbors for
        :type node:          mixed
        :param return_nids:  return a list of node ID's (nid) instead of a new
                             graph object representing the selection
        :type return_nids:   bool
        """

        nid = node or self.nid
        nng = node_neighbors(self, nid)

        if return_nids:
            return sorted(nng)
        return self.getnodes(nng)

    def parent(self, node=None, return_nids=False):
        """
        Get the parent node of the source node relative to the graph root
        when following the shortest path (Dijkstra shortest path).

        :param node:         node to define parent of
        :type node:          mixed
        :param return_nids:  return parent nid instead of a new graph object
                             representing the selection
        :type return_nids:   bool

        :return:             parent node
        :rtype:              Graph object
        """

        nid = node or self.nid
        if self.root == nid:
            self.getnodes(None)

        np = node_parent(self, nid, self.root)

        if return_nids:
            return np
        return self.getnodes(np)
    
    def all_parents(self, node=None, return_nids=False):
        """
        Get all parent nodes to the source node relative to the graph root
    
        :param node:         node to define parents of
        :type node:          mixed
        :param return_nids:  return parent nid instead of a new graph object
                             representing the selection
        :type return_nids:   bool

        :return:             parent nodes
        :rtype:              Graph object or list
        """
        
        nid = node or self.nid
        anp = node_all_parents(self, nid, self.root)
        
        if return_nids:
            return anp
        return self.getnodes(anp)
        
    def siblings(self, node=None, return_nids=False):
        """
        Get the siblings of the source node

        :param node:         source node to start search from
        :type node:          mixed
        :param return_nids:  return a list of node ID's (nid) instead of a new
                             graph object representing the selection
        :type return_nids:   bool

        :return:             sibling nodes
        :rtype:              Graph object or list
        """

        nid = node or self.nid
        nsb = node_siblings(self, nid, self.root)

        if return_nids:
            return sorted(nsb)
        return self.getnodes(nsb)
