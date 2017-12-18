# -*- coding: utf-8 -*-

import logging as logger

from .graph_helpers import GraphException
from .graph_io.io_helpers import _open_anything


class _NodeEdgeBase(object):
    """
    Base class for classes that handle single node or edge graphs.
    """

    def __getattr__(self, key):
        """
        Implement class __getattr__

        Expose node or edge dictionary keys as class attributes.
        Called after the default __getattribute__ lookup it will raise a
        GraphException if the attribute was not found.
        If the key is present, the `get` method is called for it's value.

        :param key: attribute name
        :return:    attribute value
        """

        if key not in self.__dict__:
            value = self.get(key=key, default='_Graph_no_key__')
            if value == '_Graph_no_key__':
                raise GraphException('No such node or edge attribute: {0}'.format(key))

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
            raise GraphException('No such node or edge attribute: {0}'.format(key))

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


class EdgeTools(_NodeEdgeBase):
    """
    Graph methods to overload and extend the methods in the graph base class to
    deal with edge data in single edge graphs.
    """

    def __contains__(self, key):

        nid = self.nid
        if nid:
            return key in self.edges[self.nid]

        return False

    def get(self, key=None, defaultattr=None, default=None):
        """
        Return edge value

        Used by the `value` method to get direct access to relevant node or
        edge attributes. The `value` method itself is a placeholder method
        that can be overloaded by custom classes to post process the data
        before returning it.

        :param key:         node or edge value attribute name. If not defined
                            then attempt to use class wide `node_data_tag`
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

        key = key or self.edge_data_tag
        if key in target:
            return target[key]
        return target.get(defaultattr, default)

    @property
    def nid(self):
        """
        Return the nid of the current selected edge.

        This would actually be 'eid' for edge id rather than node id (nid).
        """

        nids = list(self.edges.keys())
        if nids:
            return nids[0]

        return None

    def set(self, key, value):
        """
        Set edge attribute values.
        The method may be overloaded in custom classes to pre-process data
        before setting.

        :param key:   edge attribute key
        :param value: edge attribute value
        """

        self.edges[self.nid][key] = value


class NodeTools(_NodeEdgeBase):
    """
    Graph methods to overload and extend the methods in the graph base class to
    deal with node data in single node graphs.
    """

    def __contains__(self, key):

        nid = self.nid
        if nid:
            return key in self.nodes[self.nid]
        return False

    def get(self, key=None, default=None, defaultattr=None):
        """
        Return node value

        Used by the `value` method to get direct access to relevant node
        attributes. The `value` method itself is a placeholder method that
        can be overloaded by custom classes to post process the data
        before returning it.

        :param key:         node value attribute name. If not defined then
                            attempt to use class wide `node_data_tag` attribute.
        :type key:          mixed
        :param defaultattr: node or edge value attribute to use as source of
                            default data when `key` attribute is not present.
        :type defaultattr:  mixed
        :param default:     value to return when all fails
        :type default:      mixed
        """

        # Get node attributes
        target = self.nodes[self.nid]

        key = key or self.node_data_tag
        if key in target:
            return target[key]
        return target.get(defaultattr, default)

    def connected_edges(self):
        """
        Return the connected edges to a node

        :return: connected edges
        :rtype:  list
        """

        return [edge for edge in self.edges if self.nid in edge]

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
        :rtype:  mixed
        """

        nids = list(self.nodes.keys())
        if nids:
            return nids[0]

        return None

    def set(self, key, value):
        """
        Set node attribute values.
        The method may be overloaded in custom classes to pre-process data
        before setting.

        :param key:   node attribute key
        :param value: node attribute value
        """

        self.nodes[self.nid][key] = value


class FileHandler(object):

    def get(self, **kwargs):
        """
        Return a file with a URI as file like object
        """

        uri = self._get(key='url', **kwargs)
        if uri is None:
            logger.warning('No file URI defined')

        fobject = _open_anything(uri)
        return fobject
