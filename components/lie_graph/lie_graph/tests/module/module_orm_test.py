# -*- coding: utf-8 -*-

"""
file: module_graphorm_test.py

Unit tests for the Graph Object Relations Mapper (orm)
"""

import os
import unittest2

from lie_graph.graph_io.io_tgf_format import read_tgf
from lie_graph.graph_orm import GraphORM


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
    _gpf_graph = os.path.abspath(os.path.join(currpath, '../files/graph.tgf'))

    def setUp(self):
        """
        ConfigHandlerTests class setup

        Load graph from file and assign custom classes to labels and register
        with the ORM.
        """

        self.graph = read_tgf(self._gpf_graph)

        self.orm = GraphORM()
        self.orm.map_edge(ORMtestMo, {'label': 'mo'})
        self.orm.map_edge(ORMtestBi, {'label': 'bi'})
        self.orm.map_node(ORMtestTgf6, {'key': 'six'})
        self.orm.map_node(ORMtestTgf9, {'key': 'nine'})

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
        self.assertRaises(AssertionError, self.orm.map_node, 'not_a_class', {'key': 'two'})
        self.assertRaises(AssertionError, self.orm.map_edge, 'not_a_class', {'key': 'two'})

        # No query attributes, nothing to match
        self.assertRaises(AssertionError, self.orm.map_node, 'no_match_attr')
        self.assertRaises(AssertionError, self.orm.map_edge, 'no_match_attr')

    def test_graph_orm_mapped_nodes(self):
        """
        Test if all nodes are correctly mapped
        """

        self.assertItemsEqual(self.graph.orm.mapped_node_types.keys(), ['key'])
        self.assertItemsEqual(self.graph.orm.mapped_node_types.values()[0], ['nine', 'six'])

    def test_graph_orm_mapped_edges(self):
        """
        Test if all edges are correctly mapped
        """

        self.assertItemsEqual(self.graph.orm.mapped_edge_types.keys(), ['label'])
        self.assertItemsEqual(self.graph.orm.mapped_edge_types.values()[0], ['mo', 'bi'])

    def test_graph_orm_node(self):
        """
        Test ORM class mapping for nodes
        """

        self.assertEqual(self.graph.getnodes(6).add, 6)
        self.assertTrue(hasattr(self.graph.getnodes(6), 'get_label'))
        self.assertEqual(self.graph.getnodes(6).get_label(), "tgf6 class 6")

        # Node 9 has a custom class but misses the 'add' attribute
        self.assertFalse(hasattr(self.graph.getnodes(9), 'add'))
        self.assertTrue(hasattr(self.graph.getnodes(9), 'get_label'))
        self.assertRaises(AttributeError, self.graph.getnodes(9).get_label)

    def test_graph_orm_edge(self):
        """
        Test ORM class mapping for edges
        """

        for e, v in self.graph.edges.items():
            label = v.get('label')
            if label == 'bi':
                self.assertTrue(hasattr(self.graph.getedges(e), 'get_label'))
                self.assertEqual(self.graph.getedges(e).get_label(), "bi class")
            elif label == 'mo':
                self.assertTrue(hasattr(self.graph.getedges(e), 'get_label'))
                self.assertEqual(self.graph.getedges(e).get_label(), "mo class")

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

        # Changing the custom class 'add' attribute only affects the
        # particular node
        node6.add += 1
        self.assertEqual(children.add, 6)
        self.assertEqual(node6.add, 7)
        self.assertEqual(children.get_label(), 'tgf9 class 6')

    def test_graph_orm_inherit(self):
        """
        Test inheritence of non-package classes in ORM generated classes
        """

        # Turn inheritance of
        self.graph.orm._inherit = False

        # First call to ORM from base, node 6 should still have 'add' attribute
        node6 = self.graph.getnodes([6])
        self.assertTrue(hasattr(node6, 'add'))

        # Second call to ORM from node 6, node 9 should not have 'add'
        node9 = node6.getnodes(9)
        self.assertFalse(hasattr(node9, 'add'))