# -*- coding: utf-8 -*-

"""
file: module_storage_driver_test.py

Unit tests graph nodes and edges storage drivers
"""

import unittest2

from lie_graph.graph_storage_drivers.graph_dict import DictStorage


class _PropertyTests(object):
    """
    Mixin class to test class property getter and setter methods
    """

    _propvalue = 3

    @property
    def aproperty(self):

        return self._propvalue

    @aproperty.setter
    def aproperty(self, value):

        self._propvalue = value


class _BaseStorageDriverTests(object):

    def test_dict_creation(self):
        """
        Test default Python dict-like creation from iterable and/or mappings
        """
        mapping = {'one': 1, 'two': 2, 'three': 3}

        # Storage from a native dict
        fromdict = self.storage_instance(mapping)
        self.assertDictEqual(fromdict, mapping)

        # Storage from keyword arguments
        frommap = self.storage_instance(**mapping)
        self.assertDictEqual(frommap, mapping)

        # Storage from list of tuples
        frommap = self.storage_instance([('one', 1), ('two', 2), ('three', 3)])
        self.assertDictEqual(frommap, mapping)

        # Storage from a list of keys
        new_d = fromdict.fromkeys(['one', 'two'])
        self.assertDictEqual(new_d, {'one': 1, 'two': 2})

    def test_dict_length(self):
        """
        Test size of storage which equals number of keys in default Python dict
        """

        self.assertEqual(len(self.storage), 5)
        self.assertEqual(len(self.storage), len(self.storage.keys()))

    def test_dict_getitem(self):
        """
        Test Python dict-like __getitem__ behaviour
        """

        self.assertEqual(self.storage['one'], 1)
        self.assertRaises(KeyError, self.storage.__getitem__, 'nokey')

    def test_dict_getattr(self):
        """
        Test Python dict-like __getattr__ behaviour
        """

        self.assertEqual(self.storage.one, 1)
        self.assertRaises(AttributeError, self.storage.__getattr__, 'nokey')

    def test_dict_setitem(self):
        """
        Test Python dict-like __setitem__ behaviour
        """

        # Change value for existing key
        self.storage['two'] = 3
        self.assertEqual(self.storage.get('two'), 3)

        # Add newkey, value pair
        self.storage['six'] = 6
        self.assertEqual(self.storage.get('six'), 6)

    def test_dict_delitem(self):
        """
        Test Python dict-like __delitem__ behaviour
        """

        # Remove key
        del self.storage['one']
        self.assertTrue('one' not in self.storage)

        # Remove key that does not exist
        self.assertRaises(KeyError, self.storage.__delitem__, 'nokey')

    def test_dict_property(self):
        """
        Test ability of the class to deal with get/set of class property values
        """

        propclass = type('PropertyClass', (self.storage_instance, _PropertyTests), {})
        storage = propclass({'one': 1, 'two': 2, 'three': 3})

        # Default getter property and regular data
        self.assertEquals(storage['one'], 1)
        self.assertEquals(storage.aproperty, 3)
        self.assertEquals(storage.two, 2)

        # 'get' method should not return property
        self.assertIsNone(storage.get('aproperty'))
        self.assertIsNone(storage.get('_propvalue'))

        # Default setter
        storage.aproperty = 4
        self.assertEquals(storage.aproperty, 4)
        self.assertTrue('aproperty' not in storage)

        # Properties have precedence over data store
        storage['aproperty'] = 10
        self.assertTrue('aproperty' in storage)
        self.assertEquals(storage.aproperty, 4)
        self.assertEquals(storage['aproperty'], 10)

    def test_dict_contain(self):
        """
        Test Python dict-like contain magic methods
        """

        self.assertTrue('five' in self.storage)
        self.assertFalse('six' in self.storage)

    def test_dict_iter(self):
        """
        Test Python dict-like __iter__ behaviour
        """

        keys = self.storage.keys()
        for k in self.storage:
            self.assertTrue(k in keys)

    def test_dict_str(self):
        """
        Test Python dict-like __str__ behaviour
        """

        self.assertEqual(str(self.storage), "{'four': 4, 'one': 1, 'five': 5, 'three': 3, 'two': 2}")

    def test_dict_clear(self):
        """
        Test Python dict clear method
        """

        self.storage.clear()
        self.assertEqual(len(self.storage), 0)

    def test_dict_copy(self):

        return

    def test_dict_get(self):

        # Default getter
        self.assertTrue(self.storage.get('one'), 1)
        self.assertTrue(self.storage.get('ten', 10), 10)
        self.assertEqual(self.storage.get('ten'), None)

    def test_dict_items(self):
        """
        Test Python dict items method. This should be the python 3.x compatible
        items view object.
        """

        items = self.storage.items()
        self.assertFalse(isinstance(items, list))
        self.assertItemsEqual(list(items), [('one', 1), ('two', 2), ('three', 3), ('four', 4), ('five', 5)])

        # Adding a new item should be reflected in the Keys View
        self.storage['six'] = 6
        self.assertItemsEqual(list(items), [('one', 1), ('two', 2), ('three', 3), ('four', 4), ('five', 5), ('six', 6)])
        self.assertEqual(len(items), 6)

    def test_dict_iteritems(self):

        items = self.storage.iteritems()

        self.assertFalse(isinstance(items, list))
        self.assertItemsEqual(list(items), [('one', 1), ('two', 2), ('three', 3), ('four', 4), ('five', 5)])

    def test_dict_iterkeys(self):

        keys = self.storage.iterkeys()

        self.assertFalse(isinstance(keys, list))
        self.assertItemsEqual(list(keys), ['five', 'four', 'one', 'three', 'two'])

    def test_dict_itervalues(self):

        values = self.storage.itervalues()

        self.assertFalse(isinstance(values, list))
        self.assertItemsEqual(list(values), [1, 2, 3, 4, 5])

    def test_dict_keys(self):
        """
        Test Python dict keys method. This should be the python 3.x compatible
        keys view object.
        """

        keys = self.storage.keys()
        self.assertFalse(isinstance(keys, list))
        self.assertItemsEqual(list(keys), ['five', 'four', 'one', 'three', 'two'])

        # Adding a new key should be reflected in the Keys View
        self.storage['six'] = 6
        self.assertItemsEqual(list(keys), ['one', 'two', 'three', 'four', 'five', 'six'])
        self.assertEqual(len(keys), 6)

    def test_dict_pop(self):

        pop = self.storage.pop('five')
        self.assertTrue(pop == 5)
        self.assertTrue('five' not in self.storage)

    def test_dict_popitem(self):

        popitem = self.storage.popitem()
        self.assertTrue(popitem not in self.storage.items())

    def test_dict_set(self):
        """
        Test dictionary set method. Not a default Python dict method
        """

        self.storage.set('six', 6)
        self.assertTrue('six' in self.storage)

    def test_dict_setdefault(self):

        self.storage.setdefault('ten', 10)
        self.assertTrue('ten' in self.storage)

    def test_dict_update(self):

        self.storage.update({'eight': 8, 'nine': 9})
        self.assertTrue('eight' in self.storage)

        self.storage.update(ten=10)
        self.assertTrue('ten' in self.storage)
        self.storage.update({'eight': 8, 'nine': 9})

    def test_dict_values(self):
        """
        Test Python dict values method. This should be the python 3.x compatible
        values view object.
        """

        values = self.storage.values()
        self.assertFalse(isinstance(values, list))
        self.assertItemsEqual(list(values), [1, 2, 3, 4, 5])

        self.storage['six'] = 6
        self.assertItemsEqual(list(values), [1, 2, 3, 4, 5, 6])
        self.assertEqual(len(values), 6)

    def test_dict_viewitems(self):

        items = self.storage.items()
        self.assertFalse(isinstance(items, list))
        self.assertItemsEqual(list(items), [('one', 1), ('two', 2), ('three', 3), ('four', 4), ('five', 5)])

        # Adding a new item should be reflected in the Keys View
        self.storage['six'] = 6
        self.assertItemsEqual(list(items), [('one', 1), ('two', 2), ('three', 3), ('four', 4), ('five', 5), ('six', 6)])
        self.assertEqual(len(items), 6)

    def test_dict_viewkeys(self):

        keys = self.storage.keys()
        self.assertFalse(isinstance(keys, list))
        self.assertItemsEqual(list(keys), ['five', 'four', 'one', 'three', 'two'])

        # Adding a new key should be reflected in the Keys View
        self.storage['six'] = 6
        self.assertItemsEqual(list(keys), ['one', 'two', 'three', 'four', 'five', 'six'])
        self.assertEqual(len(keys), 6)

    def test_dict_viewvalues(self):

        values = self.storage.values()
        self.assertFalse(isinstance(values, list))
        self.assertItemsEqual(list(values), [1, 2, 3, 4, 5])

        self.storage['six'] = 6
        self.assertItemsEqual(list(values), [1, 2, 3, 4, 5, 6])
        self.assertEqual(len(values), 6)

    def test_dict_truethtest(self):
        """
        Test methods for 'existence' truth test
        """

        # An empty graph
        empty = self.storage_instance()
        e = False
        if empty:
            e = True
        self.assertFalse(e)
        self.assertIsNotNone(empty is None)
        self.assertEqual(len(empty), 0)

        # A graph with content
        e = False
        if self.storage:
            e = True
        self.assertTrue(e)
        self.assertIsNotNone(self.storage is None)
        self.assertNotEqual(len(self.storage), 0)

    def test_dict_comparison(self):
        """
        Test rich key based comparison operators between two storage objects
        """

        graph1 = self.storage_instance({'three': 3, 'four': 4, 'six': 6})
        graph2 = self.storage_instance({'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6})

        self.assertEqual(self.storage.intersection(graph1), {'four', 'three'})
        self.assertEqual(self.storage.difference(graph1), {'five', 'two', 'one'})
        self.assertEqual(self.storage.symmetric_difference(graph1), {'six', 'five', 'two', 'one'})
        self.assertEqual(self.storage.union(graph1), {'six', 'three', 'one', 'four', 'five', 'two'})
        self.assertFalse(self.storage.isdisjoint(graph1))
        self.assertFalse(self.storage.issubset(self.storage, propper=True))
        self.assertTrue(self.storage.issubset(self.storage, propper=False))
        self.assertTrue(graph2.issuperset(self.storage, propper=True))
        self.assertTrue(self.storage.issuperset(self.storage, propper=False))

        self.assertEqual(self.storage & graph1, {'four', 'three'})
        self.assertEqual(self.storage ^ graph1, {'six', 'five', 'two', 'one'})
        self.assertEqual(self.storage | graph1, {'six', 'three', 'one', 'four', 'five', 'two'})
        self.assertFalse(self.storage == graph1)
        self.assertTrue(self.storage != graph1)
        self.assertFalse(self.storage < self.storage)
        self.assertTrue(self.storage <= self.storage)
        self.assertTrue(graph2 > self.storage)
        self.assertTrue(self.storage >= self.storage)


class TestDictStorage(_BaseStorageDriverTests, unittest2.TestCase):
    """
    Unit tests for DictStorage class
    """

    def setUp(self):

        mapping = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5}
        self.storage_instance = DictStorage
        self.storage = DictStorage(mapping)

    def test_dict_view_get(self):

        # Selective view getter
        self.storage.set_view(['one', 'three'])
        self.assertTrue(self.storage.get('two', 2), 2)
        self.assertRaises(KeyError, self.storage.__getitem__, 'four')

    def test_dict_view_magicmethods(self):
        """
        Test dictionary magic methods for a default dictionary
        and for on with a selective view on the main dict.
        """

        # Selective view
        self.storage.set_view(['one', 'three'])
        self.assertEqual(len(self.storage), 2)
        self.assertTrue('one' in self.storage)
        self.assertFalse('five' in self.storage)

        self.assertIn(str(self.storage), ["{'one': 1, 'three': 3}", "{'three': 3, 'one': 1}"])
        self.assertEqual(repr(self.storage), '<DictStorage object {0}: 2 items, is_view: True>'.format(id(self.storage)))

    def test_dict_set_view(self):

        self.storage.set_view(['one', 'three', 'five'])

        self.assertTrue(self.storage.is_view)
        self.assertRaises(KeyError, self.storage.__delitem__, 'two')
        self.assertDictEqual(self.storage.to_dict(), {'three': 3, 'one': 1, 'five': 5})

    def test_dict_view_del(self):

        self.storage.set_view(['one', 'three', 'five'])

        # View contains key
        del self.storage['one']
        self.assertFalse('one' in self.storage)

        # View does not contain key
        self.assertRaises(KeyError, self.storage.__delitem__, 'two')

    def test_dict_view_pop(self):

        self.storage.set_view(['one', 'three', 'five'])

        # View contains key
        pop = self.storage.pop('five')
        self.assertTrue(pop == 5)
        self.assertTrue('five' not in self.storage)

        # View does not contain key
        self.assertRaises(KeyError, self.storage.pop, 'two')

    def test_dict_view_popitem(self):

        self.storage.set_view(['one', 'three', 'five'])

        popitem = self.storage.popitem()
        self.assertTrue(popitem not in self.storage.items())

    def test_dict_view_clear(self):

        self.storage.set_view(['one', 'three', 'five'])

        # Graph clear only operates on selection if is_view
        self.storage.clear()
        self.assertTrue(len(self.storage) == 0)

        self.storage.reset_view()
        self.assertItemsEqual(list(self.storage.keys()), ['four', 'two'])
        self.storage.clear()
        self.assertTrue(len(self.storage) == 0)

    def test_dict_keysview_comaprison(self):
        """
        Test the DictStorage view based keys comparison methods
        """

        keyview = self.storage.keys()
        other = DictStorage({'two': 2, 'three': 3, 'four': 4, 'six': 6})

        self.assertEqual(keyview & other.keys(), {'four', 'two', 'three'})
        self.assertEqual(keyview | other.keys(), {'six', 'three', 'two', 'four', 'five', 'one'})
        self.assertEqual(keyview - other.keys(), {'five', 'one'})
        self.assertEqual(keyview ^ other.keys(), {'five', 'one', 'six'})

    def test_dict_valuesview_comaprison(self):
        """
        Test the DictStorage view based values comparison methods
        """

        values = self.storage.values()
        self.storage['six'] = 6
        
        other = DictStorage({'two': 2, 'three': 3, 'four': 4, 'six': 6})
        self.assertEqual(values & other.values(), {4, 6, 2, 3})
        self.assertEqual(values | other.values(), {1, 2, 3, 4, 5, 6})
        self.assertEqual(values - other.values(), {1, 5})
        self.assertEqual(values ^ other.values(), {1, 5})
