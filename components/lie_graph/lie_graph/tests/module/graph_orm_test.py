# -*- coding: utf-8 -*-

"""
file: module_graphorm_test.py

Unit tests for the Graph Object Relations Mapper (orm)
"""

import os
import unittest2

from lie_graph.graph_io.io_tgf_format import read_tgf
from lie_graph.graph_orm import GraphORM
from lie_graph.graph_mixin import FileHandler


class ORMtestMo(object):

    @staticmethod
    def get_label():

        return "mo class"


class ORMtestBi(object):

    @staticmethod
    def get_label():

        return "bi class"


class ORMtestTgf6(object):

    add = 6

    def get_label(self):

        return "tgf6 class {0}".format(self.add)


class ORMtestTgf9(object):

    def get_label(self):

        return "tgf9 class {0}".format(self.add)


class TestGraphORM(unittest2.TestCase):
    currpath = os.path.dirname(__file__)
    _gpf_graph = os.path.join(currpath, '../', 'files', 'graph.tgf')

    def setUp(self):

        self.graph = read_tgf(self._gpf_graph)

        self.orm = GraphORM()
        self.orm.map_edge(ORMtestMo, {'label': 'mo'})
        self.orm.map_edge(ORMtestBi, {'label': 'bi'})
        self.orm.map_node(ORMtestTgf6, {'tgf': "'six'"})
        self.orm.map_node(ORMtestTgf9, {'tgf': "'nine'"})
        self.orm.map_node(FileHandler, {'tgf': "'four'"})

        self.graph.orm = self.orm

    def test_graph_orm_exceptions(self):
        """
        Test ORM exception handling
        """

        base_cls = self.graph._get_class_object()

        # Only perform orm lookup for a list with only nodes or edges, not mixed.
        self.assertRaises(AssertionError, self.orm.get, self.graph, (3.4, 5), base_cls)
        self.assertRaises(AssertionError, self.orm.get, self.graph, ((1, 2), 'node'), base_cls)

        # Mapper only accepts classes
        self.assertRaises(AssertionError, self.orm.map_node, 'not_a_class', {'tgf': "'two'"})
        self.assertRaises(AssertionError, self.orm.map_edge, 'not_a_class', {'tgf': "'two'"})

        # No query attributes, nothing to match
        self.assertRaises(AssertionError, self.orm.map_node, 'no_match_attr')
        self.assertRaises(AssertionError, self.orm.map_edge, 'no_match_attr')

    def test_graph_orm(self):
        """
        Test dynamic inheritance
        """

        # Get node 6 from the full graph and then children of 6 from node 6 object
        self.graph.root = 1
        node6 = self.graph.getnodes([6])
        children = node6.getnodes(9)

        # Node 6 should have node6 specific get_label method
        self.assertEqual(node6.get_label(), 'tgf6 class 6')

        # Children should get node9 specific get_label method but with node6
        # attribute
        self.assertEqual(children.get_label(), 'tgf9 class 6')
