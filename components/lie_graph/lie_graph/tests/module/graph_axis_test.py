# -*- coding: utf-8 -*-

"""
file: module_graphaxis_test.py

Unit tests for the Graph axis methods
"""

import json
import os
import unittest2

from lie_graph import GraphAxis
from lie_graph.graph_helpers import GraphException
from lie_graph.graph_io.io_dict_parser import dict_to_graph
from lie_graph.graph_io.io_helpers import _nest_flattened_dict
from lie_graph.graph_axis_methods import *


class GraphAxisTests(unittest2.TestCase):
    currpath = os.path.dirname(__file__)
    _settings_json = os.path.join(currpath, '../', 'files', 'config_handler_test.json')

    def setUp(self):
        """
        ConfigHandlerTests class setup

        Load test settings file from config_handler_test.json
        """

        self.data = _nest_flattened_dict(json.load(open(self._settings_json)))
        self.graph = GraphAxis()
        dict_to_graph(self.data, self.graph)

    def test_graph_axis_children(self):
        """
        Test 'children' method
        """

        # Test axis methods directly
        self.assertEqual(node_children(self.graph, 5, self.graph.root), [])
        self.assertEqual(node_children(self.graph, 2, self.graph.root), [3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(node_children(self.graph, 29, self.graph.root), [30])

        # Using node nid's directly, returning graph objects
        self.assertEqual(sorted(self.graph.children(5).nodes.keys()), [])
        self.assertEqual(sorted(self.graph.children(2).nodes.keys()), [3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(sorted(self.graph.children(29).nodes.keys()), [30])

        # Using node nid's directly, returning nids
        self.assertEqual(self.graph.children(5, return_nids=True), [])
        self.assertEqual(self.graph.children(2, return_nids=True), [3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(self.graph.children(29, return_nids=True), [30])

        # Using sub graphs
        sub = self.graph.getnodes(18)
        self.assertEqual(sorted(sub.children().nodes.keys()), [19, 20, 21, 22])
        self.assertEqual(sub.children(return_nids=True), [19, 20, 21, 22])

        # with is_masked equals True
        self.graph.is_masked = True
        sub = self.graph.getnodes(18)
        self.assertEqual(sorted(sub.children().nodes.keys()), [])

    def test_graph_axis_neighbors(self):
        """
        Test graph node_neighbors method in a masked and unmasked graph
        """

        # Test axis methods directly
        self.assertEqual(node_neighbors(self.graph, 3), [2])
        self.assertEqual(node_neighbors(self.graph, 10), [1, 11, 18])
        self.assertEqual(node_neighbors(self.graph, 29), [1, 30])

        # Node neighbor query in a non-isolated graph (is_masked = False), returning graph objects
        self.assertEqual(sorted(self.graph.neighbors(3).nodes.keys()), [2])
        self.assertEqual(sorted(self.graph.neighbors(10).nodes.keys()), [1, 11, 18])
        self.assertEqual(sorted(self.graph.neighbors(29).nodes.keys()), [1, 30])

        # Node neighbor query in a non-isolated graph (is_masked = False), returning nids
        self.assertEqual(self.graph.neighbors(3, return_nids=True), [2])
        self.assertEqual(self.graph.neighbors(10, return_nids=True), [1, 11, 18])
        self.assertEqual(self.graph.neighbors(29, return_nids=True), [1, 30])

        # Node neighbor query in isolated graph (is_masked = True)
        self.graph.is_masked = True
        sub = self.graph.getnodes(3)
        self.assertEqual(sorted(sub.neighbors().nodes.keys()), [])
        self.assertEqual(sub.neighbors(return_nids=True), [])
        sub = self.graph.getnodes([10, 11, 18])
        self.assertEqual(sorted(sub.neighbors(10).nodes.keys()), [11, 18])
        self.assertEqual(sub.neighbors(10, return_nids=True), [11, 18])
        sub = self.graph.getnodes([1, 29])
        self.assertEqual(sorted(sub.neighbors().nodes.keys()), [29])
        self.assertEqual(sub.neighbors(return_nids=True), [29])

    def test_graph_axis_parent(self):
        """
        Test 'parent' method
        """

        # Test axis methods directly
        self.assertEqual(node_parent(self.graph, 1, self.graph.root), None)
        self.assertEqual(node_parent(self.graph, 15, self.graph.root), 11)
        self.assertEqual(node_parent(self.graph, 23, self.graph.root), 22)

        # Using node nid's directly, returning graph objects
        self.assertEqual(sorted(self.graph.parent(1).nodes.keys()), [])
        self.assertEqual(sorted(self.graph.parent(15).nodes.keys()), [11])
        self.assertEqual(sorted(self.graph.parent(23).nodes.keys()), [22])

        # Using node nid's directly, returning nids
        self.assertEqual(self.graph.parent(1, return_nids=True), None)
        self.assertEqual(self.graph.parent(15, return_nids=True), 11)
        self.assertEqual(self.graph.parent(23, return_nids=True), 22)

        # Using sub graphs
        sub = self.graph.getnodes(23)
        self.assertEqual(sorted(sub.parent().nodes.keys()), [22])
        self.assertEqual(sub.parent(return_nids=True), 22)
        sub = self.graph.getnodes(1)
        self.assertEqual(sorted(sub.parent().nodes.keys()), [])
        self.assertEqual(sub.parent(return_nids=True), None)

    def test_graph_axis_ancestors(self):
        """
        Test 'ancestors' method
        """

        # Test axis methods directly
        self.assertEqual(node_ancestors(self.graph, 24, self.graph.root), [1, 10, 18, 22])
        self.assertEqual(node_ancestors(self.graph, 24, self.graph.root, include_self=True), [1, 10, 18, 22, 24])
        self.assertEqual(node_ancestors(self.graph, 1, self.graph.root), [])

        # Using node nid's directly, returning graph objects
        self.assertEqual(sorted(self.graph.ancestors(24).nodes.keys()), [1, 10, 18, 22])
        self.assertEqual(sorted(self.graph.ancestors(24, include_self=True).nodes.keys()), [1, 10, 18, 22, 24])
        self.assertEqual(sorted(self.graph.ancestors(1).nodes.keys()), [])

        # Using node nid's directly, returning nids
        self.assertEqual(self.graph.ancestors(24, return_nids=True), [1, 10, 18, 22])
        self.assertEqual(self.graph.ancestors(24, include_self=True, return_nids=True), [1, 10, 18, 22, 24])
        self.assertEqual(self.graph.ancestors(1, return_nids=True), [])

        # Using sub graphs
        sub = self.graph.getnodes(24)
        self.assertEqual(sorted(sub.ancestors().nodes.keys()), [1, 10, 18, 22])
        self.assertEqual(sorted(sub.ancestors(include_self=True).nodes.keys()), [1, 10, 18, 22, 24])
        self.assertEqual(sub.ancestors(return_nids=True), [1, 10, 18, 22])
        self.assertEqual(sub.ancestors(include_self=True, return_nids=True), [1, 10, 18, 22, 24])
        sub = self.graph.getnodes(1)
        self.assertEqual(sorted(sub.ancestors().nodes.keys()), [])
        self.assertEqual(sub.ancestors(return_nids=True), [])

    def test_graph_axis_descendants(self):
        """
        Test 'descendants' method
        """

        # Test axis methods directly
        self.assertEqual(node_descendants(self.graph, 10, self.graph.root), [11, 18, 12, 13, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24])
        self.assertEqual(node_descendants(self.graph, 24, self.graph.root), [])
        self.assertEqual(node_descendants(self.graph, 2, self.graph.root), [3, 4, 5, 6, 7, 8, 9])

        # Using node nid's directly, returning graph objects
        self.assertEqual(sorted(self.graph.descendants(10).nodes.keys()), [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24])
        self.assertEqual(sorted(self.graph.descendants(24).nodes.keys()), [])
        self.assertEqual(sorted(self.graph.descendants(2).nodes.keys()), [3, 4, 5, 6, 7, 8, 9])

        # Using node nid's directly, returning nids
        self.assertEqual(self.graph.descendants(10, return_nids=True), [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24])
        self.assertEqual(self.graph.descendants(24, return_nids=True), [])
        self.assertEqual(self.graph.descendants(2, return_nids=True), [3, 4, 5, 6, 7, 8, 9])

        # Using sub graphs
        sub = self.graph.getnodes(10)
        self.assertEqual(sorted(sub.descendants().nodes.keys()), [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24])
        self.assertEqual(sub.descendants(return_nids=True), [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24])
        sub = self.graph.getnodes(24)
        self.assertEqual(sorted(sub.descendants().nodes.keys()), [])
        self.assertEqual(sub.descendants(return_nids=True), [])
        sub = self.graph.getnodes(2)
        self.assertEqual(sorted(sub.descendants(include_self=True).nodes.keys()), [2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(sub.descendants(include_self=True, return_nids=True), [2, 3, 4, 5, 6, 7, 8, 9])

    def test_graph_axis_leaves(self):
        """
        Test 'leaves' method
        """

        # Using node nid's directly, returning graph objects
        self.assertEqual(sorted(self.graph.leaves().nodes.keys()), [3, 4, 5, 6, 7, 8, 9, 12, 13, 14, 16, 17, 19, 20, 21, 23, 24, 26, 27, 28, 30])

        # Using node nid's directly, returning nids
        self.assertEqual(self.graph.leaves(return_nids=True), [3, 4, 5, 6, 7, 8, 9, 12, 13, 14, 16, 17, 19, 20, 21, 23, 24, 26, 27, 28, 30])

        # Using sub graphs
        sub = self.graph.descendants(2)
        self.assertEqual(sorted(sub.leaves().nodes.keys()), [3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(sub.leaves(return_nids=True), [3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(sorted(self.graph.getnodes(16).leaves().nodes.keys()), [16])
        self.assertEqual(self.graph.getnodes(16).leaves(return_nids=True), [16])

    def test_graph_axis_siblings(self):
        """
        Test 'siblings' method
        """

        # Test axis methods directly
        self.assertEqual(node_siblings(self.graph, 1, self.graph.root), [])
        self.assertEqual(node_siblings(self.graph, 2, self.graph.root), [10, 25, 29])
        self.assertEqual(node_siblings(self.graph, 3, self.graph.root), [4, 5, 6, 7, 8, 9])

        # Using node nid's directly, returning graph objects
        self.assertEqual(sorted(self.graph.siblings(1).nodes.keys()), [])
        self.assertEqual(sorted(self.graph.siblings(2).nodes.keys()), [10, 25, 29])
        self.assertEqual(sorted(self.graph.siblings(3).nodes.keys()), [4, 5, 6, 7, 8, 9])

        # Using node nid's directly, returning nids
        self.assertEqual(self.graph.siblings(1, return_nids=True), [])
        self.assertEqual(self.graph.siblings(2, return_nids=True), [10, 25, 29])
        self.assertEqual(self.graph.siblings(3, return_nids=True), [4, 5, 6, 7, 8, 9])

        # Using sub graphs, they don't have siblings if is_masked
        sub = self.graph.getnodes(1)
        self.assertEqual(sorted(sub.siblings().nodes.keys()), [])
        self.assertEqual(sub.siblings(return_nids=True), [])
        sub = self.graph.getnodes(2)
        self.assertEqual(sorted(sub.siblings().nodes.keys()), [10, 25, 29])
        self.assertEqual(sub.siblings(return_nids=True), [10, 25, 29])
        sub.is_masked = True
        self.assertEqual(sorted(sub.siblings().nodes.keys()), [])
        self.assertEqual(sub.siblings(return_nids=True), [])

    def test_graph_axis_root_definition(self):
        """
        Axis based methods require a root node to be defined.
        """

        # Root automatically define at data import stage
        self.assertEqual(self.graph.root, 1)

        # Root node inherited in sub graph if not is_masked
        sub = self.graph.getnodes(5)
        self.assertEqual(sub.root, 1)

        # Root node reset in sub graph if is_masked
        self.graph.is_masked = True
        sub = self.graph.getnodes(5)
        self.assertEqual(sub.root, 5)

        # If root not defined, raise exception
        self.graph.root = None
        self.assertRaises(GraphException, self.graph.children)

    def test_graph_axis_iteration(self):
        """
        Traversing a hierarchical graph using axis methods
        """

        # Getting descendants of node 1 children
        desc = {25: [26, 27, 28],
                2: [3, 4, 5, 6, 7, 8, 9],
                10: [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24],
                29: [30]}
        for n in self.graph.children():
            self.assertEqual(n.descendants(return_nids=True), desc[n.nid])

        # Getting descendants of node 10 with 11 as root
        desc = {1: [2, 3, 4, 5, 6, 7, 8, 9, 25, 26, 27, 28, 29, 30],
                18: [19, 20, 21, 22, 23, 24]}
        self.graph.root = 11
        for n in self.graph.children(10):
            self.assertEqual(n.descendants(return_nids=True), desc[n.nid])

        # Iterating over leaves gives single node graph objects giving direct
        # access to attributes
        self.graph.root = 1
        keys = {12: 'param1', 13: 'param2', 14: 'param3', 16: 'app_namespace', 17: 'log_level'}
        for n in self.graph.descendants(11).leaves():
            self.assertEqual(n.get(), keys[n.nid])
