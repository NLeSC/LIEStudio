# -*- coding: utf-8 -*-

"""
file: graph_mixin.py

Defines an abstract base class for node and edge tool classes that are used for
dynamic (ORM based) Graph class creation.
Node and Edge tools are used when traversing a graph returns single nodes and
single edges.
"""

import abc


class NodeEdgeToolsBaseClass(object):
    """
    Abstract Base class for node specific tools operating on node data in single
    node graphs.
    """
    __metaclass__ = abc.ABCMeta
    __isnetbc__ = True

    @abc.abstractmethod
    def __contains__(self, key):
        """
        Check if node/edge dictionary contains key

        :param key: key to check

        :rtype:     :py:bool
        """

        return False

    def __getattr__(self, key):
        """
        Implement class __getattr__

        Expose node or edge dictionary keys as class attributes.
        Called after the default __getattribute__ lookup it will raise a
        AttributeError if the attribute was not found.
        If the key is present, the `get` method is called for it's value.

        :param key: attribute name
        :return:    attribute value
        """

        if key not in self.__dict__:
            value = self.get(key=key, default='_Graph_no_key__')
            if value == '_Graph_no_key__':
                raise AttributeError('No such node or edge attribute: {0}'.format(key))

            return value

        return object.__getattribute__(self, key)

    def __getitem__(self, key):
        """
        Implement class __getitem__

        Return node or edge attributes by dictionary lookup
        It will raise a GraphException if the attribute was not found, else
        the `get` method is called for it's value.

        :param key: attribute name
        :return:    attribute value
        """

        value = self.get(key=key, default='_Graph_no_key__')
        if value == '_Graph_no_key__':
            raise KeyError('No such node or edge attribute: {0}'.format(key))

        return value

    def __setattr__(self, key, value):
        """
        Implement class __setattr__.

        Setter for both node and edge dictionaries and standard class
        attributes. If the attribute is not yet defined in either of
        these cases it is considered a standard class attribute.
        Use the `set` method to define new node or edge dictionary
        attributes. The latter method can be overloaded by custom
        classes.

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
            propobj.fset(self, value)
        elif key in self:
            self.set(key, value)
        else:
            return dict.__setattr__(self, key, value)

    def __setitem__(self, key, value):
        """
        Implement class __setitem__.

        Set values using dictionary style access in the following order:

        1 graph setter handled by property methods
        2 self.__dict__ only for existing keys
        3 `set` method for existing and new nodes/edges key,value pairs

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

    @abc.abstractmethod
    def get(self, key=None, default=None, defaultattr=None):
        """
        Return node/edge value

        Implement to provide direct access to a node or edge key/value pair
        preferably by using the `get` method of the node/edge storage API.
        The method can be used to manipulate data in the model before returning
        it to the user.

        The method is also used by all format import and export functions to
        get and set (using `set` method) the data from and set to a specific
        format respectively. The graph classes therefor do not have separate
        serializer methods but instead use different get methods to serialize
        the data.

        :param key:         node value attribute name. If not defined then
                            attempt to use class wide `node_value_tag` attribute.
        :type key:          mixed
        :param defaultattr: node or edge value attribute to use as source of
                            default data when `key` attribute is not present.
        :type defaultattr:  mixed
        :param default:     value to return when all fails
        :type default:      mixed
        """

        return

    @abc.abstractmethod
    def nid(self):
        """
        Property returning the current node or edge ID.

        This should return a single value as this property should only be
        implemented on graphs having a single node or edge
        """

        return

    @abc.abstractmethod
    def set(self, key, value):
        """
        Set node/edge key/value pair

        Implement to provide a direct setter for node or edge key/value pairs
        preferably by using the `set` method of the node/edge storage API.

        :param key:         node/edge key to set
        :param value:       node/edge value
        """

        return

    def validate(self, key=None):
        """
        Validate the current node

        Contains validation code for the data represented by the node.

        :param key: key of specific key/value pair to validate
        :type key:  :py:str

        :return:    validation success
        :rtype:     :py:bool
        """

        return True


class NodeTools(NodeEdgeToolsBaseClass):
    """
    Node specific tools
    """

    def __contains__(self, key):
        """
        Check if node/edge dictionary contains key

        :param key: key to check

        :rtype:     :py:bool
        """

        nid = self.nid
        if nid:
            return key in self.nodes[self.nid]
        return False

    def __repr__(self):
        """
        Implement class __repr__

        String representation of the node class.

        :rtype: :py:str
        """

        msg = '<{0} "{1}" object {2} (id: {3}): {4} edges>'

        return msg.format(
            type(self).__name__, self.nodes[self.nid].get(self.node_key_tag, ''), id(self),
            self.nodes[self.nid].get('_id', ''), len(self.adjacency[self.nid]))

    @property
    def isleaf(self):
        """
        Check if the current selected node is a leaf node.

        :rtype: bool
        """

        return len(self.adjacency[self.nid]) == 1

    @property
    def nid(self):
        """
        Return the nid of the current selected node.

        :return: node nid
        """

        if len(self.nodes) == 1:
            return list(self.nodes.keys())[0]

        return None

    def connected_edges(self):
        """
        Return the connected edges to a node

        :return: connected edges
        :rtype:  list
        """

        return [edge for edge in self.edges if self.nid in edge]

    def get(self, key=None, default=None, defaultattr=None):
        """
        Return node value

        Get direct access to relevant node attributes. If `key` is not defined
        the method returns the value of the default node_value_tag which is
        equivalent to returning the value for a dictionary key where the key
        is either the nid or the node_key_tag attribute.

        :param key:         node value attribute name. If not defined then
                            attempt to use class wide `node_value_tag` attribute.
        :type key:          mixed
        :param defaultattr: node or edge value attribute to use as source of
                            default data when `key` attribute is not present.
        :type defaultattr:  mixed
        :param default:     value to return when all fails
        :type default:      mixed
        """

        # Get node attributes
        target = self.nodes[self.nid]

        key = key or self.node_value_tag
        if key in target:
            return target[key]
        return target.get(defaultattr, default)

    def set(self, key, value=None):
        """
        Set node attribute values.

        :param key:   node attribute key
        :param value: node attribute value
        """

        self.nodes[self.nid][key] = value


class EdgeTools(NodeEdgeToolsBaseClass):
    """
    Edge specific tools
    """

    def __contains__(self, key):
        """
        Check if node/edge dictionary contains key

        :param key: key to check

        :rtype:     :py:bool
        """

        nid = self.nid
        if nid:
            return key in self.edges[self.nid]
        return False

    def __repr__(self):
        """
        Implement class __repr__

        String representation of the edge class.

        :rtype: :py:str
        """

        msg = '<{0} "{1}" object {2} id: {3}>'

        return msg.format(
            type(self).__name__, self.edges[self.nid].get(self.edge_key_tag, ''), id(self), self.nid)

    @property
    def nid(self):
        """
        Return the eid of the current selected edge.

        :return: edge eid
        """

        if len(self.edges) == 1:
            return list(self.edges.keys())[0]

        return None

    def get(self, key=None, defaultattr=None, default=None):
        """
        Return edge value

        Used by the `value` method to get direct access to relevant node or
        edge attributes. The `value` method itself is a placeholder method
        that can be overloaded by custom classes to post process the data
        before returning it.

        :param key:         node or edge value attribute name. If not defined
                            then attempt to use class wide `node_key_tag`
                            attribute.
        :type key:          mixed
        :param defaultattr: node or edge value attribute to use as source of
                            default data when `key` attribute is not present.
        :type defaultattr:  mixed
        :param default:     value to return when all fails
        :type default:      mixed
        """

        # Get edge attributes
        target = self.edges[self.nid]

        key = key or self.edge_key_tag
        if key in target:
            return target[key]
        return target.get(defaultattr, default)

    def set(self, key, value):
        """
        Set edge attribute values.
        The method may be overloaded in custom classes to pre-process data
        before setting.

        :param key:   edge attribute key
        :param value: edge attribute value
        """

        self.edges[self.nid][key] = value
