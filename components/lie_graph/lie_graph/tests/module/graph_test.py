# -*- coding: utf-8 -*-

"""
file: module_graph_test.py

Unit tests for the Graph base class
"""

import copy
import os
import types
import unittest2

from lie_graph import Graph
from lie_graph.graph import GraphException
from lie_graph.graph_io.io_tgf_format import read_tgf


class TestGraph(unittest2.TestCase):
    currpath = os.path.dirname(__file__)
    _gpf_graph = os.path.join(currpath, '../', 'files', 'graph.tgf')

    def setUp(self):
        """
        ConfigHandlerTests class setup

        Load graph from graph.tgf file
        """

        self.graph = read_tgf(self._gpf_graph)

    def test_autonid_node_addition(self):
        """
        Test single node addition using automatic assigned node ID
        """

        graph = Graph()

        # Single node addition with keyword based attribute
        nid = graph.add_node(10, weight=1.2)
        self.assertEqual(nid, 1)
        self.assertTrue(nid in graph.nodes)
        self.assertItemsEqual(graph.nodes[nid], {'nid': 1, '_id': 1, 'weight': 1.2, 'data': 10})

        # Single node addition, no attributes but default ones
        nid = graph.add_node('one')
        self.assertTrue(nid in graph.nodes)
        self.assertEqual(nid, 2)
        self.assertItemsEqual(graph.nodes[nid], {'nid': 2, '_id': 2, 'data': 'one'})

        # Single node addition with a list as data and keyword based attribute
        nid = graph.add_node([1.22, 4.5, 6], **{'test': True, 'pv': 1.44})
        self.assertEqual(nid, 3)
        self.assertItemsEqual(graph.nodes[nid], {'nid': 2, '_id': 2, 'test': True, 'pv': 1.44, 'data': [1.22, 4.5, 6]})

        # Single node addition with a function as data
        nid = graph.add_node(len)
        self.assertEqual(nid, 4)
        self.assertTrue(nid in graph.nodes)
        self.assertItemsEqual(graph.nodes[nid], {'nid': 4, '_id': 4, 'data': len})

        # Single node addition using other graph as data
        nid = graph.add_node(self.graph)
        self.assertEqual(nid, 5)
        self.assertTrue(nid in graph.nodes)
        self.assertEqual(graph.nodes[nid]['data'], self.graph)

    def test_autonid_nodes_addition(self):
        """
        Test multiple node addition from any iterable using automatic assigned
        node ID
        """

        graph = Graph()

        # Multiple node additon from list all having same keyword based attribute
        nids = graph.add_nodes([2, 3, 4], time='2pm')
        self.assertEqual(nids, [1, 2, 3])
        for attr, nid in enumerate(nids, start=2):
            self.assertTrue(nid in graph.nodes)
            self.assertDictEqual(graph.nodes[nid], {'nid': nid, '_id': nid, 'data': attr, 'time': '2pm'})

        # Multiple node addition using string as iterable
        nids = graph.add_nodes('nodes')
        self.assertEqual(nids, [4, 5, 6, 7, 8])
        for attr, nid in enumerate(nids):
            self.assertTrue(nid in graph.nodes)
            self.assertDictEqual(graph.nodes[nid], {'nid': nid, '_id': nid, 'data': 'nodes'[attr]})

    def test_objectnid_node_addition(self):
        """
        Test node addition using the node itself as nid instead of automatic
        assigned node ID
        """

        graph = Graph()
        graph.auto_nid = False

        nid = graph.add_node('object')
        self.assertEqual(nid, 'object')
        self.assertTrue(nid in graph.nodes)
        self.assertItemsEqual(graph.nodes[nid], {'nid': 'object', '_id': 1, 'data': 'object'})

        self.assertRaises(GraphException, graph.add_node, [1.33, 3.4])  # Unhashable objects not accepted as nid
        self.assertRaises(GraphException, graph.add_node, 'object')  # Duplicate nid not allowed

    def test_edge_addition(self):
        """
        Test single edge addition
        """

        graph = Graph()
        graph.add_nodes([1, 2, 3, 4, 5])

        # undirectional edge addition (default)
        edge = graph.add_edge(1, 2, {'type': 'monotone'})
        self.assertEqual(edge, (1, 2))
        self.assertTrue(edge in graph.edges)
        self.assertItemsEqual(graph.edges[edge], {'type': 'monotone'})
        self.assertItemsEqual(graph.edges[(2, 1)], {'type': 'monotone'})
        self.assertEqual(graph.edges[edge]['type'], 'monotone')

        e = (2, 3)
        edge = graph.add_edge(*e)
        self.assertEqual(edge, (2, 3))
        self.assertTrue(edge in graph.edges)
        self.assertItemsEqual(graph.edges[edge], {})
        self.assertItemsEqual(graph.edges[(3, 2)], {})

        # directional edge addition
        edge = graph.add_edge(3, 4, directed=True, type='directional')
        self.assertEqual(edge, (3, 4))
        self.assertTrue(edge in graph.edges)
        self.assertFalse((4, 3) in graph.edges)
        self.assertItemsEqual(graph.edges[edge], {'type': 'directional'})
        self.assertEqual(graph.edges[edge]['type'], 'directional')

        graph.is_directed = True
        edge = graph.add_edge(3, 5, type='directional')
        self.assertEqual(edge, (3, 5))
        self.assertTrue(edge in graph.edges)
        self.assertFalse((5, 3) in graph.edges)
        self.assertItemsEqual(graph.edges[edge], {'type': 'directional'})
        self.assertEqual(graph.edges[edge]['type'], 'directional')

        # Mixed auto nid and custom nid edges
        graph.is_directed = False
        graph.auto_nid = False
        graph.add_node('object')
        edge = graph.add_edge(('object', 1))
        self.assertEqual(edge, ('object', 1))
        self.assertTrue(edge in graph.edges)

        # Create nodes from edges if they do not exist, default False
        edge = graph.add_edge(12, 13, node_from_edge=True, type='monotone')
        self.assertEqual(edge, (12, 13))
        self.assertTrue(13 in graph.nodes)
        self.assertTrue(12 in graph.nodes)

    def test_edges_addition(self):
        """
        Test multiple edge addition
        """

        graph = Graph()
        graph.add_nodes([1, 2, 3, 4, 5])

        edges = graph.add_edges([(1, 2), (2, 3), (2, 4), (4, 5), (5, 2)], type='universal')
        self.assertEqual(edges, [(1, 2), (2, 3), (2, 4), (4, 5), (5, 2)])
        for edge in edges:
            self.assertTrue(edge in graph.edges)
            self.assertDictEqual(graph.edges[edge], {'type': 'universal'})

    def test_node_removal(self):
        """
        Test single node removal
        """

        self.graph.remove_node(2)
        self.assertTrue(2 not in self.graph.nodes)
        self.assertTrue(2 not in self.graph.adjacency)
        self.assertEqual(len([e for e in self.graph.edges.keys() if 2 in e]), 0)

    def test_nodes_removal(self):
        """
        Test multiple node removal
        """

        self.graph.remove_nodes([1, 10])
        for node in (1, 10):
            self.assertTrue(node not in self.graph.nodes)
            self.assertTrue(node not in self.graph.adjacency)
            self.assertEqual(len([e for e in self.graph.edges.keys() if node in e]), 0)

    def test_edge_removal_undirected(self):
        """
        Test edge removal in a undirected graph
        """

        edge_to_remove = (3, 8)
        self.graph.remove_edge(edge_to_remove)
        self.assertTrue(edge_to_remove not in self.graph.edges)
        self.assertTrue(reversed(edge_to_remove) not in self.graph.edges)
        self.assertTrue(edge_to_remove[0] not in self.graph.adjacency[edge_to_remove[1]])
        self.assertTrue(edge_to_remove[1] not in self.graph.adjacency[edge_to_remove[0]])

    def test_edge_removal_directed(self):
        """
        Test edge removal in a directed graph
        """

        edge_to_remove = (3, 8)
        self.graph.is_directed = True
        self.graph.remove_edge(edge_to_remove)
        self.assertTrue(edge_to_remove not in self.graph.edges)
        self.assertTrue(edge_to_remove[::-1] in self.graph.edges)
        self.assertTrue(edge_to_remove[0] in self.graph.adjacency[edge_to_remove[1]])
        self.assertTrue(edge_to_remove[1] not in self.graph.adjacency[edge_to_remove[0]])

    def test_edges_removal(self):
        """
        Test multiple edge removal.
        """

        edges_to_remove = [(2, 3), (3, 8)]
        self.graph.remove_edges(edges_to_remove)
        for edge in edges_to_remove:
            self.assertTrue(edge not in self.graph.edges)
            self.assertTrue(edge[::-1] not in self.graph.edges)
            self.assertTrue(edge[0] not in self.graph.adjacency[edge[1]])
            self.assertTrue(edge[1] not in self.graph.adjacency[edge[0]])

    def test_graph_clear(self):
        """
        Test graph clear method removing all nodes, edges and adjacency
        information leaving an empty graph
        """

        self.graph.clear()
        self.assertTrue(len(self.graph.adjacency) == 0)
        self.assertTrue(len(self.graph.nodes) == 0)
        self.assertTrue(len(self.graph.edges) == 0)
        self.assertEqual(len(self.graph), 0)

    def test_graph_copy(self):
        """
        Test deepcopy of the graph. This should return a new graph class
        with graph, nodes and edges GraphDict objects having a copy of the
        original dictionary.
        """

        graph_copy1 = self.graph.copy()
        self.assertNotEqual(id(self.graph.adjacency._storage), id(graph_copy1.adjacency._storage))

        graph_copy2 = copy.deepcopy(self.graph)
        self.assertNotEqual(id(self.graph.adjacency._storage), id(graph_copy2.adjacency._storage))

    def test_graph_comparison(self):
        """
        Test graph magic method comparison operators.

        The comparison operators assess equality or differences between graphs
        by comparing graph topology based on nodes and edges (adjacency) using
        the node and edge ID's. As such they do not consider node and/or edge
        attributes.
        """

        subgraph = read_tgf(self._gpf_graph)
        subgraph.remove_nodes([1, 2, 3, 4, 5])

        # Graph topology (adjacency) based equality comparison
        self.assertFalse(subgraph == self.graph)
        self.assertTrue(subgraph != self.graph)
        self.assertTrue(self.graph == self.graph)
        self.assertFalse(self.graph != self.graph)
        self.assertTrue(subgraph < self.graph)
        self.assertTrue(self.graph > subgraph)
        self.assertTrue(subgraph <= self.graph)
        self.assertTrue(self.graph >= subgraph)

        # Graph equality comparison based on nodes and edges
        self.assertTrue(subgraph in self.graph)
        self.assertFalse(self.graph in subgraph)

        self.assertEqual(len(subgraph), 6)
        self.assertFalse(not subgraph)

        subgraph.clear()
        self.assertEqual(len(subgraph), 0)
        self.assertTrue(not subgraph)

    def test_graph_addsubtract(self):
        """
        Test addition and subtraction of one graph and another graph
        """

        # Addition
        graph1 = read_tgf(self._gpf_graph)
        graph2 = read_tgf(self._gpf_graph)

        graph1.remove_nodes([1, 2, 3])
        graph2.remove_nodes([9, 10, 11])
        graph_add = graph1 + graph2
        self.assertEqual(self.graph, graph_add)

        graph1 += graph2
        self.assertEqual(self.graph, graph1)

        # Subtraction
        graph3 = read_tgf(self._gpf_graph)
        graph3.remove_nodes([1, 2, 3, 4, 5, 6, 7, 8])
        self.assertEqual(graph1 - graph2, graph3)

    def test_graph_node_attribute_get(self):
        """
        Test node attribute 'getter' methods
        """

        # Access node attributes directly (unmodified) using the nodes GraphDict
        self.assertEqual(self.graph.nodes[1]['_id'], 1)
        self.assertEqual(self.graph.nodes[3], {'data': 3, 'nid': 3, '_id': 3, 'tgf': "'three'"})
        self.assertFalse(self.graph.nodes.get(22, False))  # Node does not exist
        self.assertFalse(self.graph.nodes[3].get('notthere', False))

        # Access node attributes by nid using the (sub)graph 'get' method
        sub = self.graph.getnodes([1, 2, 3])
        self.assertEqual(self.graph.get(3, key='data'), 3)
        self.assertEqual(self.graph.get(3), 3)        # uses default node data tag
        self.assertEqual(self.graph.get(3, key='no_key', defaultattr='tgf'), "'three'")
        self.assertEqual(sub.get(3, key='data'), 3)
        self.assertEqual(sub.get(3), 3)               # uses default node data tag
        self.assertEqual(sub.get(3, key='no_key', defaultattr='tgf'), "'three'")

        # Access node attributes using the 'attr' method
        self.assertEqual(self.graph.attr(1)['_id'], 1)

        # Access node attributes using single node graph 'get' method and magic methods
        sub = self.graph.getnodes(1)
        self.assertEqual(sub['data'], 1)
        self.assertEqual(sub.data, 1)
        self.assertEqual(sub.get(), 1)
        self.assertEqual(sub.get('tgf'), "'one'")

        # GraphException for KeyError and AttributeError
        self.assertRaises(GraphException, sub.__getitem__, 'no_key')
        self.assertRaises(GraphException, sub.__getattr__, 'no_key')
        self.assertIsNone(sub.get('no_key'))

        # Specific single node methods: get connected edges
        sub = self.graph.getnodes(3)
        self.assertItemsEqual(sub.connected_edges(), [(3, 2), (2, 3), (8, 3), (3, 4), (3, 8), (4, 3)])

    def test_graph_node_attribute_set(self):
        """
        Test node attribute 'setter' methods
        """

        # Set node attributes directly (unmodified) using the nodes GraphDict
        self.graph.nodes[3]['data'] = 4
        self.graph.nodes[4].update({'data': 'node_four'})
        self.assertEqual(self.graph.nodes[3].get('data'), 4)
        self.assertEqual(self.graph.nodes[4]['data'], 'node_four')

        # Set node attributes using the 'attr' method
        self.graph.attr(1)['tgf'] = 'changed'
        self.assertEqual(self.graph.nodes[1]['tgf'], 'changed')

        # Set node attributes using single graph 'set' method and magic methods
        sub = self.graph.getnodes(5)
        sub.set('tgf', 'five')
        sub.set('new', 23.88)
        self.assertEqual(sub.nodes[5]['tgf'], 'five')
        self.assertEqual(sub.nodes[5]['new'], 23.88)

        sub['data'] = 10
        sub.tgf = 'attr'
        self.assertEqual(sub.nodes[5]['data'], 10)
        self.assertEqual(sub.nodes[5]['tgf'], 'attr')

    def test_node_query(self):
        """
        Test node query methods
        """

        # Query for nodes
        self.assertEqual(len(self.graph.query_nodes({'tgf': "'six'"}).nodes()),
                         len([e for e in self.graph.nodes() if self.graph.nodes[e].get('tgf') == "'six'"]))

        from asq.initiators import query
        q = query(self.graph.nodes.values()).where(lambda n: n['tgf'].startswith("'s")).select(lambda s: s['nid'])
        print(q)

    def test_node_iteration(self):
        """
        Test node based traversal of the graph
        """

        # Graph node iterations
        self.assertTrue(isinstance(self.graph.iternodes(), types.GeneratorType))

        # Iterating a graph uses the iternodes function that returns nodes
        # in the order they where added to the graph
        for i, n in enumerate(self.graph, start=1):
            self.assertEqual(n.nid, i)

        # Selecting one node and iterating over it will return that node only
        sub = self.graph.getnodes(6)
        self.assertEqual(len(sub), 1)
        for n in sub:
            self.assertEqual(n.nid, 6)

        # Selecting multiple nodes will return a iterable subgraph
        sub = self.graph.getnodes([1, 3, 4])
        self.assertEqual(len(sub), 3)
        self.assertEqual([n.nid for n in sub], [1, 3, 4])

    def test_graph_edge_attribute_get(self):
        """
        Test node attribute 'getter' methods
        """

        # Access edge attributes directly (unmodified) using the edges GraphDict
        self.assertEqual(self.graph.edges[(1, 2)]['label'], 'mo')
        self.assertEqual(self.graph.edges[(2, 3)], {'label': 'bi'})
        self.assertFalse(self.graph.edges.get((7, 9), False))  # edge does not exist
        self.assertFalse(self.graph.edges[(1, 2)].get('notthere', False))

        # Access edge attributes by nid using the (sub)graph 'get' method
        sub = self.graph.getedges([(1, 2), (2, 3)])
        self.assertEqual(self.graph.get((1, 2), key='label'), 'mo')
        self.assertEqual(self.graph.get((1, 2)), 'mo')        # uses default node data tag
        self.assertEqual(self.graph.get((2, 3), key='no_key', defaultattr='label'), 'bi')
        self.assertEqual(sub.get((1, 2), key='label'), 'mo')
        self.assertEqual(sub.get((1, 2)), 'mo')               # uses default node data tag
        self.assertEqual(sub.get((2, 3), key='no_key', defaultattr='label'), 'bi')

        # Access edge attributes using the 'attr' method
        self.assertEqual(self.graph.attr((6, 7))['label'], 'bi')

        # Access edge attributes using single edge graph 'get' method and magic methods
        sub = self.graph.getedges((1, 2))
        self.assertEqual(sub['label'], 'mo')
        self.assertEqual(sub.label, 'mo')
        self.assertEqual(sub.get(), 'mo')
        self.assertEqual(sub.get('label'), 'mo')

        # GraphException for KeyError and AttributeError
        self.assertRaises(GraphException, sub.__getitem__, 'no_key')
        self.assertRaises(GraphException, sub.__getattr__, 'no_key')
        self.assertIsNone(sub.get('no_key'))

    def test_graph_edge_attribute_set(self):
        """
        Test edge attribute 'setter' methods
        """

        # Set edge attributes directly (unmodified) using the nodes GraphDict
        self.graph.edges[(1, 2)]['label'] = 4
        self.graph.edges[(2, 1)].update({'label': 'changed'})
        self.assertEqual(self.graph.edges[(1, 2)].get('label'), 4)
        self.assertEqual(self.graph.edges[(2, 1)]['label'], 'changed')

        # Set edge attributes using the 'attr' method
        self.graph.attr((1, 2))['tgf'] = 'changed'
        self.assertEqual(self.graph.edges[(1, 2)]['tgf'], 'changed')

        # Set edge attributes using single graph 'set' method and magic methods
        sub = self.graph.getnodes(5)
        sub.set('tgf', 'five')
        sub.set('new', 23.88)
        self.assertEqual(sub.nodes[5]['tgf'], 'five')
        self.assertEqual(sub.nodes[5]['new'], 23.88)

        sub['data'] = 10
        sub.tgf = 'attr'
        self.assertEqual(sub.nodes[5]['data'], 10)
        self.assertEqual(sub.nodes[5]['tgf'], 'attr')

    def test_edge_query(self):
        """
        Test edge query methods
        """

        # Query for edges
        self.assertEqual(len(self.graph.query_edges({'label': 'bi'}).edges()),
                         len([e for e in self.graph.edges() if self.graph.edges[e].get('label') == 'bi']))

    def test_edge_iteration(self):
        """
        Test edge based traversal of the graph
        """

        # Graph node iterations
        self.assertTrue(isinstance(self.graph.iteredges(), types.GeneratorType))
