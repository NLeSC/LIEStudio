# -*- coding: utf-8 -*-

"""
file: config_test.py

Unit tests for the lie_graph component
"""

import unittest2

from lie_graph import Graph
from lie_graph.graph_algorithms import *


class TestGraphAlgorithms(unittest2.TestCase):

    def setUp(self):

        self.graph = Graph(
            nodes={1: {'weight': 2.5, 'data': 10}, 2: {'data': 'one'},
                   3: {'data': [1.22, 4.5, 6], 'pv': 1.44, 'test': True}, 4: {'data': len},
                   5: {'data': 2, 'time': '2pm'}, 6: {'data': 3, 'time': '2pm'}, 7: {'data': 4, 'time': '2pm'},
                   8: {'data': 'n'}, 9: {'data': 'o'}, 10: {'data': 'd'}, 11: {'data': 'e'}, 12: {'data': 's'},
                   13: {'data': 13}, 'object': {'data': 'object'}},
            edges={(5, 4): {'type': 'universal'}, (5, 6): {'type': 'universal'}, (11, 9): {'type': 'universal'},
                   (3, 2): {'type': 'universal'}, (2, 1): {'type': 'monotone'}, (9, 10): {'type': 'universal'},
                   (2, 3): {'type': 'universal'}, (9, 6): {'type': 'universal'}, (6, 5): {'type': 'universal'},
                   (1, 2): {'type': 'monotone'}, ('object', 12): {'type': 'universal'},
                   (6, 9): {'type': 'universal'}, (6, 7): {'type': 'universal'}, (12, 13): {'type': 'monotone'},
                   (7, 8): {}, (7, 6): {'type': 'universal'}, (13, 12): {'type': 'monotone'},
                   (3, 8): {'type': 'universal'}, (4, 5): {'type': 'universal'}, (12, 'object'): {'type': 'universal'},
                   (9, 11): {'type': 'universal'}, (4, 3): {'type': 'universal'}, (8, 3): {'type': 'universal'},
                   (3, 4): {'type': 'universal'}, (10, 9): {'type': 'universal'}},
            adjacency={1: [2], 2: [1, 3], 3: [2, 8, 4], 4: [5, 3], 5: [4, 6], 6: [5, 9, 7], 7: [8, 6], 8: [3],
                       9: [10, 6, 11], 10: [9], 11: [9], 12: [13, 'object'], 13: [12], 'object': [12]}
        )

    def test_graph_shortest_path_method(self):
        """
        Test Dijkstra shortest path method
        """

        # In a mixed directed graph where 7 connects to 8 but not 8 to 7
        self.assertEqual(dijkstra_shortest_path(self.graph, 8, 10), [8, 3, 4, 5, 6, 9, 10])
        self.assertEqual(list(dfs_paths(self.graph, 8, 10)), [[8, 3, 4, 5, 6, 9, 10]])
        self.assertEqual(list(dfs_paths(self.graph, 8, 10, method='bfs')), [[8, 3, 4, 5, 6, 9, 10]])

        # Fully connect 7 and 8
        self.graph.add_edge((8, 7), directed=True)
        self.assertEqual(dijkstra_shortest_path(self.graph, 8, 10), [8, 7, 6, 9, 10])
        self.assertEqual(list(dfs_paths(self.graph, 8, 10)), [[8, 7, 6, 9, 10], [8, 3, 4, 5, 6, 9, 10]])
        self.assertEqual(list(dfs_paths(self.graph, 8, 10, method='bfs')), [[8, 7, 6, 9, 10], [8, 3, 4, 5, 6, 9, 10]])

    def test_graph_dfs_method(self):
        """
        Test graph depth-first-search and breath-first-search
        """

        # Connectivity information using Depth First Search / Breath first search
        self.assertItemsEqual(dfs(self.graph, 8), [8, 3, 4, 5, 6, 7, 9, 11, 10, 2, 1])
        self.assertItemsEqual(dfs(self.graph, 8, method='bfs'), [8, 3, 2, 4, 1, 5, 6, 9, 7, 10, 11])

    def test_graph_node_reachability_methods(self):
        """
        Test graph algorithms
        """

        # Test if node is reachable from other node (uses dfs internally)
        self.assertTrue(is_reachable(self.graph, 8, 10))
        self.assertFalse(is_reachable(self.graph, 8, 12))

    def test_graph_topology_methods(self):
        """
        Test graph topology algorithms
        TODO: These do not all work yet
        """

        # Return the degree of nodes in a graph
        self.assertEqual(list(degree(self.graph, nodes=(1, 4, 6))), [(1, 1), (4, 2), (6, 3)])

        # Are nodes all connected to one another
        self.assertFalse(nodes_are_interconnected(self.graph, [1, 2, 3]))
        self.assertTrue(nodes_are_interconnected(self.graph, [1, 2]))

        # Return Brandes betweenness centrality
        # print(brandes_betweenness_centrality(self.graph))

        # Return eigenvector centrality
        # print(eigenvector_centrality(self.graph))

        # Return weighted adjacency map
        # print(adjacency(self.graph))
