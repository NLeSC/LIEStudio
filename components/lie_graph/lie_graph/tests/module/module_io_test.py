# -*- coding: utf-8 -*-

"""
file: module_io_test.py

Unit tests for import and export of graph data formats
"""

import os
import unittest2

from lie_graph import Graph, GraphAxis
from lie_graph.graph_helpers import graph_directionality
from lie_graph.graph_io.io_tgf_format import read_tgf, write_tgf
from lie_graph.graph_io.io_json_format import read_json, write_json
from lie_graph.graph_io.io_dict_format import read_dict, write_dict
from lie_graph.graph_io.io_web_format import read_web, write_web

from lie_graph.graph_io.io_jsonschema_format import JSONSchemaParser

FILEPATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../files/'))


class FloatArray(object):

    def set(self, key, value):
        assert isinstance(value, list)

        float_array = []
        for v in value:
            float_array.append(float(v))

        self.nodes[self.nid][key] = float_array


class WebParserTest(unittest2.TestCase):
    """
    Unit tests for parsing Spider serialized data structures (.web format)
    """

    web_file = os.path.join(FILEPATH, 'graph.web')
    tempfiles = []

    def tearDown(self):
        """
        tearDown method called after each unittest to cleanup
        the files directory
        """

        for tmp in self.tempfiles:
            if os.path.exists(tmp):
                os.remove(tmp)

    def test_format_import(self):
        """
        Test import of format
        """

        graph = read_web(self.web_file)

        # Default graph attributes set
        self.assertEqual(len(graph), 694)
        self.assertEqual(len(graph.edges), 1386)
        self.assertEqual(graph.is_directed, False)
        self.assertEqual(graph_directionality(graph), 'undirectional')
        self.assertEqual(graph.root, 1)
        self.assertTrue(isinstance(graph, GraphAxis))

        # No ORM or format auto detect set, all values should be strings
        self.assertTrue(isinstance(graph.query_nodes({'key': 'ntrials'}).value, str))
        self.assertTrue(isinstance(graph.query_nodes({'key': 'rotate180_0'}).value, str))

        for node in graph.query_nodes({'key': 'activereslist'}):
            self.assertTrue(isinstance(node.value, list))

        for node in graph.query_nodes({'type': 'FloatArray'}):
            self.assertTrue(all([isinstance(n, str) for n in node.get()]))

    def test_format_import_autoformatparse(self):
        """
        Test import of format with automatic parsing of data types
        """

        graph = read_web(self.web_file, auto_parse_format=True)

        self.assertTrue(isinstance(graph.query_nodes({'key': 'ntrials'}).value, int))
        self.assertTrue(isinstance(graph.query_nodes({'key': 'rotate180_0'}).value, bool))

        for node in graph.query_nodes({'key': 'activereslist'}):
            self.assertTrue(isinstance(node.value, list))

        for node in graph.query_nodes({'type': 'FloatArray'}):
            self.assertTrue(all([isinstance(n, float) for n in node.get()]))

    def test_format_import_orm(self):
        """
        Test import of format with custom ORM classes
        """

        web = GraphAxis()
        web.orm.map_node(FloatArray, {'type': 'FloatArray'})
        web = read_web(self.web_file, graph=web)

        for node in web.query_nodes({'type': 'FloatArray'}):
            self.assertTrue(all([isinstance(n, str) for n in node.get()]))

    def test_format_export(self):
        """
        Test export of format
        """

        graph = read_web(self.web_file, auto_parse_format=True)

        # Export graph as TGF to file
        web = write_web(graph)
        outfile = os.path.join(FILEPATH, 'test_export.web')
        with open(outfile, 'w') as otf:
            otf.write(web)
            self.tempfiles.append(outfile)

        self.assertTrue(os.path.isfile(outfile))

        # Import again and compare source graph
        graph1 = read_web(outfile, auto_parse_format=True)
        self.assertEqual(len(graph), len(graph1))
        self.assertEqual(len(graph.edges), len(graph1.edges))


class TGFParserTest(unittest2.TestCase):
    """
    Unit tests for parsing graphs in Trivial Graph Format (TGF)
    """
    tempfiles = []

    def tearDown(self):
        """
        tearDown method called after each unittest to cleanup
        the files directory
        """

        for tmp in self.tempfiles:
            if os.path.exists(tmp):
                os.remove(tmp)

    def test_format_import(self):
        """
        Test import of format
        """

        tgf_file = os.path.join(FILEPATH, 'graph.tgf')
        graph = read_tgf(tgf_file)

        # Default graph attributes set
        self.assertEqual(len(graph), 11)
        self.assertEqual(len(graph.edges), 11)
        self.assertEqual(graph.is_directed, False)
        self.assertEqual(graph_directionality(graph), 'directional')
        self.assertEqual(graph.root, None)
        self.assertTrue(isinstance(graph, Graph))

        # Because default auto_nid is True, string based node IDs not supported
        self.assertTrue('eleven' not in graph.nodes)
        self.assertTrue(11 in graph.nodes)

    def test_format_export(self):
        """
        Test export of format
        """

        tgf_file = os.path.join(FILEPATH, 'graph.tgf')
        graph = read_tgf(tgf_file)

        # Export graph as TGF to file
        tgf = write_tgf(graph)
        outfile = os.path.join(FILEPATH, 'test_export.tgf')
        with open(outfile, 'w') as otf:
            otf.write(tgf)
            self.tempfiles.append(outfile)

        self.assertTrue(os.path.isfile(outfile))

        # Import again and compare source graph
        graph1 = read_tgf(outfile)
        self.assertTrue(graph1 == graph)

    def test_format_custom_import(self):
        """
        Test TGF import with custom Graph instance
        """

        # Graph axis class with custom nid ID's
        graph = GraphAxis()
        graph.auto_nid = False
        graph.is_directed = True

        tgf_file = os.path.join(FILEPATH, 'graph.tgf')
        graph = read_tgf(tgf_file, graph=graph)

        # Custom graph attributes set and string based node IDs supported
        self.assertEqual(len(graph), 11)
        self.assertEqual(len(graph.edges), 11)
        self.assertEqual(graph.is_directed, True)
        self.assertEqual(graph_directionality(graph), 'directional')
        self.assertTrue(isinstance(graph, GraphAxis))
        self.assertTrue('eleven' in graph.nodes)


class JSONParserTest(unittest2.TestCase):
    """
    Unit tests for parsing graphs in lie_graph module specific JSON format
    """
    tempfiles = []

    def tearDown(self):
        """
        tearDown method called after each unittest to cleanup
        the files directory
        """

        for tmp in self.tempfiles:
            if os.path.exists(tmp):
                os.remove(tmp)

    def test_format_import(self):
        """
        Test import of format. The graph defines a root and thus will be
        imported as a GraphAxis object.
        """

        json_file = os.path.join(FILEPATH, 'graph_axis.json')
        graph = read_json(json_file)

        # Default graph attributes set
        self.assertEqual(len(graph), 35)
        self.assertEqual(len(graph.edges), 72)
        self.assertEqual(graph.is_directed, False)
        self.assertEqual(graph_directionality(graph), 'undirectional')
        self.assertEqual(graph.root, 1)
        self.assertTrue(isinstance(graph, GraphAxis))

        # Because default auto_nid is True, string based node IDs not supported
        self.assertTrue('eleven' not in graph.nodes)
        self.assertTrue(11 in graph.nodes)

    def test_format_export(self):
        """
        Test export of format
        """

        json_file = os.path.join(FILEPATH, 'graph_axis.json')
        graph = read_json(json_file)

        # Export graph as JSON to file
        jsonout = write_json(graph)
        outfile = os.path.join(FILEPATH, 'test_export.json')
        with open(outfile, 'w') as otf:
            otf.write(jsonout)
            self.tempfiles.append(outfile)

        self.assertTrue(os.path.isfile(outfile))

        # Import again and compare source graph
        graph1 = read_json(outfile)
        self.assertTrue(graph1 == graph)


class DictParserTest(unittest2.TestCase):
    """
    Unit test for parsing a Python dictionary to a graph and vice versa
    """
    test_dict = {'one': 1, 'two': {'value': 2, 'extra': True}, 'three': {'value': 3, 'extra': False},
                 4: {'value': 'four', 'five': {'value': 5, 'extra': [2.22, 4.67]}}}

    def test_format_import(self):
        """
        Test import of format.
        """

        graph = read_dict(self.test_dict)

        # Default graph attributes set
        self.assertEqual(len(graph), 13)
        self.assertEqual(len(graph.edges), 24)
        self.assertEqual(graph.is_directed, False)
        self.assertEqual(graph_directionality(graph), 'undirectional')
        self.assertEqual(graph.root, 1)
        self.assertTrue(isinstance(graph, GraphAxis))

        # Because default auto_nid is True, string based node IDs not supported
        self.assertTrue('three' not in graph.nodes)
        self.assertTrue(8 in graph.nodes)

        # Test hierarchy
        self.assertEqual(graph.children().keys(), [4, 'one', 'three', 'two'])
        self.assertEqual(graph.leaves().values(), [[2.22, 4.67], 5, 'four', 1, False, 3, True, 2])
        self.assertEqual(graph.getnodes(4).values(), [[2.22, 4.67]])

        query = graph.query_nodes({'key':'five'})
        self.assertEqual(query.children().items(), [('extra', [2.22, 4.67]), ('value', 5)])

    def test_format_export(self):
        """
        Test export of format
        """

        graph = read_dict(self.test_dict)

        # Export to dict again
        export = write_dict(graph)
        self.assertDictEqual(export, self.test_dict)

        # Export including root
        export = write_dict(graph, include_root=True)
        self.assertDictEqual(export, {'root': self.test_dict})

    def test_format_export_flattened(self):
        """
        Test export of graph as flattened dictionary
        """

        result = {u'three.value': 3, u'two.extra': True, u'4.value': 'four', u'three.extra': False, u'two.value': 2,
                  u'4.five.value': 5, u'4.five.extra': [2.22, 4.67], u'one': 1}
        graph = read_dict(self.test_dict)

        # Export to dict again
        export = write_dict(graph, nested=False)
        self.assertDictEqual(export, result)



class JSONSchemaParserTests(unittest2.TestCase):

    def test_jsonschema_import(self):
        """
        Test import of JSON schema
        """

        schema = os.path.join(FILEPATH, 'jsonschema1.json',)
        parser = JSONSchemaParser(schema)
        #
        # for e in parser.graph:
        #     print(e.key, e.value, e.nid)
        #
        # # Setting wrong type should raise error
        # d = parser.graph.query_nodes({'key': 'dtend'})
        # self.assertRaises(ValueError, d.set, 'key', 3)

        # import pprint
        # pp = pprint.PrettyPrinter()
        # pp.pprint(graph_to_dict(parser.graph, keystring='key', valuestring='value'))