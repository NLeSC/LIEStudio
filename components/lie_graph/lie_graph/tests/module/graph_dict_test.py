# -*- coding: utf-8 -*-

"""
file: module_graphdict_test.py

Unit tests for the GraphDict class
"""

import unittest2

from lie_graph.graph_dict import GraphDict


class TestGraphDict(unittest2.TestCase):

    def setUp(self):

        mapping = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5}
        self.graph = GraphDict(mapping)

    def test_get_keysview(self):
        """
        Test the GraphDict view based keys handling
        """

        keyview = self.graph.keys()
        self.assertItemsEqual(list(keyview), ['one', 'two', 'three', 'four', 'five'])

        self.graph['six'] = 6
        self.assertItemsEqual(list(keyview), ['one', 'two', 'three', 'four', 'five', 'six'])
        self.assertEqual(len(keyview), 6)

        other = GraphDict({'two': 2, 'three': 3, 'four': 4, 'six': 6})
        self.assertEqual(keyview & other.keys(), {'four', 'six', 'two', 'three'})
        self.assertEqual(keyview | other.keys(), {'six', 'three', 'two', 'four', 'five', 'one'})
        self.assertEqual(keyview - other.keys(), {'five', 'one'})
        self.assertEqual(keyview ^ other.keys(), {'five', 'one'})

    def test_get_valuesview(self):
        """
        Test the GraphDict view based values handling
        """

        valueview = self.graph.values()
        self.assertItemsEqual(list(valueview), [1, 2, 3, 4, 5])

        self.graph['six'] = 6
        self.assertItemsEqual(list(valueview), [1, 2, 3, 4, 5, 6])
        self.assertEqual(len(valueview), 6)

        other = GraphDict({'two': 2, 'three': 3, 'four': 4, 'six': 6})
        self.assertEqual(valueview & other.values(), {4, 6, 2, 3})
        self.assertEqual(valueview | other.values(), {1, 2, 3, 4, 5, 6})
        self.assertEqual(valueview - other.values(), {1, 5})
        self.assertEqual(valueview ^ other.values(), {1, 5})

    def test_get_itemsview(self):
        """
        Test the GraphDict view based items handling
        """

        itemview = self.graph.items()
        self.assertItemsEqual(list(itemview), [('one', 1), ('two', 2), ('three', 3), ('four', 4), ('five', 5)])

        self.graph['six'] = 6
        self.assertItemsEqual(list(itemview), [('one', 1), ('two', 2), ('three', 3),
                                               ('four', 4), ('five', 5), ('six', 6)])
        self.assertEqual(len(itemview), 6)

    def test_set_keysview(self):
        """
        Test working with selective key views
        """

        self.assertFalse(self.graph.is_view)
        self.graph.set_view(['one', 'three'])
        self.assertTrue(self.graph.is_view)
        self.assertDictEqual(self.graph.dict(), {'three': 3, 'one': 1})

    def test_dict_set(self):
        """
        Test dictionary item setter
        """

        self.graph.set('six', 6)
        self.assertTrue('six' in self.graph)

        self.graph['seven'] = 7
        self.assertTrue('seven' in self.graph)

        self.graph.update({'eight': 8, 'nine': 9})
        self.assertTrue('eight' in self.graph)

        self.graph.setdefault('ten', 10)
        self.assertTrue('ten' in self.graph)

    def test_dict_get(self):
        """
        Test dictionary item getter for a default dictionary
        and for on with a selective view on the main dict.
        """

        # Default getter
        self.assertTrue(self.graph.get('one'), 1)
        self.assertTrue(self.graph.get('ten', 10), 10)
        self.assertTrue(self.graph['three'], 3)
        self.assertRaises(KeyError, self.graph.__getitem__, 'ten')

        # Selective view getter
        self.graph.set_view(['one', 'three'])
        self.assertTrue(self.graph.get('two', 2), 2)
        self.assertRaises(KeyError, self.graph.__getitem__, 'four')

    def test_dict_default_del(self):
        """
        Test dictionary key deletion methods for a default dictionary.
        """

        del self.graph['three']
        self.assertFalse('three' in self.graph)

        pop = self.graph.pop('five')
        self.assertTrue(pop == 5)
        self.assertTrue('five' not in self.graph)

        popitem = self.graph.popitem()
        self.assertTrue(popitem not in self.graph.items())

        self.graph.clear()
        self.assertTrue(len(self.graph) == 0)

    def test_dict_view_del(self):
        """
        Test dictionary key deletion methods for a selective view on
        the dictionary
        """

        self.graph.set_view(['one', 'three', 'five'])
        self.assertRaises(KeyError, self.graph.__delitem__, 'two')

        del self.graph['one']
        self.assertFalse('one' in self.graph)

        pop = self.graph.pop('three')
        self.assertTrue(pop == 3)
        self.assertTrue('three' not in self.graph)

        popitem = self.graph.popitem()
        self.assertTrue(popitem not in self.graph.items())

        # Graph clear only operates on selection if is_view
        self.graph.clear()
        self.assertTrue(len(self.graph) == 0)

        self.graph.reset_view()
        self.assertItemsEqual(list(self.graph.keys()), ['four', 'two'])
        self.graph.clear()
        self.assertTrue(len(self.graph) == 0)

    def test_dict_creation(self):
        """
        Test methods for dictionary creation
        """

        mapping = {'one': 1, 'two': 2, 'three': 3}

        # GraphDict from a native dict
        fromdict = GraphDict(mapping)
        self.assertDictEqual(fromdict, mapping)

        # GraphDict from keyword arguments
        frommap = GraphDict(**mapping)
        self.assertDictEqual(frommap, mapping)

        # GraphDict from list of tuples
        frommap = GraphDict([('one', 1), ('two', 2), ('three', 3)])
        self.assertDictEqual(frommap, mapping)

        # GraphDict from a list of keys
        new_d = fromdict.fromkeys(['one', 'two'])
        self.assertDictEqual(new_d, {'one': 1, 'two': 2})

    def test_dict_magic(self):
        """
        Test dictionary magic methods for a default dictionary
        and for on with a selective view on the main dict.
        """

        # Default
        self.assertEqual(len(self.graph), 5)
        self.assertTrue('five' in self.graph)
        self.assertFalse('six' in self.graph)

        # Selective view
        self.graph.set_view(['one', 'three'])
        self.assertEqual(len(self.graph), 2)
        self.assertTrue('one' in self.graph)
        self.assertFalse('five' in self.graph)

        self.assertIn(str(self.graph), ["{'one': 1, 'three': 3}", "{'three': 3, 'one': 1}"])
        self.assertEqual(repr(self.graph), '<GraphDict object {0}: 2 items, is_view: True>'.format(id(self.graph)))

    def test_dict_truethtest(self):
        """
        Test methods for 'existance' trueth test
        """

        # An empty graph
        empty = GraphDict()
        e = False
        if empty:
            e = True
        self.assertFalse(e)
        self.assertIsNotNone(empty is None)
        self.assertEqual(len(empty), 0)

        # A graph with content
        e = False
        if self.graph:
            e = True
        self.assertTrue(e)
        self.assertIsNotNone(self.graph is None)
        self.assertNotEqual(len(self.graph), 0)

    def test_dict_comparison(self):
        """
        Test rich key based comparison operators between two GraphDicts
        """

        graph1 = GraphDict({'three': 3, 'four': 4, 'six': 6})
        graph2 = GraphDict({'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6})

        self.assertEqual(self.graph.intersection(graph1), {'four', 'three'})
        self.assertEqual(self.graph.difference(graph1), {'five', 'two', 'one'})
        self.assertEqual(self.graph.symmetric_difference(graph1), {'six', 'five', 'two', 'one'})
        self.assertEqual(self.graph.union(graph1), {'six', 'three', 'one', 'four', 'five', 'two'})
        self.assertFalse(self.graph.isdisjoint(graph1))
        self.assertFalse(self.graph.issubset(self.graph, propper=True))
        self.assertTrue(self.graph.issubset(self.graph, propper=False))
        self.assertTrue(graph2.issuperset(self.graph, propper=True))
        self.assertTrue(self.graph.issuperset(self.graph, propper=False))

        self.assertEqual(self.graph & graph1, {'four', 'three'})
        self.assertEqual(self.graph ^ graph1, {'six', 'five', 'two', 'one'})
        self.assertEqual(self.graph | graph1, {'six', 'three', 'one', 'four', 'five', 'two'})
        self.assertFalse(self.graph == graph1)
        self.assertTrue(self.graph != graph1)
        self.assertFalse(self.graph < self.graph)
        self.assertTrue(self.graph <= self.graph)
        self.assertTrue(graph2 > self.graph)
        self.assertTrue(self.graph >= self.graph)
