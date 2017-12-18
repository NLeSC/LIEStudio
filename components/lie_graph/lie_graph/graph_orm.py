# -*- coding: utf-8 -*-

import inspect
import logging as logger


class GraphORM(object):

    def __init__(self, inherit=True):

        self._node_orm_mapping = {}
        self._edge_orm_mapping = {}
        self._node_mapping = {}
        self._edge_mapping = {}
        self._class_name = 'Graph'
        self._inherit = inherit
    
    def _class_factory(self, base_cls, classes):
        """
        Factory for custom Graph classes

        Build custom Graph class by adding classes to base_cls.
        The factory resolves the right method resolution order (mro).

        :param base_cls: graph base class. Needs to be based on Graph class
        :type base_cls:  Graph (inherited) class
        :param classes:  additional classes to include in base class when
                         building custom Graph class
        :type classes:   list or tuple

        :return:         custom Graph class
        :rtype:          class
        """

        # Get method resolution order for the base_cls and filter for base
        # classes created by the GraphORM class to keep the mro clean.
        base_cls_mro = [c for c in inspect.getmro(base_cls) if not self.__module__ == c.__module__]

        # Inherit previous custom modules or only graph module classes
        if not self._inherit:
            base_cls_mro = [c for c in base_cls_mro if c.__module__.startswith('lie_graph')]

        # Add custom classes to the base class mro
        for n in reversed(classes):
            if n not in base_cls_mro:
                base_cls_mro.insert(0, n)

        # Build the new base class
        base_cls_name = self._class_name or base_cls.__name__
        base_cls = type(base_cls_name, tuple(base_cls_mro), {'adjacency': None, 'nodes': None, 'edges': None})
        return base_cls

    @property
    def mapped_node_types(self):
        """
        Returns a dictionary with all mapped node attributes
        """

        return self._node_mapping

    @property
    def mapped_edge_types(self):
        """
        Returns a dictionary with all mapped edge attributes
        """

        return self._edge_mapping

    def map_node(self, cls, node_attr=None, **kwargs):
        """
        Assign a class to be mapped to a node based on node attributes

        :param cls:        class to map
        :type cls:         class
        :param node_attr:  node attributes to match
        :type node_attr:   :py:class:dict
        :param kwargs:     additional keyword arguments to add to matching
                           dictionary
        """

        assert inspect.isclass(cls), TypeError('cls attribute is not a class')

        matching_rules = {}
        if node_attr:
            assert isinstance(node_attr, dict), TypeError('node_attr not of type dictionary')
            matching_rules.update(node_attr)

        matching_rules.update(kwargs)
        assert len(matching_rules) > 0, 'No node attribute matching rules defined for ORM class: {0}'.format(cls)

        for k, v in matching_rules.items():
            if k not in self._node_mapping:
                self._node_mapping[k] = []
            self._node_mapping[k].append(v)

        self._node_orm_mapping[cls] = set(matching_rules.items())

    def map_edge(self, cls, edge_attr=None, **kwargs):
        """
        Assign a class to be mapped to an edge based on edge attributes

        :param cls:        class to map
        :type cls:         class
        :param edge_attr:  edge attributes to match
        :type edge_attr:   :py:class:dict
        :param kwargs:     additional keyword arguments to add to matching
                           dictionary
        """

        assert inspect.isclass(cls), TypeError('cls attribute is not a class')

        matching_rules = {}
        if edge_attr:
            assert isinstance(edge_attr, dict), TypeError('edge_attr not of type dictionary')
            matching_rules.update(edge_attr)

        matching_rules.update(kwargs)
        assert len(matching_rules) > 0, 'No edge attribute matching rules defined for ORM class: {0}'.format(cls)

        for k, v in matching_rules.items():
            if k not in self._edge_mapping:
                self._edge_mapping[k] = []
            self._edge_mapping[k].append(v)

        self._edge_orm_mapping[cls] = set(matching_rules.items())

    def get(self, graph, objects, base_cls, classes=None):
        """
        Map a custom class to a node or edge based on their attributes.

        Both attribute key and value are considered in the matching.

        TODO:

            extend matching engine to match only key or values and use
            logical operators on values.

        If there is nothing to map, return the base class which by default is
        the same class as the Graph instance making the call to the get method.

        :param graph:                       a graph to match against
        :type graph:                        `lie_graph.graph.Graph`
        :param objects:                     one or more nodes or edges to match against
        :type objects:                      list
        :param base_cls:                    graph base class. Needs to be based on Graph class
        :type base_cls:                     `lie_graph.graph.Graph` (inherited) class
        :param classes:                     additional classes to include in base class when
                                            building custom Graph class
        :type classes:                      list or tuple
        """

        # Are we matching edges? or nodes?
        is_edges = all([type(i) in (tuple, list) for i in objects])
        if not is_edges:

            is_nodes = all([type(i) in (int, str, unicode) for i in objects])
            assert is_nodes, 'Query need to be only nodes or only edges not mixed.'

        # Get the node/edge attributes to match against
        query = []
        for i in objects:
            attr = graph.attr(i)
            if isinstance(attr, dict):
                query.extend([(k, v) for k, v in attr.items() if not type(v) in (list, dict)])

        # query matching based on set operation, does not work for unhashable types
        try:
            query = set(query)
        except TypeError:
            logger.error('Unable to build query')
            query = set([])

        # Use node or edge mapping dictionary
        mapper = self._node_orm_mapping
        if is_edges:
            mapper = self._edge_orm_mapping

        # Match
        orm_classes = []
        for node, mapping in mapper.items():
            if mapping.intersection(query) == mapping:
                orm_classes.append(node)

        # Build and return custom class
        if classes:
            orm_classes.extend(classes)

        return self._class_factory(base_cls, orm_classes)
