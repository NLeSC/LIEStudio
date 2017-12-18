# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import collections

from .graph import Graph
from .graph_algorithms import dijkstra_shortest_path
from .graph_axis_class import GraphAxisMethods
from .graph_query import GraphQuery


def _flatten_nested_dict(graph_dict, parent_key='', sep='.'):
    """
    Flatten a nested dictionary by concatenating all nested keys.
    Keys are converted to a string representation if needed.

    :param graph_dict: dictionary to flatten
    :type graph_dict:  dict
    :param parent_key: leading string in concatenated keys
    :type parent_key:  str
    :param sep:        concatenation seperator
    :type sep:         str
    :return:           flattened dictionary
    :rtype:            dict
    """

    items = []
    for key, value in graph_dict.items():

        # parse key to string if needed
        if not(isinstance(key, str) or isinstance(key, unicode)):
            logging.debug('Dictionary key {0} of type {1}. Parse to unicode'.format(key, type(key))
            key = unicode(key)

        new_key = unicode(parent_key + sep + key if parent_key else key)
        if isinstance(value, collections.MutableMapping):
            items.extend(_flatten_nested_dict(value, new_key, sep=sep).items())
        else:
            items.append((new_key, value))

    return dict(items)


def _nest_flattened_dict(graph_dict, sep='.'):
    """
    Convert a dictionary that has been flattened by the
    `_flatten_nested_dict` method to a nested representation

    :param graph_dict: dictionary to nest
    :type graph_dict:  dict
    :param sep:        concatenation seperator
    :type sep:         str

    :return:           nested dictionary
    :rtype:            dict
    """

    nested_dict = {}
    for key, value in graph_dict.items():

        splitted = key.split(sep)
        if len(splitted) == 1:
            nested_dict[key] = value

        d = nested_dict
        for k in splitted[:-1]:
            if k not in d:
                d[k] = {}
            d = d[k]

        d[splitted[-1]] = value

    return nested_dict


class ConfigHandler(Graph, GraphAxisMethods):
    """
    ConfigHandler class

    Manages system wide configuration with support for local overrides for a
    user, module or function specific context.
    Settings are internally represented as a graph. The ConfigHandler class
    exposes the graph using an API that mimics a Python dictionary with a
    number of additional methods.

    The 'keys' and 'values' in the dictionary are attributes of a graph node.
    There may be an arbitrary number of attributes in a node having different
    attribute names and values. All of these can be accessed using the same
    dict like API. By default, a loaded configuration will use the 'key'
    attribute name to represent dictionary keys and the 'value' attribute name
    for data.
    The hierarchical structure of a nested dictionary is represented by edges
    connecting the nodes.

    Iterating the graph 'dictionary' returns new ConfigHandler objects
    representing a single node that holds the dictionary 'key' and 'value' in
    the node attributes.
    The `keys`, `values` and `items` methods on the other hand, allow access
    to keys and values directly based on node attribute names.
    """

    sep = '.'

    def __call__(self):
        """
        Implement class __call__ method

        This function will return a **copy** of the (sub)dictionary
        the object represents.

        :return: full configuration dictionary
        :rtype:  dict
        """

        return self.dict(nested=True)

    def __contains__(self, key):
        """
        Implement class __contains__ method

        This is the equivalent of the dict __contains__ method in that it only
        checks the first level of a nested dictionary for the key.
        This method overloads the default method in the Graph class.

        The `contains` method checks for the presence of the key at any
        level.

        :return: if the dictionary contains the key at the first level
        :rtype:  bool
        """

        return key in self.keys()

    def __eq__(self, other):
        """
        Test equality (==) in dictionary keys between two ConfigHandler
        instances

        :param other: other ConfigHandler instance to test for
        :type other:  ConfigHandler instance
        """

        if isinstance(other, ConfigHandler):
            return list(self.keys()) == list(other.keys())

    def __iter__(self):
        """
        Implement class __iter__ method

        Iterate over child nodes of the (sub)graph

        :return: child nodes
        :rtype:  generator object
        """

        root = self._resolve_nid()
        if root is None:
            root = self.root

        for nid in self.children(root):
            yield self.getnodes(nid)

    def __ge__(self, other):
        """
        Test if current ConfigHandler contains equal or more (>=) keys
        than other ConfigHandler.

        :param other: other ConfigHandler instance to test for
        :type other:  ConfigHandler instance
        """

        if isinstance(other, ConfigHandler):
            return len(self) >= len(other)

    def __getattr__(self, key):
        """
        __getattr__ overload.

        Expose dictionary keys as class attributes.
        fallback to the default __getattr__ behaviour.
        Returns subdictionaries from root to leafs for nested dictionaries
        similar to the default dict behaviour.

        :param key: attribute name
        :return:    subdirectory for nested keys, value for unique keys.
        """

        if key == 'nid':
            return object.__getattribute__(self, key)

        query = self.find('{0}{1}'.format(self.sep, key))
        if query is None:
            return object.__getattribute__(self, key)

        query = self.descendant(query[0], include_self=True)
        return self.getnodes(query)

    def __getitem__(self, key):
        """
        __getitem__ overload.

        Get values using dictionary style access, fallback to
        default __getitem__.

        Returns subdictionaries from root to leafs for nested dictionaries
        similar to the default dict behaviour.

        :param key: attribute name
        :type key:  :py:str
        :return:    subdirectory for nested keys, value for unique keys.
        """

        query = self.find('{0}{1}'.format(self.sep, key))
        if query:
            query = self.descendant(query[0], include_self=True)
            return self.getnodes(query)

        return self.__dict__[key]

    def __gt__(self, other):
        """
        Test if current ConfigHandler contains more (>) keys than other
        ConfigHandler.

        :param other: other ConfigHandler instance to test for
        :type other:  ConfigHandler instance
        """

        if isinstance(other, ConfigHandler):
            return len(self) > len(other)

    def __le__(self, other):
        """
        Test if current ConfigHandler contains equal or less (<=) keys
        than other ConfigHandler.

        :param other: other ConfigHandler instance to test for
        :type other:  ConfigHandler instance
        """

        if isinstance(other, ConfigHandler):
            return len(self) <= len(other)

    def __len__(self):
        """
        Implement class __len__ method

        :return: number of dictionary entries
        :rtype:  int
        """

        return len(list(self.keys()))

    def __lt__(self, other):
        """
        Test if current ConfigHandler contains less (<) keys than other
        ConfigHandler.

        :param other: other ConfigHandler instance to test for
        :type other:  ConfigHandler instance
        """

        if isinstance(other, ConfigHandler):
            return len(self) < len(other)

    def __ne__(self, other):
        """
        Test inequality (!=) in dictionary keys between two ConfigHandler
        instances

        :param other: other ConfigHandler instance to test for
        :type other:  ConfigHandler instance
        """

        if isinstance(other, ConfigHandler):
            return list(self.keys()) != list(other.keys())

    def __setattr__(self, key, value):
        """
        __setattr__ overload.

        Set dictionary entries using class attribute setter methods in
        the following order:

        1 self.__dict__ setter at class initiation
        2 config setter handeled by property methods
        3 self.__dict__ only for existing keys
        4 config setter for existing and new keys,value pairs

        :param key:   attribute name.
        :param value: attribute value
        """

        propobj = getattr(self.__class__, key, None)

        if '_initialised' not in self.__dict__:
            return dict.__setattr__(self, key, value)
        elif isinstance(propobj, property) and propobj.fset:
            propobj.fset(self, value)
        elif key in self.__dict__:
            self.__setitem__(key, value)
        else:
            self.set(key, value)

    def __setitem__(self, key, value):
        """
        __setitem__ overload.

        Set values using dictionary style access, fallback to
        default __setattr__

        :param key:   attribute name
        :type key:    str
        :param value: attribute value
        """

        propobj = getattr(self.__class__, key, None)

        if isinstance(propobj, property) and propobj.fset:
            propobj.fset(self, value)
        elif key in self.__dict__:
            dict.__setattr__(self, key, value)
        else:
            self.set(key, value)

    def __str__(self):
        """
        Implement class __str__ method.

        Return a print friendly overview of the current settings.
        Parameter placeholders are not resolved.

        :return: print friendly overview of settings.
        :rtype:  str
        """

        graph_dict = self.dict()

        overview = []
        for key in sorted(graph_dict.keys()):
            value = graph_dict[key]

            # Encode strings to UTF-8
            if isinstance(value, str) or isinstance(value, unicode):
                value = value.strip()

            overview.append('{0}: {1}\n'.format(key, value))

        return ''.join(overview)

    def contains(self, key, keystring='key'):
        """
        Check if key is in graph based dictionary at any level.
        The magic method __contains__ checks only the first level.

        :return: if the graph based dictionary contains the key
        :rtype:  bool
        """

        for nid in self.nodes:
            if (keystring, key) in self.nodes[nid].items():
                return True

        return False

    def dict(self, nested=False, sep='.', keystring='key', valuestring='value',
             default=None, path_method=dijkstra_shortest_path):
        """
        Convert graph representation of the dictionary tree into a dictionary
        using a nested or flattened representation of the dictionary hierarchy.

        In a flattened representation, the keys are concatinated using
        the `sep` seperator.
        Dictionary keys and values are obtained from the node attributes using
        `keystring` and `valuestring` that are set to 'key' and 'value' by
        default.

        The hierarchy in the dictionary is determined by calculating the
        shortest path (dijkstra_shortest_path) from the current root node
        to the leaf nodes (leaves method) in the (sub)graph

        :param nested:      return a nested or flattened dictionary
        :type nested:       bool
        :param sep:         key seperator used in flattrening the dictionary
        :type sep:          str
        :param keystring:   key used to identify dictionary 'key' in node
                            attributes
        :type keystring:    str
        :param valuestring: key used to identify dictionary 'value' in node
                            attributes
        :type valuestring:  str
        :param default:     value to use when node value was not found using
                            valuestring.
        :type default:      mixed
        :param path_method: method used to calculate shortest path between
                            root node and leaf node
        :type path_method:  method
        :rtype:             :py:class:dict

        TODO: get path between nodes closest to root and leaves using closest_to
              method is potentially slow for large graphs.
        """

        if self.root in self.nodes:
            rootnodes = [self.root]
        else:
            rootnodes = self.closest_to(self.root, list(self.nodes.keys()))

        graph_dict = {}
        for nid in rootnodes:
            subgraph = self.descendant(nid)
            subgraph = self.getnodes(subgraph)
            leaves = subgraph.leaves()

            for leave in leaves:
                path = path_method(self._full_graph, nid, leave)
                flattened = sep.join(
                    [str(self._full_graph.nodes[p][keystring]) for p in path])
                graph_dict[flattened] = self._full_graph.nodes[leave].get(valuestring, default)

        if nested:
            graph_dict = _nest_flattened_dict(graph_dict, sep=sep)

        return graph_dict

    def get(self, key, keystring='key', default=None):
        """
        Emulates Pythons dictionary get method

        :return: node having the query key or default
        :rtype:  lie_config.ConfigHandler
        """

        if self.sep in key:
            nids = self.find(key)
            if nids:
                return self.getnodes(nids)
            return default

        root = self._resolve_nid() or self.root
        for nid in self.children(root):
            if keystring in self.nodes[nid] and self.nodes[nid][keystring] == key:
                return self.getnodes(nid)

        return default

    def items(
            self, keystring='key', valuestring='value', defaultstring=None,
            default=None):
        """
        Emulates Pythons dictionary items method.

        Returns a tuple of node key,value pairs. Only return value if key was
        found.

        :param keystring:     key used to identify dictionary 'key' in node
                              attributes
        :type keystring:      str
        :param valuestring:   key used to identify dictionary 'value' in node
                              attributes
        :type valuestring:    str
        :param defaultstring: key to identify dictionary 'value' used as
                              default when valuestring is not in the dictionary
        :type defaultstring:  str
        :param default:       default value to return when `valuestring` and/or
                              `defaultstring` did not return results.
        :type default:        mixed

        :return:              key,value pair as tuple
        :rtype:               generator
        """

        root = self._resolve_nid()
        if root is None:
            root = self.root

        childnodes = self.children(root)

        for nid in childnodes:
            key = self.nodes[nid].get(keystring, None)
            if key is not None:
                child = self.getnodes(nid)
                if child.isleaf:
                    value = child.nodes[nid].get(valuestring, default)
                    if value is None and defaultstring:
                        value = child.nodes[nid].get(defaultstring, default)
                    yield (key, value)
                else:
                    yield (key, child)

    def load(self, config, keystring='key', valuestring='value'):
        """
        Load configuration dictionary.

        This will clear any configuration dictionary already loaded and
        reinitialize the current ConfigHandler class as root for the new
        configuration.
        Use the `update` or `add` methods to update an existing instance
        of a root ConfigHandler class.

        :param config: configuration
        :type config:  :py:class:dict
        """
        pred = isinstance(config, dict)
        msg = "Default configuration needs to be a dictionary type, got: {0}"
        assert pred, TypeError(msg.format(type(config)))

        config = _nest_flattened_dict(config, sep='.')

        # Clear current config
        self.clear()

        self.node_data_tag = keystring
        rootnid = self.add_node('config')
        self.root = rootnid

        def _walk_dict(key, item, rootnid):

            nid = self.add_node(key)
            self.add_edge(rootnid, nid)

            if isinstance(item, dict):
                for k, v in item.items():
                    _walk_dict(k, v, nid)
            else:
                self.nodes[nid][valuestring] = item

        for k, v in config.items():
            _walk_dict(k, v, rootnid)

    def key(self, keystring='key'):

        nid = self._resolve_nid()
        return self.nodes[nid][keystring]

    def keys(self, keystring='key'):
        """
        Emulates Pythons dictionary keys method returning keys at the current
        (nested) dictionary level.

        :param keystring:   key used to identify dictionary 'key' in node
                            attributes
        :type keystring:    str

        :return:            dictionary keys
        :rtype:             generator
        """

        root = self._resolve_nid()
        if root is None:
            root = self.root

        childnodes = self.children(root)
        if self.is_masked:
            return (
                self.nodes[nid][keystring] for nid in childnodes
                if keystring in self.nodes[nid])
        else:
            return (
                self._full_graph.nodes[nid][keystring] for nid in childnodes
                if keystring in self._full_graph.nodes[nid])

    def find(self, key):

        nid = self._resolve_nid()

        if not isinstance(key, (tuple, list)):
            key = [key]

        query = GraphQuery()
        result = []
        for k in key:
            if self.is_masked:
                result.extend(query.query(self, k, nid=nid))
            else:
                result.extend(query.query(self._full_graph, k, nid=nid))

        return [r for r in result if r is not None]

    def set(self, key, value):

        nids = self.find('{0}{1}'.format(self.sep, key))
        for nid in nids:
            if self.is_masked:
                self.nodes[nid]['value'] = value
            else:
                self._full_graph.nodes[nid]['value'] = value

    def update(self, other, replace=True):

        if isinstance(other, ConfigHandler):
            print(other)

    def value(self, valuestring='value'):

        nid = self._resolve_nid()
        return self.nodes[nid][valuestring]

    def values(self, valuestring='value', defaultstring=None, default=None):
        """
        Emulates Pythons dictionary values method.

        :param valuestring:   key used to identify dictionary 'value' in node
                              attributes
        :type valuestring:    str
        :param defaultstring: key to identify dictionary 'value' used
                              as default when valuestring is not in the
                              dictionary
        :type defaultstring:  str
        :param default:       default value to return when `valuestring` and/or
                              `defaultstring` did not return results.
        :type default:        mixed

        :return:              node values or nodes for nested dictionaries.
        :rtype:               generator
        """

        root = self._resolve_nid()
        if root is None:
            root = self.root

        childnodes = self.children(root)

        for nid in childnodes:
            child = self.getnodes(nid)
            if child.isleaf:
                value = child.nodes[nid].get(valuestring, default)
                if value is None and defaultstring:
                    value = child.nodes[nid].get(defaultstring, default)
                yield value
            else:
                yield child
