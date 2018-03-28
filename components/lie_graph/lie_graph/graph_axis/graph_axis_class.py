# -*- coding: utf-8 -*-

"""
Graph axis methods

Class for traversing and querying (sub)graph hierarchy with respect to a root
node.
"""

from lie_graph.graph import Graph
from lie_graph.graph_helpers import GraphException
from lie_graph.graph_axis.graph_axis_methods import (node_ancestors, node_children, node_descendants, node_neighbors,
    node_parent, node_all_parents, node_siblings, node_leaves)


class GraphAxis(Graph):
    """
    Hierarchical graph query and traversal with respect to a root node.

    The GraphAxis class extends the Graph base class with methods that enable
    query and traversal of graphs that have a hierachy with respect to a
    certain root node.
    A root node is chosen by node ID (nid) and is the one with the lowest ID
    (number) by default or any other one chosen at a later time.
    Hierarchy is queried with respect to the root node by means of axis that
    include: children, descendants, leaves, neighours, siblings, parents and
    ancestors.

    These methods return selections, or sub-graphs, that represent the
    respective axis. By default these selections maintain full connectivity to
    the full graphs and thus represent a selective 'view' on the full graph.
    This behaviour can be changed by enabling a 'mask' on the selection or by
    copying the selection into a new independent graph. The behaviour of both
    options are the same, connectivity is maintained with the selection but
    outside of it. The benefit of a mask, enabled by settings 'is_masked' to
    True, is that it is non-destructive to the data and can be easily lifted
    again.

    The behaviour of axis methods is furthermore affected by the directivity
    of the graph. The default non-directive graphs can be fully traversed
    forwards and backwards. Directed graphs or mixed graphs block traversal
    to parts of the graph by lack of an edge to traverse over.

    All of the axis methods are wrappers around their respective function in
    lie_graph.graph_axis.graph_axis_methods. These functions return node ID's
    that are used by the wrapper method to return the respective sub-graph or
    node ID's with 'return_nids' equals True.
    """

    def _resolve_nid(self):
        """
        Return the node ID (nid) of the current node

        When using single node graph objects this method will return the nid of
        the given node, in multi-node graphs it will return the first nid in
        the keys list and in empty graphs it will return None.
        """

        if self.root is None:
            raise GraphException('Graph node descendant requires a root node')

        try:
            return self.nid
        except AttributeError:
            return self.root

    def ancestors(self, node=None, include_self=False, return_nids=False):
        """
        Return the ancestors of the source node

        Traversal path is determined as the shortest path between the root node
        and the target node (Dijkstra shortest path).

        Directed graphs and/or is_masked behaviour: if the target node is not
        reachable using the Dijkstra shortest path method, the selection will
        remain empty.

        :param node:         source node to start search from
        :type node:          mixed
        :param include_self: include source nid in results
        :type include_self:  bool
        :param return_nids:  return a list of node ID's (nid) instead of a new
                             graph object representing the selection
        :type return_nids:   bool
        """

        nid = node or self._resolve_nid()
        anc = node_ancestors(self, nid, self.root, include_self=include_self)

        # mask node check
        if self.is_masked:
            anc = [n for n in anc if n in self.nodes]

        if return_nids:
            return anc
        return self.getnodes(anc)

    def children(self, node=None, include_self=False, return_nids=False):
        """
        Return the children of the source node.

        Traversal path is determined from the parent node with respect to the
        root via the source node to the children.

        Directed graphs and/or is_masked behaviour: masked child nodes or child
        nodes with directed connections from child to parent but not vice-versa
        will not be returned.

        :param node:         source node to start search from
        :type node:          mixed
        :param include_self: include source nid in results
        :type include_self:  bool
        :param return_nids:  return a list of node ID's (nid) instead of a new
                             graph object representing the selection
        :type return_nids:   bool

        :rtype:              Graph object or :py:list
        """

        nid = node or self._resolve_nid()
        nch = node_children(self, nid, self.root, include_self=include_self)

        if return_nids:
            return nch
        return self.getnodes(nch)

    def descendants(self, node=None, include_self=False, return_nids=False):
        """
        Return all descendants nodes to the source node

        Traversal path is determined from the parent with respect to the root
        node to the source node and then all descendants of the source.

        Directed graphs and/or is_masked behaviour: masked descendant linage's
        or linage's unreachable by directed edges are not returned.

        :param node:         source node to start search from
        :type node:          mixed
        :param include_self: include source nid in results
        :type include_self:  bool
        :param return_nids:  return a list of node ID's (nid) instead of a new
                             graph object representing the selection
        :type return_nids:   bool
        """

        nid = node or self._resolve_nid()
        nds = node_descendants(self, nid, self.root, include_self=include_self)

        if return_nids:
            return nds
        return self.getnodes(nds)

    def leaves(self, include_root=False, return_nids=False, include_isolated=False):
        """
        Return all leaf nodes in the (sub)graph

        Directed graphs and/or is_masked behaviour: leaf nodes are identified
        as those nodes having one edge only. This equals one adjacency node in
        an undirectional graph and no adjacency nodes in a directed graph.

        Graph root nodes do not affect the character of a node being a leave,
        neither will unidirectional versus directional edges.

        :param include_root:     include the root node if it is a leaf
        :type include_root:      bool
        :param return_nids:      return a list of node ID's (nid) instead of a new
                                 graph object representing the selection
        :type return_nids:       bool
        :param include_isolated: Include isolated nodes in the result
        :type include_isolated:  :py:bool

        :return:                 leaf node nids
        """

        leaves = node_leaves(self, include_isolated=include_isolated)
        if not include_root and self.root in leaves:
            leaves.remove(self.root)

        if return_nids:
            return sorted(leaves)
        return self.getnodes(leaves)

    def neighbors(self, node=None, return_nids=False):
        """
        Return de neighbor nodes of the source node.

        This method is not hierarchical and thus the root node has no effect.

        Directed graphs and/or is_masked behaviour: masked nodes or directed
        nodes not having an edge from source to node will not be returned.

        :param node:         node to return neighbors for
        :type node:          mixed
        :param return_nids:  return a list of node ID's (nid) instead of a new
                             graph object representing the selection
        :type return_nids:   bool
        """

        nid = node or self._resolve_nid()
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

        nid = node or self._resolve_nid()
        np = None
        if self.root != nid:
            np = node_parent(self, nid, self.root)

            # For masked graphs, parent might not be in nodes
            if self.is_masked and not np in self.nodes:
                np = None

        if return_nids:
            return np
        return self.getnodes(np)
    
    def all_parents(self, node=None, return_nids=False):
        """
        Get all parent nodes to the source node relative to the graph root

        Directed graphs and/or is_masked behaviour: masked nodes or directed
        nodes not having an edge from source to node will not be returned.

        :param node:         node to define parents of
        :type node:          mixed
        :param return_nids:  return parent nid instead of a new graph object
                             representing the selection
        :type return_nids:   bool

        :return:             parent nodes
        :rtype:              Graph object or list
        """
        
        nid = node or self._resolve_nid()
        anp = node_all_parents(self, nid, self.root)
        
        if return_nids:
            return anp
        return self.getnodes(anp)
        
    def siblings(self, node=None, return_nids=False):
        """
        Get the siblings of the source node

        Directed graphs and/or is_masked behaviour: masked nodes or directed
        nodes not having an edge from source to node will not be returned.

        :param node:         source node to start search from
        :type node:          mixed
        :param return_nids:  return a list of node ID's (nid) instead of a new
                             graph object representing the selection
        :type return_nids:   bool

        :return:             sibling nodes
        :rtype:              Graph object or list
        """

        nid = node or self._resolve_nid()
        nsb = node_siblings(self, nid, self.root)

        if return_nids:
            return sorted(nsb)
        return self.getnodes(nsb)

    # DICTIONARY LIKE NODE ACCESS
    def items(self, keystring=None, valuestring=None, desc=True):
        """
        Python dict-like function to return node items in the (sub)graph.

        Keystring defines the value lookup key in the node data dict.
        This defaults to the graph node_key_tag.
        Valuestring defines the value lookup key in the node data dict.

        :param keystring:   Data key to use for dictionary keys.
        :type keystring:    :py:str
        :param valuestring: Data key to use for dictionary values.
        :type valuestring:  :py:str
        :param desc:        return nested values as new GraphAxis objects
        :type desc:         :py:bool

        :return:            List of keys, value pairs
        :rtype:             :py:list
        """

        keystring = keystring or self.node_key_tag
        valuestring = valuestring or self.node_value_tag

        if desc:
            return [(n.get(keystring), n.get(valuestring)) if n.isleaf else (n.get(keystring), n)
                    for n in self.iternodes()]
        return [(n.get(keystring), n.get(valuestring)) for n in self.iternodes()]

    def values(self, valuestring=None, desc=True):
        """
        Python dict-like function to return node values in the (sub)graph.

        Valuestring defines the value lookup key in the node data dict.

        :param valuestring: Data key to use for dictionary values.
        :type valuestring:  :py:str
        :param desc:        return nested values as new GraphAxis objects
        :type desc:         :py:bool


        :return:            List of values
        :rtype:             :py:list
        """

        valuestring = valuestring or self.node_value_tag

        if desc:
            return [n.get(valuestring) if n.isleaf else n for n in self.iternodes()]
        return [n.get(valuestring) for n in self.iternodes()]

