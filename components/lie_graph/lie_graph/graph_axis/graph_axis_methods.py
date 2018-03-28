# -*- coding: utf-8 -*-

"""
Graph axis methods

Functions for traversing and querying (sub)graph hierarchy with respect
to a root node. These functions are similar to the axis methods commonly found
in XML libraries.

All these functions accept a (sub)graph, a node id (nid) to query axis based
hierarchy for and a root nid relative to which the hierarchy should be
defined.
"""

from itertools import combinations

from lie_graph.graph_algorithms import dijkstra_shortest_path, node_neighbors, dfs_paths


def closest_to(graph, source, target):
    """
    Determine which of the target nodes are closest to the source node.

    This method is not hierarchical and thus the root node has no effect.

    :param graph:  Graph to perform calculation for
    :type graph:   Graph class instance
    :param source: source node id
    :type source:  :py:int
    :param target: target node id's
    :type target:  :py:list

    :rtype:        :py:list
    """

    if source in target:
        target.remove(source)

    if not len(target):
        return [source]
    if len(target) == 1:
        return target

    shortest = {}
    for nid in sorted(target):
        path = dijkstra_shortest_path(graph._full_graph, source, nid)
        shortest[nid] = set(path)

    remove = []
    for comb in combinations(shortest.keys(), 2):
        if shortest[comb[0]].issubset(shortest[comb[1]]):
            remove.append(comb[1])

    return [n for n in shortest.keys() if n not in remove]


def node_ancestors(graph, nid, root, include_self=False):
    """
    Return the ancestors of the source node

    Traversal path is determined as the shortest path between the root node
    and the target node (Dijkstra shortest path).

    This function always uses the full graph to return the ancestors.
    For masked graphs, check afterwards if the ancestors are in the graph
    node view or use the GraphAxis 'ancestors' method that performs that
    check.

    :param graph:        Graph to perform calculation for
    :type graph:         Graph class instance
    :param nid:          source node to start search from
    :type nid:           :py:int
    :param root:         root node for the search
    :type root:          :py:int
    :param include_self: include source nid in results
    :type include_self:  :py:bool
    """

    anc = dijkstra_shortest_path(graph._full_graph, root, nid)

    if not include_self and nid in anc:
        anc.remove(nid)

    return anc


def node_children(graph, nid, root, include_self=False):
    """
    Return the children of the source node.

    Traversal path is determined from the parent node with respect to the
    root via the source node to the children.

    Directed graphs and/or is_masked behaviour: masked child nodes or child
    nodes with directed connections from child to parent but not vice-versa
    will not be returned.

    :param graph:        Graph to perform calculation for
    :type graph:         Graph class instance
    :param nid:          source node to start search from
    :type nid:           :py:int
    :param root:         root node for the search
    :type root:          :py:int
    :param include_self: include source nid in results
    :type include_self:  :py:bool
    """

    # Children are all neighbors of the node except the parent
    p = node_parent(graph, nid, root)
    children = [n for n in node_neighbors(graph, nid) if not n == p]

    if include_self:
        children.insert(0, nid)

    return children


def node_descendants(graph, nid, root, include_self=False):
    """
    Return all descendants nodes to the source node

    Traversal path is determined from the parent with respect to the root
    node to the source node and then all descendants of the source.

    Directed graphs and/or is_masked behaviour: masked descendant linage's
    or linage's unreachable by directed edges are not returned.

    :param graph:        Graph to perform calculation for
    :type graph:         Graph class instance
    :param nid:          source node to start search from
    :type nid:           :py:int
    :param root:         root node for the search
    :type root:          :py:int
    :param include_self: include source nid in results
    :type include_self:  :py:bool
    """

    # Get nid child nodes to start descendants walk from
    # Add self to avoid backtracking during the walk
    start = node_children(graph, nid, root, include_self=True)

    def _walk(child_nid):
        ch = node_neighbors(graph, child_nid)
        for c in ch:
            if c not in start:
                start.append(c)
                _walk(c)

    # Start descendants walk from child nodes
    for cid in [i for i in start if not i == nid]:
        _walk(cid)

    if not include_self:
        start.remove(nid)

    return start


def node_leaves(graph, include_isolated=False):
    """
    Return all leaf nodes in the graph

    Selects all nodes in the graph that are connected to one other node
    using a directed or undirected edge.
    The first selection may also include isolated nodes being nodes without any
    edge to other nodes or one edge in opposite direction. These are
    subsequently removed because they are technically no 'leaves' of a parent
    node. However, is 'include_isolated' is True, they are returned

    Graph root nodes do not affect the character of a node being a leaf,
    directed graphs will if the edge goes from leaf to parent only as this
    effectively isolates the node from the parents.

    :param graph:            Graph to perform calculation for
    :type graph:             Graph class instance
    :param include_isolated: Include isolated nodes in the result
    :type include_isolated:  :py:bool

    :return:                 leaf node nids
    :rtype:                  :py:list
    """

    # Select all true leaves
    if not include_isolated:
        leaves = [node for node in graph.nodes() if len(graph.adjacency.get(node, [])) == 1]
        leaves = [leaf for leaf in leaves if (graph.adjacency[leaf][0], leaf) in graph.edges]

    # Or include isolated ones
    else:
        leaves = [node for node in graph.nodes() if len(graph.adjacency.get(node, [])) <= 1]

    return leaves


def node_parent(graph, nid, root):
    """
    Get the parent node of the source node relative to the graph root
    when following the shortest path (Dijkstra shortest path).

    This function always uses the full graph to return the parent.
    For masked graphs, check afterwards if the parent is in the graph
    node view or use the GraphAxis 'parent' method that performs that
    check.

    :param graph:  Graph to perform calculation for
    :type graph:   Graph class instance
    :param nid:    source node to start search from
    :type nid:     :py:int
    :param root:   root node for the search
    :type root:    :py:int

    :return:       parent node
    :rtype:        Graph object
    """

    shortest_path = dijkstra_shortest_path(graph._full_graph, root, nid)
    if len(shortest_path) > 1 and shortest_path[-1] == nid:
        return shortest_path[-2]
    return None


def node_all_parents(graph, nid, root):
    """
    Get all parent nodes to the source node relative to the graph root

    Directed graphs and/or is_masked behaviour: masked nodes or directed
    nodes not having an edge from source to node will not be returned.

    :param graph:  Graph to perform calculation for
    :type graph:   Graph class instance
    :param nid:    source node to start search from
    :type nid:     :py:int
    :param root:   root node for the search
    :type root:    :py:int

    :return:       parent node nids
    :rtype:        :py:list
    """

    # Get all paths to the target node
    all_adjacent = []
    for path in dfs_paths(graph, root, nid):
        all_adjacent.extend(path)
    all_adjacent = set(all_adjacent)

    all_parents = [key for key in node_neighbors(graph, nid) if key in all_adjacent]
        
    return all_parents


def node_siblings(graph, nid, root):
    """
    Get the siblings of the source node

    Directed graphs and/or is_masked behaviour: masked nodes or directed
    nodes not having an edge from source to node will not be returned.

    :param graph:  Graph to perform calculation for
    :type graph:   Graph class instance
    :param nid:    source node to start search from
    :type nid:     :py:int
    :param root:   root node for the search
    :type root:    :py:int

    :return:       sibling node nids
    :rtype:        :py:list
    """

    # Siblings are all children of the nid parent except self.
    parent = node_parent(graph, nid, root)
    siblings = []
    if parent is not None:
        if graph.is_masked:
            siblings = [n for n in node_children(graph._full_graph, parent, graph.root)
                        if not n == nid and n in graph.nodes]
        else:
            siblings = [n for n in node_children(graph._full_graph, parent, graph.root) if not n == nid]

    return siblings
