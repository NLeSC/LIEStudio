# -*- coding: utf-8 -*-

"""
file: graph.py

Graph base class implementing a graph based data storage with support
for dictionary like storage of data in graph nodes and edges, rich
graph comparison, query and traversal method and a Object Relations
Mapper.
"""

from __future__ import unicode_literals

import collections
import copy
import logging as logger
import weakref

from lie_graph.graph_storage_drivers.graph_dict import DictStorage
from lie_graph.graph_mixin import NodeTools, EdgeTools
from lie_graph.graph_orm import GraphORM
from lie_graph.graph_algorithms import nodes_are_interconnected
from lie_graph.graph_math_operations import graph_union, graph_update
from lie_graph.graph_helpers import (GraphException, adjacency_to_edges, edge_list_to_adjacency,
                                     edge_list_to_nodes, make_edges)


class Graph(object):
    """
    Graph base class

    *Graph root*
    By default a graph is an undirected and non-rooted network of nodes.
    Many graph methods however require the definition of a root relative to
    which a calculation will be performed.

    The graph class defines a `root` attribute for this purpose that is
    undefined by default. It will be set automatically in the following cases:

    * Node traversal: the first node selected (getnodes method) will be assigned
      root and traversal to `child` nodes will be done relative to the `root`.
      If multiple nodes are selected using `getnodes`, the root node is
      ambiguous and will be set to the node with the lowest nid.
    """

    def __init__(self, adjacency=None, nodes=None, edges=None, orm=None, root=None, is_directed=False,
                 auto_nid=True, edge_key_tag='label', node_key_tag='key', node_value_tag='value'):
        """
        Implement class __init__

        Initiate empty DictStorage for the adjacency, nodes and edges.
        Update these objects with any adjacency, nodes or edges DictStorage
        objects passed as argument.

        :param adjacency:     object that stores the dictionary of node/edges
                              ID pairs. This is the graph adjacency.
                              Adjacency is optional and will be constructed
                              from edges by default.
        :type adjacency:      DictStorage instance
        :param nodes:         object that stores the dictionary of node ID/node
                              data pairs
        :type nodes:          DictStorage instance
        :param edges:         object that stores the dictionary of edge ID/edge
                              data pairs
        :type edges:          DictStorage instance
        :param orm:           graph Object Relations Mapper
        :type orm:            GraphORM object
        :param is_directed:   Rather the graph is directed or undirected
        :type is_directed:    :py:bool
        :param auto_nid:      Use integers as node ID, automatically assigned
                              and internally managed. If False, the node object
                              added will itself be used as node ID as long as
                              it is hashable. In the latter case, nodes are
                              enforced to be unique, duplicate nodes will be
                              ignored.
        :type auto_nid:       :py:bool
        :param node_key_tag:  dictionary key used to store node data key
        :type node_key_tag:   :py:str
        :param node_value_tag:dictionary key used to store node data value
        :type node_value_tag: :py:str
        :param edge_key_tag:  dictionary key used to store edge data
        :type edge_key_tag:   :py:str
        :param root:          root node nid used by various methods when
                              traversing the graph in a directed fashion where
                              the notion of a parent is important.
        :type root:           mixed
        """

        self.orm = orm or GraphORM()
        self.nodes = DictStorage(nodes)
        self.edges = DictStorage(edges)
        self.adjacency = DictStorage(adjacency)

        # Adjacency is optional and can be constructed from edges.
        if not adjacency and edges:
            self._set_adjacency()

        # Graph attributes, set directly
        self.is_directed = is_directed
        self.is_masked = False
        self.auto_nid = auto_nid
        self.root = root
        self.edge_key_tag = edge_key_tag
        self.node_key_tag = node_key_tag
        self.node_value_tag = node_value_tag
        self.node_tools = NodeTools
        self.edge_tools = EdgeTools

        # Graph internal attributes, do not set manually.
        # Automatically assigned node ID's always increment the highest
        # integer ID in the graph
        self._nodeid = 1
        self._set_auto_nid()
        self._full_graph = self
        self._initialised = True

    def __add__(self, other):
        """
        Implement class __add__, addition (+).

        :param other: other Graph instance
        :return:      new graph combining self and other
        :rtype:       Graph instance
        """

        if not isinstance(other, Graph):
            GraphException(
                "Object {0} not instance of Graph base class".format(
                    type(other).__name__))
            return

        newgraph = self.copy()
        newgraph = graph_union(newgraph, other)

        return graph_update(newgraph, other)

    def __contains__(self, other):
        """
        Implement class __contains__

        Test if other is identical to, or a subgraph of self with respect to
        its topology (adjacency).

        .. warning:: This comparison is based on identity in node ID in the
                     graph adjacency, not node or edge attributes.
        """

        if not isinstance(other, Graph):
            logger.error(
                "Object {0} not instance of Graph base class".format(
                    type(other).__name__))
            return False

        other_nodes_keys = set(other.nodes.keys())
        self_nodes_keys = set(self.nodes.keys())
        other_edges_keys = set(other.edges.keys())
        self_edges_keys = set(self.edges.keys())

        return all((
            other_nodes_keys.issubset(self_nodes_keys),
            other_edges_keys.issubset(self_edges_keys)))

    def __copy__(self, memo={}):
        """
        Copy directives for this class
        """

        return self.copy()

    def __deepcopy__(self, memo={}):
        """
        Deepcopy directives for this class
        """

        return self.copy(deep=True)

    def __eq__(self, other):
        """
        Implement class __eq__

        Evaluate equality based on graph topology (adjacency)

        .. warning:: This comparison is based on identity in node ID in the
                     graph adjacency, not node or edge attributes.
        """

        if self.adjacency.keys() != other.adjacency.keys():
            return False

        return all(
            set(self.adjacency[i]) == set(other.adjacency[i])
            for i in self.adjacency)

    def __getitem__(self, key):
        """
        Implement class __getitem__

        Return nodes or edges in a (sub)graph by dictionary lookup.
        This function is overloaded in (sub)graphs containing single nodes or
        edges to provide access to node or edge attributes.

        :return: nodes or edges.
        :rtype:  Node ID as integer or edge ID as tuple of 2 node ID's.
        """

        if type(key) in (tuple, list):
            return self.getedges(key)

        return self.getnodes(key)

    def __ge__(self, other):
        """
        Implement class __ge__

        Evaluate greater-then or equal equality based on graph topology (edges)
        """

        return self.edges.keys() >= other.edges.keys()

    def __gt__(self, other):
        """
        Implement class __gt__

        Evaluate greater-then equality based on graph topology (edges)
        """

        return self.edges.keys() > other.edges.keys()

    def __iadd__(self, other):
        """
        Implements class __iadd__, inplace addition (+=).

        Calls the class `add` method

        :param other: other Graph instance
        :return:      self combined with other
        :rtype:       Graph instance
        """

        if not isinstance(other, Graph):
            GraphException(
                "Object {0} not instance of Graph base class".format(
                    type(other).__name__))
            return

        newgraph = graph_union(self, other)

        return graph_update(newgraph, other)

    def __isub__(self, other):
        """
        Implement class __isub__, inplace subtraction (-=).

        :param other: other Graph instance
        :return:      self with other subtracted
        :rtype:       Graph instance
        """

        self.remove_nodes(other.nodes.keys())

        return self

    def __iter__(self):
        """
        Implement class __iter__

        Iterate over nodes using iternodes

        :return: single node Graph
        :rtype:  :lie_graph:Graph
        """

        return self.iternodes()

    def __len__(self):
        """
        Implement class __len__

        Represent the length of the graph as the number of nodes

        :return: number of nodes
        :rtype:  int
        """

        return len(self.nodes)

    def __le__(self, other):
        """
        Implement class __le__

        Evaluate less-then or equal to equality based on graph topology (edges)
        """

        return self.edges.keys() <= other.edges.keys()

    def __lt__(self, other):
        """
        Implement class __lt__

        Evaluate less-then equality based on graph topology (edges)
        """

        return self.edges.keys() < other.edges.keys()

    def __ne__(self, other):
        """
        Implement class __ne__

        Evaluate non-equality in graph topology (adjacency)

        .. warning:: This comparison is based on identity in node ID in the
                     graph adjacency, not node or edge attributes.
        """

        return not self.__eq__(other)

    def __repr__(self):
        """
        Implement class __repr__

        String representation of the class listing node and edge count.

        :rtype: :py:str
        """

        msg = '<{0} object {1}: {2} nodes, {3} edges>'
        edges = sum([len(self.adjacency[n]) for n in self.nodes])

        return msg.format(
            type(self).__name__, id(self), len(self.nodes), edges)

    def __sub__(self, other):
        """
        Implement class __sub__, subtraction (-).

        :param other: other Graph instance
        :return:      new graph with other subtracted
        :rtype:       Graph instance
        """

        new_graph = self.copy()
        new_graph.remove_nodes(other.nodes.keys())

        return new_graph

    @classmethod
    def _get_class_object(cls):
        """
        Returns the current class object. Used by the graph ORM to construct
        new Graph based classes
        """

        return cls

    def _set_auto_nid(self):
        """
        Set the automatically assigned node ID (nid) based on the nids in the
        current graph
        """

        if len(self.adjacency):
            self._nodeid = max(i if isinstance(i, int) else 0 for i in self.adjacency) + 1

    def _set_full_graph(self, graph):
        """
        Set a weak reference to the full graph

        :param graph: Graph instance
        """

        if isinstance(graph, Graph):
            self._full_graph = weakref.ref(graph._full_graph)()

    def _set_adjacency(self):
        """
        (re)create the adjacency list from the graph edges
        """

        self.adjacency = DictStorage(edge_list_to_adjacency(self.edges.keys()))

    def add_edge(self, nd1, nd2=None, directed=None, node_from_edge=False, **kwargs):
        """
        Add edge between two nodes to the graph

        An edge is defined as a connection between two node ID's.
        Edge metadata defined as a dictionary allows it to be queried
        by the various graph query functions.

        :param nd1:            edge defined by two node ID's. nd1 may also be
                               an edge tuple/list ignoring nd2
        :type nd1:             int or tuple/list
        :param nd2:            edge defined by two node ID's. nd1 may also be
                               an edge tuple/list ignoring nd2
        :type nd2:             :py:int
        :param directed:       override the graph definition for is_directed
                               for the added edge.
        :type directed:        :py:bool
        :param node_from_edge: make node for edge node id's not in graph
        :type node_from_edge:  :py:bool
        :param kwargs:         any additional keyword arguments to be added as
                               edge metadata.

        :return:               edge ID
        :rtype:                :py:tuple
        """

        if isinstance(nd1, list) or isinstance(nd1, tuple):
            nd2 = nd1[1]
            nd1 = nd1[0]

        for nodeid in (nd1, nd2):
            if nodeid not in self.adjacency:
                if node_from_edge:
                    self.add_node(nodeid)
                else:
                    assert nodeid in self.adjacency, logger.error('Node with id {0} not in graph.'.format(nodeid))

        # Create edge tuples, directed or un-directed (local override possible for mixed graph).
        if directed is None:
            directed = self.is_directed
        edges_to_add = make_edges((nd1, nd2), directed=directed)

        for edge in edges_to_add:
            if edge in self.edges:
                logger.warning('Edge between nodes {0}-{1} exists. Use edge update to change attributes.'.format(*edge))
                continue

            # Make a deepcopy of the added attributes
            self.edges[edge] = copy.deepcopy(kwargs)

            # Add target node as neighbour of source node in graph
            # adjacency object
            # This operation is always directed.
            if not edge[1] in self.adjacency[edge[0]]:
                self.adjacency[edge[0]].append(edge[1])

            logger.debug('Add edge between node {0}-{1}'.format(*edge))

        return edges_to_add[0]

    def add_edges(self, edges, **kwargs):
        """
        Add multiple edges to the graph.

        This is the iterable version of the add_edge methods allowing
        multiple edge additions from any iterable.

        :param edges: Objects to be added as edges to the graph
        :type edges: Iterable of hashable objects
        :return: list of edge ids for the objects added in the same
               order as th input iterable.
        :rtype: list
        """

        if isinstance(edges, dict):
            edges = [(k[0], k[1], v) for k, v in edges.items()]

        edges_added = []
        for e in edges:
            pred = len(e) in (2, 3)
            msg = 'Edge needs to contain two nodes and optional arguments, got: {0}'
            err = logger.error(msg.format(e))

            assert pred, err
            edges_added.append(self.add_edge(*e, **kwargs))

        return edges_added

    def add_node(self, node=None, **kwargs):
        """
        Add a node to the graph

        All nodes are stored using a dictionary like data structure like:

            {nid: {'_id': auto_nid, attribute_key: attribute_value, ....}}

        Where the nid is the unique node ID stored as node key that can be any
        hashable object except None. The value is a dictionary that contains
        at least the '_id' attribute representing a unique auto-incremented
        integer node identifier and any additional arguments as key/value
        pairs. The '_id' attribute is added automatically.
        The API used to access stored node information reassembles a Python
        dictionary like API. The method used to store data is determined by
        the graph storage driver.

        Node ID and node attributes
        The nid is the primary way of identifying a node. If the nid is
        automatically assigned (auto_nid) but `node` is defined, this data
        is stored as attribute using the `node_key_tag` as key unless over
        loaded by any of the supplied attributes.
        Using the node_key_tag and node_value_tag is a convenient way of
        storing node data that should be accessible using the same key.
        The node_key_tag and node_value_tag are used as default in the various
        dictionary style set and get methods of the graph, node and edge
        classes.

        .. note:: 'add_node' checks if there is a node with nid in the graph
                  already. If found, a warning is logged and the attributes
                  of the existing node are updated.

        :param node:     object representing the node
        :type node:      any hashable object
        :param kwargs:   any additional keyword arguments to be added as
                         node attributes.
        :return:         node ID (nid)
        :rtype:          int
        """

        # If not auto_nid and not node that we cannot continue
        if not self.auto_nid and node is None:
            raise GraphException('Node ID required when auto_nid is disabled')

        # Use internal nid or node as node ID
        if self.auto_nid:
            nid = self._nodeid
        else:
            nid = node

            # Node needs to be hashable
            if not isinstance(node, collections.Hashable):
                raise GraphException('Node {0} of type {1} not a hashable object'.format(nid, type(node).__name__))

            # If node exist, log a warning, update attributes and return
            if nid in self.nodes:
                logger.warning('Node {0} already assigned'.format(nid))
                self.nodes[nid].update(copy.deepcopy(kwargs))
                return nid

        logger.debug('Add node. id: {0}, type: {1}'.format(nid, type(node).__name__))

        # Prepare node data dictionary
        node_data = {}
        if self.auto_nid:
            node_data[self.node_key_tag] = node
        node_data.update(copy.deepcopy(kwargs))

        # Always set a unique ID to the node
        node_data['_id'] = self._nodeid

        self.adjacency[nid] = []
        self.nodes[nid] = node_data

        # Always increment internal node ID by 1
        self._nodeid += 1

        return nid

    def add_nodes(self, nodes, **kwargs):
        """
        Add multiple nodes to the graph.

        This is the iterable version of the add_node methods allowing
        multiple node additions from any iterable.

        :param nodes: Objects to be added as nodes to the graph
        :type nodes: Iterable of hashable objects
        :return: list of node ids for the objects added in the same
               order as th input iterable.
        :rtype: list
        """

        node_collection = []
        for node in nodes:
            node_collection.append(self.add_node(node, **kwargs))

        return node_collection

    def attr(self, key, copy_attr=False):
        """
        Provides direct access to a node or edge attribute by ID.

        It returns a reference to the original data source unless the copy_attr
        attribute equals True in case it will return a deepcopy of the
        dictionary.

        :param key:       node or edge identifier to return data for
        :type key:        mixed
        :param copy_attr: Return a deep copy of the data dictionary
        :type copy_attr:  :py:bool

        :return:          Node or edge attribute.
        :rtype:           Node ID as integer or edge ID as tuple of 2 node ID's
        """

        data_dict = None
        if isinstance(key, tuple) or isinstance(key, list):
            key = tuple(key)
            if self.is_masked:
                data_dict = self.edges.get(key)
            data_dict = self._full_graph.edges.get(key)
        elif self.is_masked:
            data_dict = self.nodes.get(key)
        else:
            data_dict = self._full_graph.nodes.get(key)

        if copy_attr:
            return copy.deepcopy(data_dict)
        return data_dict

    def clear(self):
        """
        Clear nodes and edges in the graph.

        If the Graph instance represents a sub graph, only those nodes and edges
        will be removed.
        """

        self.nodes.clear()
        self.edges.clear()
        self.adjacency.clear()

        # Reset node ID counter if the full graph is cleared
        if len(self) == len(self._full_graph):
            self._nodeid = 0

    def copy(self, deep=True, copy_view=True, clean=True):
        """
        Return a (deep) copy of the graph

        A normal copy is a shallow copy that will copy the class and its
        attributes except for the nodes, edges and _full_graph objects that
        are referenced.

        If 'deep' equals true, a deepcopy of the class and its attributes is
        made. The new graph has _full_graph referenced to itself.
        A deep copy of graph returns a new graph that should be self
        consistent. If a subgraph is copied this way it may contain edges
        between nodes that are not in the sub graph. These are removed by
        default (clean attribute)

        :param deep:        return a deep copy of the Graph object
        :type deep:         :py:bool
        :param copy_view:   make a deep copy of the full nodes, edges and
                            adjacency dictionary and set any 'views'.
                            Otherwise, only make a deep copy of the 'view'
                            state.
        :type copy_view:    :py:bool
        :param clean:       Remove non-existing edges
        :type clean:        :py:bool

        :return:            copy of the graph
        :rtype:             Graph object
        """

        # Make a new instance of the current class
        base_cls = self._get_class_object()

        # Make a deep copy
        if deep:
            class_copy = base_cls()

            class_copy.nodes.update(
                copy.deepcopy(self.nodes.to_dict(return_full=True)))
            if copy_view:
                class_copy.nodes._view = copy.deepcopy(self.nodes._view)

            class_copy.edges.update(copy.deepcopy(
                self.edges.to_dict(return_full=True)))
            if copy_view:
                class_copy.edges._view = copy.deepcopy(self.edges._view)

            if clean:
                nids = set(class_copy.nodes.keys())
                for edge in [e for e in class_copy.edges.keys()]:
                    if not set(edge).issubset(nids):
                        del class_copy.edges[edge]

            # If clean, rebuild adjacency
            if clean:
                class_copy._set_adjacency()
            else:
                class_copy.adjacency.update(
                    copy.deepcopy(self.adjacency.to_dict(return_full=True)))
                if copy_view:
                    class_copy.adjacency._view = copy.deepcopy(
                        self.adjacency._view)

            class_copy.orm = copy.deepcopy(self.orm)

        # Make a shallow copy
        else:
            class_copy = base_cls(
                adjacency=self.adjacency, nodes=self.nodes, edges=self.edges,
                orm=self.orm)
            class_copy._full_graph = self._full_graph

        # Copy all class attributes except 'adjacency','nodes', 'edges',
        # '_full_graph and orm
        notcopy = ('adjacency', 'edges', 'nodes', '_full_graph', 'orm')
        for k, v in self.__dict__.items():
            if k not in notcopy:
                class_copy.__dict__[k] = copy.deepcopy(v)

        # Reset the graph root if needed
        if class_copy.root and class_copy.root not in class_copy.nodes:
            class_copy.root = min(class_copy.nodes)
            logger.debug('Reset graph root to {0}'.format(class_copy.root))

        logger.debug(
            'Return {0} copy of graph {1}'.format('deep' if deep else 'shallow', repr(self)))

        return class_copy

    def empty(self):
        """
        Report if the graph is empty (no nodes)

        :rtype: :py:bool
        """

        return len(self) == 0

    def get(self, nid, key=None, defaultattr=None, default=None):
        """
        Return (sub)graph values.

        This is a placeholder method that can be overloaded by custom classes
        to return a value for (sub)graphs containing more than one edge or
        node in contrast to the single node or edge graph classes for which
        the get method returns attribute values.
        The `get` method has the latter functionality by default and will
        return single node or edge attributes based on nid.

        :param nid:         node or edge identifier to return data for. If not
                            defined attempt to resolve using `nid` property.
        :type nid:          mixed
        :param key:         node or edge value attribute name. If not defined
                            then attempt to use class wide `node_key_tag`
                            attribute.
        :type key:          mixed
        :param defaultattr: node or edge value attribute to use as source of
                            default data when `key` attribute is not present.
        :type defaultattr:  mixed
        :param default:     value to return when all fails
        :type default:      mixed
        """

        # Return node or edge data
        target = self.attr(nid)

        # Get key or default class node/edge data key
        if isinstance(nid, tuple) or isinstance(nid, list):
            key = key or self.edge_key_tag
        else:
            key = key or self.node_key_tag

        if key in target:
            return target[key]
        return target.get(defaultattr, default)

    def getedges(self, edges, orm_cls=None):
        """
        Get an edge as graph object

        Returns a new graph view object for the given edge and it's nodes.
        If `is_masked` equals True the new graph object will represent
        a fully isolated sub graph for the edges, the connected nodes and the
        adjacency using views on the respective nodes, edges and adjacency
        DictStorage instances.
        If `is_masked` equals False only the edges DictStorage will represent
        the sub graph as a view but nodes and adjacency will represent the full
        graph. As such, connectivity with the full graph remains.

        Getedges calls the Graph Object Relation Mapper (GraphORM) class
        to customize the returned (sub) Graph class. Next to the custom classes
        registered with the ORM mapper, the `getedges` method allows for
        further customization of the returned Graph object through the
        orm_cls attribute. In addition, for sub graphs containing single edges,
        the EdgeTools class is added.

        :param edges:   edge id
        :type edges:    iterable of length 2 containing integers
        :param orm_cls: custom classes to construct new edge oriented Graph
                        class from.
        :type orm_cls:  list
        """

        # Coerce to list
        if all(type(e) in (tuple, list) for e in edges):
            edges = [tuple(e) for e in edges]
        elif len(edges) == 2:
            edges = [tuple(edges)]

        # Edges need to be in graph
        if edges:
            edges_not_present = [e for e in edges if e not in self.edges]
            if edges_not_present:
                raise GraphException(
                    'Following edges are not in graph {0}'.format(
                        edges_not_present))
        else:
            edges = []

        # Build custom class list. Default NodeTools need to be included in
        # case of single nodes and not overloaded in MRO.
        custom_orm_cls = []
        if orm_cls:
            if not isinstance(orm_cls, list):
                msg = 'Custom edge classes need to be defined as list'
                raise GraphException(msg)
            custom_orm_cls.extend(orm_cls)
        if len(edges) == 1:
            custom_orm_cls.append(self.edge_tools)

        base_cls = self.orm.get(
            self, edges, self._get_class_object(), classes=custom_orm_cls)
        w = base_cls(
            adjacency=self.adjacency, nodes=self.nodes, edges=self.edges,
            orm=self.orm)

        w.edges.set_view(edges)

        # Get nodes and adjacency for the edge selection if it represents
        # an isolated graph
        if self.is_masked:
            adjacency = edge_list_to_adjacency(edges)
            w.nodes.set_view(adjacency.keys())
            w.adjacency = DictStorage(adjacency)

        # copy class attributes
        for key, value in self.__dict__.items():
            if key not in ('nodes', 'edges', 'orm', 'adjacency'):
                w.__dict__[key] = value
        w._set_full_graph(self)

        return w

    def getnodes(self, nodes, orm_cls=None):
        """
        Get one or multiple nodes as new sub graph object

        Returns a new graph view object for the given node and it's edges.
        If `is_masked` equals True the new graph object will represent
        a fully isolated sub graph for the nodes, the edges that connect them
        and the adjacency using views on the respective nodes,
        edges and adjacency DictStorage instances.
        If `is_masked` equals False only the nodes DictStorage will represent
        the subgraph as a view but edges and adjacency will represent the full
        graph. As such, connectivity with the full graph remains.
        If nodes equals None or empty list, the returned Graph object will have
        no nodes and is basically 'empty'.

        Getnodes calls the Graph Object Relation Mapper (GraphORM) class
        to customize the returned (sub) Graph class. Next to the custom classes
        registered with the ORM mapper, the `getnodes` method allows for
        further customization of the returned Graph object through the
        orm_cls attribute. In addition, for sub graphs containing single nodes,
        the NodeTools class is added.

        :param nodes:   node id
        :param orm_cls: custom classes to construct new node oriented Graph
                        class from.
        :type orm_cls:  list
        """

        # Coerce to list
        if not isinstance(nodes, (tuple, list)) and nodes:
            nodes = [nodes]

        # Nodes need to be in graph
        if nodes:
            nodes_not_present = [n for n in nodes if n not in self.adjacency]
            if nodes_not_present:
                raise GraphException('Following nodes are not in graph {0}'.format(nodes_not_present))
        else:
            nodes = []

        # Build custom class list. Default NodeTools need to be included in
        # case of single nodes and not overloaded in MRO.
        custom_orm_cls = []
        if orm_cls:
            if not isinstance(orm_cls, list):
                raise GraphException('Custom node classes need to be defined as list')
            custom_orm_cls.extend(orm_cls)
        if len(nodes) == 1:
            custom_orm_cls.append(self.node_tools)

        base_cls = self.orm.get(self, nodes, self._get_class_object(), classes=custom_orm_cls)
        w = base_cls(adjacency=self.adjacency, nodes=self.nodes, edges=self.edges, orm=self.orm)
        w.nodes.set_view(nodes)

        # Get edges and adjacency for the node selection if it represents
        # an isolated graph
        if self.is_masked:
            edges = adjacency_to_edges(nodes, self.adjacency, nodes)
            w.edges.set_view(edges)

            if edges:
                w.adjacency = DictStorage(edge_list_to_adjacency(edges))
            else:
                w.adjacency = DictStorage(dict([(n, []) for n in nodes]))

        # copy class attributes
        for key, value in self.__dict__.items():
            if key not in ('nodes', 'edges', 'orm', 'adjacency'):
                w.__dict__[key] = value
        w._set_full_graph(self)

        # If root node set and is_masked, reset root to node in new sub(graph)
        # to prevent a root node that is not in the new subgraph.
        if w.root is not None and self.is_masked:
            if w.root not in w.nodes() and len(w.nodes):
                w.root = min(w.nodes[n].get('_id', n) for n in w.nodes())

        return w

    def insert(self, node, between):
        """
        Insert a new node in between two other

        :param node:    node to add
        :param between: nodes to add new node in between
        """

        if len(between) > 2:
            raise Exception('Insert is only able to insert between two nodes')

        if nodes_are_interconnected(self, between):
            nid = self.add_node(node)
            for n in between:
                self.add_edge((nid, n))

            del self.edges[between]

    def iteredges(self, orm_cls=None):
        """
        Graph edge iterator

        Returns a new graph view object for the given edge and it's nodes.

        :param orm_cls: custom classes to construct new Graph class from for
                        every edge that is returned
        :type orm_cls:  list
        """

        for edge in self.edges:
            yield self.getedges(edge, orm_cls=orm_cls)

    def iternodes(self, orm_cls=None):
        """
        Graph node iterator

        Returns a new graph view object for the given node and it's edges.
        The dynamically created object contains additional node tools.
        Nodes are returned in node ID sorted order.

        :param orm_cls: custom classes to construct new Graph class from for
                        every node that is returned
        :type orm_cls:  list
        """

        for node in sorted(self.nodes.keys()):
            yield self.getnodes(node, orm_cls=orm_cls)

    def query_edges(self, query=None, orm_cls=None, **kwargs):
        """
        Select nodes and edges based on edge data query

        :param query:   dictionary of edge data key/value pairs to query on
        :type query:    dict
        :param orm_cls: custom classes to construct new Graph class from.
        :type orm_cls:  list
        """

        # Build query
        query_set = []
        if isinstance(query, dict):
            query_set.extend(query.items())
        query_set.extend(kwargs.items())

        query_set = set(query_set)
        edges = []
        for edge, attr in sorted(self.edges.items()):
            if all([q in attr.items() for q in query_set]):
                edges.append(edge)

        return self.getedges(edges, orm_cls=orm_cls)

    def query_nodes(self, query=None, orm_cls=None, **kwargs):
        """
        Select nodes and edges based on node data query

        The `getnodes` method is called for the nodes matching the query

        :param query:   dictionary of node data key/value pairs to query
        :type query:    dict
        :param orm_cls: custom classes to construct new Graph class from.
        :type orm_cls:  list
        """

        # Build query
        query_set = []
        if isinstance(query, dict):
            query_set.extend(query.items())
        query_set.extend(kwargs.items())

        query_set = set(query_set)
        nodes = []
        for node, attr in sorted(self.nodes.items()):
            if all([q in attr.items() for q in query_set]):
                nodes.append(node)

        nodes = list(set(nodes))
        return self.getnodes(nodes, orm_cls=orm_cls)

    def remove_edge(self, nd1, nd2=None, directed=None):
        """
        Removing an edge from the graph

        Checks if the graph contains the edge, then removes it.
        If the graph is undirectional, try to remove both edges
        of the undirectional pair.
        Force directed removal of the edge using the 'directed' argument.
        Useful in mixed (un)-directional graphs.

        :param nd1:      edge defined by two node ID's. nd1 may also be
                         an edge tuple/list ignoring nd2
        :type nd1:       int or tuple/list for nd1
        :param nd2:      second node ID in edge definition, may be None
                         if nd1 is a tuple/list
        :type nd2:       :py:int
        :param directed: force directed removal of the edge
        :type directed:  :py:bool
        """

        if not (isinstance(nd1, list) or isinstance(nd1, tuple)):
            nd1 = (nd1, nd2)

        if not isinstance(directed, bool):
            directed = self.is_directed

        # Make edges, directed or undirected based on graph settings
        for edge in make_edges(nd1, directed=directed):
            if edge in self.edges:
                # Remove from adjacency list
                if edge[1] in self.adjacency[edge[0]]:
                    self.adjacency[edge[0]].remove(edge[1])
                else:
                    msg = 'Node {0} not part of edge list node {1}'
                    logger.warning(msg.format(*edge))

                del self.edges[edge]
                logger.debug('Removed edge {0} from graph'.format(edge))
            else:
                logger.warning(
                    'Unable to remove edge {0}. No such edge ID'.format(edge))

    def remove_edges(self, edges):
        """
        Remove multiple edges from the graph.

        This is the iterable version of the remove_edge methods allowing
        mutliple edge removal from any iterable.

        :param edges: Iterable of edges to remove
        :type edges: Iterable of edges defined as tuples of two node ID's
        """

        for edge in edges:
            self.remove_edge(edge)

    def remove_node(self, node):
        """
        Removing a node from the graph

        Checks if the graph contains the node and if the node is connected with
        edges. Removes the node and associated edges.

        :param node: Node to remove
        :type node: mixed
        """

        if node in self.adjacency:

            # Get edges connected to node and remove them
            edges = [edge for edge in self.edges if node in edge]
            for edge in edges:
                del self.edges[edge]

            # Remove node from other nodes adjacency list
            adj_list = [e for e in edge_list_to_nodes(edges) if not e == node]
            for adj in adj_list:
                if node in self.adjacency[adj]:
                    self.adjacency[adj].remove(node)

            # Remove node from adjacency and nodes object
            del self.adjacency[node]
            del self.nodes[node]

            msg = 'Removed node {0} with {1} connecting edges from graph'
            logger.debug(msg.format(node, len(edges)))

        else:
            msg = 'Unable to remove node {0}. No such node ID'.format(node)
            logger.warning(msg)

    def remove_nodes(self, nodes):
        """
        Remove multiple nodes from the graph.

        This is the iterable version of the remove_node methods allowing
        multiple nodes to be removed from any iterable.

        :param nodes: Nodes to remove
        :type nodes: mixed
        """

        for node in nodes:
            self.remove_node(node)

    # DICTIONARY LIKE NODE ACCESS
    def items(self, keystring=None, valuestring=None):
        """
        Python dict-like function to return node items in the (sub)graph.

        Keystring defines the value lookup key in the node data dict.
        This defaults to the graph node_key_tag.
        Valuestring defines the value lookup key in the node data dict.

        :param keystring:   Data key to use for dictionary keys.
        :type keystring:    :py:str
        :param valuestring: Data key to use for dictionary values.
        :type valuestring:  :py:str

        :return:            List of keys, value pairs
        :rtype:             :py:list
        """

        keystring = keystring or self.node_key_tag
        valuestring = valuestring or self.node_value_tag

        return [(n.get(keystring), n.get(valuestring)) for n in self.iternodes()]

    def keys(self, keystring=None):
        """
        Python dict-like function to return node keys in the (sub)graph.

        Keystring defines the value lookup key in the node data dict.
        This defaults to the graph node_key_tag.

        :param keystring:   Data key to use for dictionary keys.
        :type keystring:    :py:str

        :return:            List of keys
        :rtype:             :py:list
        """

        keystring = keystring or self.node_key_tag
        return [n.get(keystring) for n in self.iternodes()]

    def values(self, valuestring=None):
        """
        Python dict-like function to return node values in the (sub)graph.

        Valuestring defines the value lookup key in the node data dict.

        :param valuestring: Data key to use for dictionary values.
        :type valuestring:  :py:str

        :return:            List of values
        :rtype:             :py:list
        """

        valuestring = valuestring or self.node_value_tag
        return [n.get(valuestring) for n in self.iternodes()]
