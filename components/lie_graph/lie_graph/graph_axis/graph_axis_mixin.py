# -*- coding: utf-8 -*-

"""
file: graph_mixin.py

NodeTools and EdgeTools classes for axis based graphs (GraphAxis class)
"""

from lie_graph.graph_mixin import NodeTools, EdgeTools


class NodeAxisTools(NodeTools):

    def __getattr__(self, key):
        """
        Implement class __getattr__

        Expose child nodes as class attributes using their primary key (usually
        defined by the node_key_tag). If not found, call __getattr__ on the
        parent class which uses attribute lookup.

        :param key: node key
        :type key:  :py:str

        :return:    node
        """

        # Look for key amongst node children `node_key_tag`
        for child in self:
            if child.get(self.node_key_tag) == key:
                return child

        return super(NodeAxisTools, self).__getattr__(key)

    def __iter__(self):
        """
        Implement class __iter__

        Iterate over the nodes children

        :return: single node graph
        :rtype:  :py:Graph
        """

        for child in self.children(return_nids=True):
            yield self.getnodes(child)


class EdgeAxisTools(EdgeTools):

    pass
