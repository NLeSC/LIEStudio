# -*- coding: utf-8 -*-

"""
file: graph_driver_baseclass.py

Defines a graph driver base class where all driver implementations
have to inherit from.
"""

import abc


class GraphDriverBaseClass(object):
    """
    Base class for graph data storage drivers

    Primary storage of node and edge data is decoupled from the main graph
    structure. Access is enabled using a API with methods that mimic Python
    dictionary like behaviour.
    This setup allows different storage backends to be used transparently
    in a graph settings by constructing a dedicated driver to that storage
    using the API. The GraphDriverBaseClass defines the boilerplate for the
    driver specific API. All driver classes will have to inherit from this
    base class.

    The base class defines a series of abstract methods required for basic
    dictionary like behaviour and additional concrete and clas magic methods
    derived from that.
    A driver is free to implement additional, driver specific methods.
    """
    __metaclass__ = abc.ABCMeta

    # ABSTRACT METHODS
    @abc.abstractmethod
    def __len__(self):
        """
        Implement class __len__

        Returns the number of items in the data store or the selective view.
        """

        return 0

    @abc.abstractmethod
    def copy(self):
        """
        Make a shallow copy the data store or selective view.
        """

        return

    @abc.abstractmethod
    def fromkeys(self, keys, value=None):
        """
        Create a new dictionary with keys from seq and values set to value.

        :param keys:  sequence containing keys
        :param value: default value
        """

        return

    @abc.abstractmethod
    def get(self, key, default=None):
        """
        Defines a method to get a 'value' by 'key' or return default if not
        the key is not defined. This method never raises a KeyError.

        :param key:     dictionary key to get value for
        :param default: default value to return if key does not exist
        """

        return

    @abc.abstractmethod
    def items(self):
        """
        Implement Python 3.x dictionary like 'items' method that returns a
        view on the items in the data store

        :return: data items as tuple of key/value pairs
        :rtype:  items view instance
        """

        return

    @abc.abstractmethod
    def iteritems(self):
        """
        Implement Python 3.x dictionary like 'items' iterator method that
        returns a view on the items in the data store

        :return: data items as tuple of key/value pairs
        :rtype:  items view instance
        """

        return

    @abc.abstractmethod
    def iterkeys(self):
        """
        Implement Python 3.x dictionary like 'keys' iterator method that
        returns a view on the keys in the data store

        :return: data keys
        :rtype:  keys view instance
        """

        return

    @abc.abstractmethod
    def itervalues(self):
        """
        Implement Python 3.x dictionary like 'values' iterator method that
        returns a view on the values in the data store

        :return: data values
        :rtype:  values view instance
        """

        return

    @abc.abstractmethod
    def keys(self):
        """
        Implement Python 3.x dictionary like 'keys' method that returns
        a view on the keys in the data store

        :return: data keys
        :rtype:  keys view instance
        """

        return

    @abc.abstractmethod
    def remove(self, key):
        """
        Base method fro removing key, value pairs from the data storage

        :param key: Key to remove
        """

        return

    @abc.abstractmethod
    def set(self, key, value):
        """
        Defines a method to set the 'value' of a 'key'
        """

        return

    @abc.abstractmethod
    def to_dict(self):
        """
        Return a Python dictionary of the current data view

        :return: py:dict
        """

        return {}

    @abc.abstractmethod
    def values(self):
        """
        Implement Python 3.x dictionary like 'values' method that returns
        a view on the values in the data store

        :return: data values
        :rtype:  values view instance
        """

        return

    @abc.abstractmethod
    def viewitems(self):
        """
        Implement Python 2.7 equivalent of the Python 3.x dictionary like
        'items' method that returns a view on the items in the data store

        :return: data items
        :rtype:  items view instance
        """

        return

    @abc.abstractmethod
    def viewkeys(self):
        """
        Implement Python 2.7 equivalent of the Python 3.x dictionary like
        'keys' method that returns a view on the keys in the data store

        :return: data keys
        :rtype:  keys view instance
        """

        return

    @abc.abstractmethod
    def viewvalues(self):
        """
        Implement Python 2.7 equivalent of the Python 3.x dictionary like
        'values' method that returns a view on the values in the data store

        :return: data values
        :rtype:  values view instance
        """

        return

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

        Calls the class `to_dict` method

        :rtype:  :py:dict
        """

        return self.to_dict()

    def __contains__(self, key):
        """
        Implement class __contains__

        Boolean check if data store contains key

        :param key: key to check existence for

        :rtype:     bool
        """

        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    def __delitem__(self, key):
        """
        Implement class __delitem__

        Remove a key from the data storage using the remove method

        :param key: Key to remove
        """

        if key not in self:
            raise KeyError
        self.remove(key)

    def __eq__(self, other):
        """
        Implement class __eq__

        Implements class equality (==) test as equality between the dictionary
        items of self and other. Items respect dictionary views.

        :rtype:  :py:bool
        """

        if not isinstance(other, (GraphDriverBaseClass, dict)):
            return NotImplemented
        return set(self.items()) == set(other.items())

    def __iter__(self):
        """
        Implement class __iter__

        Iterate over keys in the data
        """

        return self

    def __ge__(self, other):
        """
        Implement class __ge__

        Implements the class greater or equal to (>=) operator calling
        issuperset.

        :rtype: :py:bool
        """

        return self.issuperset(other, propper=False)

    def __getattr__(self, key):
        """
        Implement class __getattr__

        Expose data by key as class attributes.
        Uses the class `get` method to return the value. If the key is not
        present, pass along to the default __getattribute__ method

        :param key: attribute name

        :return:    attribute value
        """

        if key in self:
            return self.get(key)

        return object.__getattribute__(self, key)

    def __getitem__(self, key):
        """
        Implement class __getitem__

        Calls the class `get` method

        :param key: key name

        :return:    key value
        """

        result = self.get(key)
        if result is None:
            raise KeyError(key)

        return result

    def __gt__(self, other):
        """
        Implement class __gt__

        Implements the class greater then (>) operator calling issuperset.

        :rtype: :py:bool
        """

        return self.issuperset(other)

    # Mappings are not hashable by default, but subclasses can change this
    __hash__ = None

    def __le__(self, other):
        """
        Implement class __le__

        Implements the class less then or equal to (<=) operator calling
        issubset

        :rtype: :py:bool
        """

        return self.issubset(other, propper=False)

    def __lt__(self, other):
        """
        Implement class __ge__

        Implements the class less then (<) operator calling issubset.

        :rtype: :py:bool
        """

        return self.issubset(other)

    def __ne__(self, other):
        """
        Implement class __ne__

        Implements class non-equality (!=) test as non-equality between the
        dictionary items of self and other. Items respect dictionary views.

        :rtype:  :py:bool
        """

        return not (self == other)

    def __or__(self, other):
        """
        Implement class __or__

        Implements the bitwise 'or' (or |) which equals the union between the
        keys of this _store and the other _store.
        """

        return self.union(other)

    def __repr__(self):
        """
        Implement class __repr__

        Returns a string representation of the object meta-data
        """

        return '<{0} object {1}: {2} items>'.format(self.__class__.__name__, id(self), len(self))

    def __setattr__(self, key, value):
        """
        Implement class __setattr__

        Set data and class attributes. If the attribute is not yet defined in
        either of these cases it is considered a standard class attribute.
        Use the `set` method to define new data key, value pairs.

        __setattr__ is resolved in the following order:

        1 self.__dict__ setter at class initiation
        2 graph setter handled by property methods
        3 `set` method for existing nodes/edges dictionary attributes.
        3 self.__dict__ only for existing and new class attributes

        :param key:  attribute name.
        :param value: attribute value
        """

        propobj = getattr(self.__class__, key, None)

        if '_initialised' not in self.__dict__:
            return dict.__setattr__(self, key, value)
        elif isinstance(propobj, property) and propobj.fset:
            propobj.fset(value)
        elif key in self:
            self.set(key, value)
        else:
            self.__dict__[key] = value

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
        Returns a string representation of the dictionary.
        The order of the printed dictionary items may vary.

        :rtype: :py:str
        """

        return repr(self.to_dict())

    def __xor__(self, other):
        """
        Implement class __and__

        Implements the bitwise 'xor' (or ^) which equals the
        symmetric_difference between the keys of this data store and the other
        data store.
        """

        return self.symmetric_difference(other)

    __marker = object()

    # RICH SET-BASED COMPARISON METHODS
    def difference(self, other):
        """
        Return the difference between the key set of self and other

        :rtype: :py:class:set
        """

        return set(self.keys()).difference(set(other.keys()))

    def intersection(self, other):
        """
        Return the intersection between the key set of self and other

        :param other:   object to compare to
        :type other:    :py:dict

        :rtype:         :py:class:set
        """

        return set(self.keys()).intersection(set(other.keys()))

    def isdisjoint(self, other):
        """
        Returns a Boolean stating whether the key set in self overlap with the
        specified key set or iterable of other.

        :param other:   object to compare to
        :type other:    :py:dict

        :rtype:         :py:bool
        """

        return len(self.intersection(other)) == 0

    def issubset(self, other, propper=True):
        """
        Keys in self are also in other but other contains more keys
        (propper = True)

        :param other:   object to compare to
        :type other:    :py:dict
        :param propper: ensure that both key lists are not the same.
        :type propper:  :py:bool

        :rtype:         :py:bool
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

        :param other:   object to compare to
        :type other:    :py:dict
        :param propper: ensure that both key lists are not the same.
        :type propper:  :py:bool

        :rtype:         :py:bool
        """

        self_keys = set(self.keys())
        other_keys = set(other.keys())
        if propper:
            return self_keys.issuperset(other_keys) and self_keys != other_keys
        else:
            return self_keys.issuperset(other_keys)

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

    # ABSTRACT METHODS DERIVED DICTIONARY METHODS
    def clear(self):
        """
        Remove all key, value pairs from the data source.
        """

        for key in self.keys():
            self.remove(key)

    def pop(self, key, default=__marker):
        """
        Dictionary like pop methods

        Removes the key and returns the corresponding value or default if the
        key was not found and default is defined, otherwise a KeyError is
        raised.

        :param key:     key to return value for
        :param default: option default value if key is not found

        :return:        value
        """

        try:
            value = self[key]
        except KeyError:
            if default is self.__marker:
                raise
            return default
        else:
            del self[key]
            return value

    def popitem(self):
        """
        Dictionary like popitem methods

        Remove and return some (key, value) pair as a 2-tuple but raises
        KeyError if the object is empty.

        :return: key, value pair
        :rtype:  :py:tuple
        """

        try:
            key = next(iter(self))
        except StopIteration:
            raise KeyError
        value = self[key]
        del self[key]
        return key, value

    def update(self, *args, **kwds):
        """
        Dictionary like update methods

        Update the data store from mapping/iterable (arg) and/or from
        individual keyword arguments (kwargs).

        :param args: mapping/iterable to update from
        :param kwds: keyword arguments to update from
        """

        if args:
            assert len(args) == 1, TypeError('update expected at most 1 arguments, got {0}'.format(len(args)))

            other = args[0]
            if isinstance(other, GraphDriverBaseClass):
                for key, value in other.iteritems():
                    self.set(key, value)
            elif hasattr(other, "keys"):
                for key in other.keys():
                    self.set(key, other[key])
            else:
                for key, value in other:
                    self.set(key, value)

        for key, value in kwds.items():
            self.set(key, value)

    def setdefault(self, key, default=None):
        """
        Dictionary like set default method

        If key is not defined set to default value.

        :param key:     key to set
        :param default: default value to set

        :return:        value
        """

        try:
            return self[key]
        except KeyError:
            self[key] = default

        return default
