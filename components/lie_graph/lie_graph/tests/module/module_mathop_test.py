# -*- coding: utf-8 -*-

"""
file: module_mathop_test.py

Unit tests for graph 'set' like math operations functions
"""

import os
import string
import unittest2
import random

from lie_graph.graph_io.io_tgf_format import read_tgf
from lie_graph.graph_math_operations import *


class TestGraphMathOperations(unittest2.TestCase):

    currpath = os.path.dirname(__file__)
    _gpf_graph = os.path.join(currpath, '../', 'files', 'graph.tgf')

    def setUp(self):
        """
        ConfigHandlerTests class setup

        Load graph from graph.tgf file
        """

        self.graph1 = read_tgf(self._gpf_graph)

        self.graph2 = read_tgf(self._gpf_graph)
        self.graph2.is_directed = True
        self.graph2.remove_nodes([1, 2, 3, 4, 5])

        self.graph3 = read_tgf(self._gpf_graph)
        self.graph3.is_directed = True
        self.graph3.remove_nodes([6, 7, 8, 9, 10, 11])

    def test_math_operations_update(self):
        """
        Test updating nodes and/or edges attribute update for nodes and edges in
        self from other
        """

        newattribs = []
        for edge in self.graph2.edges():
            randstring = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            newattribs.append(randstring)
            self.graph2.edges[edge].update({'rand': randstring})

        graph_update(self.graph1, self.graph2)
        self.assertEqual([e['rand'] for e in self.graph1.iteredges() if 'rand' in e], newattribs)

    def test_math_operations_add(self):
        """
        Test graph addition (add nodes and edges from other to self) followed
        by graph update to update node and edge attributes form other to self.
        """

        added = graph_add(self.graph2, self.graph3)
        self.assertTrue(self.graph2 in added)
        self.assertTrue(self.graph3 in added)

        added = graph_update(added, self.graph3)
        for node in added.nodes.keys():
            self.assertDictEqual(added.nodes[node], self.graph1.nodes[node])
        for edge in added.edges.keys():
            self.assertDictEqual(added.edges[edge], self.graph1.edges[edge])
