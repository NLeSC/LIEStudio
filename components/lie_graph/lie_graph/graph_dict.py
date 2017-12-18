# -*- coding: utf-8 -*-

"""
file: graph_dict.py

Unified view based dictionary class used by the Graph class to store node, edge
and adjacency information.
"""

import weakref

try:
    import collections as colabc
except ImportError:
    import collections.abc as colabc


class DictWrapper(dict):
    """
    Dummy wrapper around Python's native dict class to allow it to be weakly
    referenced by the weakref module.
    """
    pass


class KeysView(colabc.KeysView):
    """
    Handling dictionary key based views

    Extends the collections ABC KeysView class
    """

    __slots__ = ()

    def __contains__(self, key):
        """
        Implements class __contains__

        Check if key is in self KeysView
        """

        return key in set(self)

    def __str__(self):
        """
        Implements class __str__

        :return: keys in KeysView as set
        :rtype:  str
        """

        return repr(set(self))

    def __repr__(self):
        """
        Implements class __repr__

        :return: KeysView instance representation
        :rtype:  str
        """

        return ''.join((type(self).__name__, '(', repr(set(self)), ')'))


class ItemsView(colabc.ItemsView):
    """
    Handling dictionary items based views

    Extends the collections ABC ItemsView class
    """

    __slots__ = ()

    def __contains__(self, item):
        """
        Implements class __contains__

        Check if item is in self ItemsView
        """

        return item in tuple(self)

    def __str__(self):
        """
        Implements class __str__

        :return: items in ItemsView as set
        :rtype:  str
        """

        return repr(tuple(self))

    def __repr__(self):
        """
        Implements class __repr__

        :return: ItemsView instance representation
        :rtype:  str
        """

        return ''.join((type(self).__name__, '(', repr(tuple(self)), ')'))


class ValuesView(colabc.ValuesView):
    """
    Handling dictionary value based views

    Extends the collections ABC ValuesView class
    """

    __slots__ = ()

    def __and__(self, other):
        """
        Implement class __and__

        Implements the bitwise 'and' (or &) which equals the intersection
        between the keys of self and other.
        """

        return set(self).intersection(other)

    def __or__(self, other):
        """
        Implement class __or__

        Implements the bitwise 'or' (or |) which equals the union between the
        keys of this self and other.
        """

        return set(self).union(other)

    def __xor__(self, other):
        """
        Implement class __and__

        Implements the bitwise 'xor' (or ^) which equals the
        symmetric_difference between the keys of this and other.
        """

        return set(self).symmetric_difference(other)

    def __sub__(self, other):
        """
        Implements class __sub__

        :return: difference between values in other with respect to self
        :rtype:  set
        """

        return set(self).difference(other)

    def __contains__(self, value):
        """
        Implements class __contains__

        Check if value is in self ValuesView
        """

        return value in set(self)

    def __str__(self):
        """
        Implements class __str__

        :return: values in ValuesView as set
        :rtype:  str
        """

        return repr(self)

    def __repr__(self):
        """
        Implements class __repr__

        :return: ValuesView instance representation
        :rtype:  str
        """

        return ''.join((type(self).__name__, '(', repr(tuple(self)), ')'))


class GraphDict(colabc.MutableMapping, dict):
    """
    GraphDict class

    Provides a Python native dict like class with unified keys, values, and
    items based dictionary views across Python distributions.
    The class supports weak referencing of the internal dictionary (_storage)
    using the weakref module to reduce memory footprint and enable true
    synchronized views across different instances of the GraphDict class.

    Methods provided by collections.MutableMapping:
    __contains__

    TODO: should the GraphDict comparison methods return a new GraphDict
          object with the intersection, difference, symmetric-difference
          or union of the two graphs instead of the keys and leave the
          respective key,value or item based comparison methods up to the
          KeyView, ValueView and ItemView respectively?
    """

    __slots__ = ('_storage', '_view')

    def __init__(self, *args, **kwargs):
        """
        Implement class __init__

        Initiate the internal _storage dictionary.
        If a GraphDict instance is provided, a _storage dictionary has been
        created and we will setup a weak reference to it. Otherwise init
        a new dictionary using args and/or kwargs as input to the native
        Python dict constructor.
        """

        self._view = None
        self._storage = None

        if len(args):
            mappable = args[0]

            # mappable is GraphDict instance, setup weakref to _storage
            if isinstance(mappable, GraphDict):
                self._storage = weakref.ref(mappable._storage)()

            # mappable is any type accepted by the dict class constructor
            elif mappable is not None:
                self._storage = DictWrapper(mappable)

            # no mappable, setup default DictWrapper with optional kwargs
            else:
                self._storage = DictWrapper(**kwargs)
        else:
            self._storage = DictWrapper(**kwargs)

    def __and__(self, other):
        """
        Implement class __and__

        Implements the bitwise 'and' (or &) which
        equals the intersection between the keys
        of this _store and the other _store.
        """

        return self.intersection(other)

    def __call__(self):
        """
        Implement class __call__

        Calls the class `dict` method
        """

        return self.dict()

    def __delitem__(self, key):
        """
        Implement class __delitem__

        If the GraphDict instance represent a selective view of the main
        dictionary, only allow item deletion for keys in the respective view.

        ..  note:: Do not use this method directly to remove nodes or edges
                   from the graph as it may leave the graph in a funny state.
                   Use the graph remove_node or remove_edge methods instead.

        :param key: dictionary key to remove
        """

        if self.is_view:
            if key not in self._view:
                raise KeyError('"{0}" not part of selective view'.format(key))
            self._view.remove(key)

        del self._storage[key]

    def __eq__(self, other):
        """
        Implement class __eq__

        Implements class equality (==) test as equality between the dictionary
        items of self and other. Items respect dictionary views.

        :rtype:  bool
        """

        if isinstance(other, dict):
            return set(self.items()) == set(other.items())
        return False

    def __ge__(self, other):
        """
        Implement class __ge__

        Implements the class greater or equal to (>=) operator calling
        issuperset.

        :rtype: bool
        """

        return self.issuperset(other, propper=False)

    def __getitem__(self, key):
        """
        Implement class __getitem__

        Calls the class `get` method
        """

        result = self.get(key)
        if result is None:
            raise KeyError(key)

        return result

    def __gt__(self, other):
        """
        Implement class __gt__

        Implements the class greater then (>) operator calling issuperset.

        :rtype: bool
        """

        return self.issuperset(other)

    def __iter__(self):
        """
        Implement class __iter__

        Iterate over keys in _storage
        """

        if self.is_view:
            return iter(self._view)

        return iter(self._storage)

    def __le__(self, other):
        """
        Implement class __le__

        Implements the class less then or equal to (<=) operator calling
        issubset

        :rtype: bool
        """

        return self.issubset(other, propper=False)

    def __len__(self):
        """
        Implement class __len__

        Returns the number of items in the _storage or the selective
        view on it.
        """

        if self.is_view:
            return len(self._view)

        return len(self._storage)

    def __lt__(self, other):
        """
        Implement class __ge__

        Implements the class less then (<) operator calling issubset.

        :rtype: bool
        """

        return self.issubset(other)

    def __ne__(self, other):
        """
        Implement class __ne__

        Implements class non-equality (!=) test as non-equality between the
        dictionary items of self and other. Items respect dictionary views.

        :rtype:  bool
        """

        if isinstance(other, dict):
            return set(self.items()) != set(other.items())
        return True

    def __or__(self, other):
        """
        Implement class __or__

        Implements the bitwise 'or' (or |) which
        equals the union between the keys
        of this _store and the other _store.
        """

        return self.union(other)

    def __repr__(self):
        """
        Implement class __repr__

        Returns a string representation of the object meta-data
        """
        msg = '<{0} object {1}: {2} items, is_view: {3}>'

        return msg.format(
            self.__class__.__name__, id(self), len(self), self.is_view)

    def __setitem__(self, key, value):
        """
        Implement class __setitem__

        Calls the class `set` method

        :param key:   dictionary key to add or update
        :param value: key value
        """

        self.set(key, value)

    def __str__(self):
        """
        Returns a string representation of the dictionary
        The order of the printed dictionarty items may vary.

        :rtype: str
        """

        return repr(self.dict())

    def __xor__(self, other):
        """
        Implement class __and__

        Implements the bitwise 'xor' (or ^) which
        equals the symmetric_difference between the
        keys of this _store and the other _store.
        """

        return self.symmetric_difference(other)

    @property
    def is_view(self):
        """
        Does the current GraphDict represent a selective view on the
        parent dictionary?

        :rtype: bool
        """

        return self._view is not None

    def dict(self, return_full=False):
        """
        Return a shallow copy of the full dictionary.

        If the current GraphDict represent a selective view on the parent
        dictionary then only return a dictionary with a shallow copy of the
        keys in the selective view.

        :param return_full: ignores is_view and return the full dictionary
        :type return_full:  bool

        :rtype:             :py:dict
        """

        return_dict = self._storage
        if self.is_view and not return_full:
            return_dict = {
                k: v for k, v in return_dict.items() if k in self._view}

        return return_dict

    def clear(self):
        """
        Clear key/values from the dictionary.

        If the GraphDict instance represent a selective view of the main
        dictionary, only those keys will be cleared.
        """

        if self.is_view:
            for key in self._view:
                del self[key]
        else:
            self._storage.clear()

    def difference(self, other):
        """
        Return the difference between the key set of self and other

        :rtype: :py:class:set
        """

        return set(self.keys()).difference(set(other.keys()))

    def fromkeys(self, keys):
        """
        Return a shallow copy of the dictionary for selected keys.

        If the GraphDict instance represent a selective view of the main
        dictionary, only those keys will be considered.

        :param keys: keys to return dictionary copy for
        """

        return GraphDict([(k, self[k]) for k in keys if k in self])

    def get(self, key, default=None):
        """
        Implement dictionary getter

        If the GraphDict instance represent a selective view of the main
        dictionary, only allow item getter for keys in the respective view.

        ..  note:: Do not use this method directly to add nodes or edges
                   from the graph as it may leave the graph in a funny state.
                   Use the graph add_node or add_edge methods instead.

        :param key:     dictionary key to get value for
        :param default: default value to return if key does not exist
        """

        if self.is_view:
            if key in self._view:
                return self._storage[key]
            return default

        return self._storage.get(key, default)

    def intersection(self, other):
        """
        Return the intersection between the key set of self and other

        :rtype: :py:class:set
        """

        return set(self.keys()).intersection(set(other.keys()))

    def isdisjoint(self, other):
        """
        Returns a Boolean stating whether the key set in self overlap with the
        specified key set or iterable of other.

        :rtype: bool
        """

        return len(self.intersection(other)) == 0

    def issubset(self, other, propper=True):
        """
        Keys in self are also in other but other contains more keys
        (propper = True)

        :param propper: ensure that both key lists are not the same.
        :type propper:  :py:bool
        """

        self_keys = set(self.keys())
        other_keys = set(other.keys())
        if propper:
            return self_keys.issubset(other_keys) and self_keys != other_keys
        else:
            return self_keys.issubset(other_keys)

    def issuperset(self, other, propper=True):
        """
        Keys in self are also in other but self contains more keys
        (propper = True)

        :param propper: ensure that both key lists are not the same.
        :type propper:  :py:bool
        """

        self_keys = set(self.keys())
        other_keys = set(other.keys())
        if propper:
            return self_keys.issuperset(other_keys) and self_keys != other_keys
        else:
            return self_keys.issuperset(other_keys)

    def items(self):
        """
        Implement Python 3 dictionary like 'items' method that returns a
        DictView class.

        :return: dictionary items as tuple of key/value pairs
        :rtype:  DictView instance
        """

        return ItemsView(self)

    iteritems = items
    viewitems = items

    def keys(self):
        """
        Implement Python 3 dictionary like 'keys' method that returns a DictView
        class.

        :return: dictionary keys
        :rtype:  DictView instance
        """

        return KeysView(self)

    iterkeys = keys
    viewkeys = keys

    def reset_view(self):
        """
        Reset the selective view on the dictionary
        """

        self._view = None

    def set(self, key, value):
        """
        Implement dictionary setter

        ..  note::  Do not use this method directly to add new nodes or edges
            to the graph. Use the graph add_node or add_edge methods for this
            purpose instead.

        :param key:   dictionary key to add or update
        :param value: key value
        """

        self._storage[key] = value
        if self.is_view:
            self._view.add(key)

    def set_view(self, keys):
        """
        Register keys to represent a selective view on the dictionary

        :param keys: keys to set
        :type keys:  list or tuple
        """

        keys = [key for key in keys if key in self._storage]
        self._view = set(keys)

    def symmetric_difference(self, other):
        """
        Return the symmetric difference between the key set of self and other

        :rtype: :py:class:set
        """

        return set(self.keys()).symmetric_difference(set(other.keys()))

    def union(self, other):
        """
        Return the union between the key set of self and other

        :rtype: :py:class:set
        """

        return set(self.keys()).union(set(other.keys()))

    def update(self, other):
        """
        Update key/value pairs in also updating the view if needed

        :param other: other key/value pairs
        :type other:  :py:dict
        """

        self._storage.update(other)
        if self.is_view:
            self._view.update(list(other.keys()))

    def values(self):
        """
        Implement Python 3 dictionary like 'values' method that returns a DictView
        class.

        :return: dictionary values
        :rtype:  DictView instance
        """

        return ValuesView(self)

    itervalues = values
    viewvalues = values
