# -*- coding: utf-8 -*-

import re


class GraphQuery(object):
    """
    Graph query engine

    Query mini language:

        . = positional argument as either:
            key = search at rootlevel
            .key = search at current node
            ..key = search at any level
        {} = node or edge argument based search:
            'type': seach in 'node' or 'edge'
            'attr': attribute name to match
    """

    def __init__(self, sep='.'):

        self.sep = sep
        self._any_level = '{0}{0}'.format(self.sep)

    def _parse_query_string(self, querystring):

        # Replace position tokens
        querystring = querystring.replace(self._any_level, ' A ')
        querystring = querystring.replace(self.sep, ' S ')
        querystring = querystring.split()
        if not querystring[0] in ('S', 'A'):
            querystring.insert(0, 'R')

        assert len(querystring) % 2 == 0, 'Positional error in query {0}'.format(querystring)

        query_object = []
        for i in range(0, len(querystring), 2):
            pos, key = querystring[i:i + 2]

            m = re.search("({.*})", key)
            attr = {}
            if m:
                for a in m.groups():
                    key = key.split(a)[0]
                    attr = eval(a)

            query_struct = {'key': key, 'type': 'node', 'pos': pos}
            query_struct.update(attr)
            query_object.append(query_struct)

        return query_object

    @staticmethod
    def _attr_match(source, query):

        query = set(query.items())

        return all([q in source.items() for q in query])

    def query_edges(self, graph, pos='R', attr='key', key=None, **kwargs):

        pass

    def query_nodes(self, nid, pos='R', attr='key', key=None, **kwargs):

        if pos == 'S':
            children = []
            for n in nid:
                children.extend(self.graph.children(n))
            result = []
            for child in set(children):
                attributes = self.graph.nodes[child]
                if self._attr_match(attributes, {attr: key}):
                    result.append(child)
            return result

        elif pos == 'A':
            result = []
            for nid, attributes in self.graph.nodes.items():
                if self._attr_match(attributes, {attr: key}):
                    result.append(nid)
            return result

        elif pos == 'R':
            root = self.graph.nodes[self.graph.root]
            if self._attr_match(root, {attr: key}):
                return [self.graph.root]

        return None

    def query(self, graph, querystring, nid=None):

        query_object = self._parse_query_string(querystring)
        self.graph = graph

        if not nid:
            nid = self.graph.nid

        nid = [nid]
        for qo in query_object:
            if qo['type'] == 'node':
                nid = self.query_nodes(nid, **qo)
            elif qo['type'] == 'edge':
                nid = self.query_edges(nid, **qo)
            else:
                nid = None

            if nid is None:
                return None

        return nid
