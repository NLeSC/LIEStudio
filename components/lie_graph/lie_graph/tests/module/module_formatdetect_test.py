# -*- coding: utf-8 -*-

"""
file: module_formatdetect_test.py

Unit tests for the FormatDetect class
"""

import unittest2

from lie_graph.graph_io.io_helpers import FormatDetect


class TestFormatDetect(unittest2.TestCase):

    def test_internal_unicode_handling(self):
        """
        Strings should be converted to unicode internally
        """

        fp = FormatDetect()
        for test in ('notunicode', u'unicode'):
            self.assertEqual(type(fp.parse(test)), unicode)

    def test_unicode_parse(self):
        """
        Test return of string or unicode values that could not be parsed to
        another type.
        """

        test_cases = ['mixed123', u'bel12.2']

        fp = FormatDetect()
        for test in test_cases:
            self.assertEqual(fp.parse(test), unicode(test))

    def test_int_parse(self):
        """
        Test detection of integer values
        """

        test_cases = [(45, 45), ('1', 1), ('188362', 188362), (u'18832', 18832), ('1e3', 1000), ('1E3', 1000),
                      (u'٥', 5), (u'๒', 2), ('-45', -45), ('34,88', '34,88'), (u'22.334.450', 22334450)]

        fp = FormatDetect()
        for test in test_cases:
            self.assertEqual(fp.parse(test[0]), test[1])

    def test_float_parse(self):
        """
        Test detection of float values
        """

        test_cases = [('1.3', 1.3), ('-1.37', -1.37), (34.56, 34.56), (-45.6, -45.6), (u'1.3e2', 130.0),
                      ('34,12', 3412), (u'3.561e+02', 356.1)]

        fp = FormatDetect()
        for test in test_cases:
            self.assertEqual(fp.parse(test[0]), test[1])

    def test_boolean_parse(self):
        """
        Test detection of boolean values
        """

        test_cases = [('true', True), ('True', True), (True, True), ('TRUE', True), (1, 1),
                      ('false', False), ('False', False), (False, False), ('FALSE', False), (0, 0)]

        fp = FormatDetect()
        for test in test_cases:
            self.assertEqual(fp.parse(test[0]), test[1])

    def test_custom_boolean_parse(self):
        """
        Test detection of custom defined boolean values
        """

        test_cases = [('true', True), ('Yes', True), ('y', True), ('false', False), ('no', False), ('n', False)]

        fp = FormatDetect()
        fp.true_types = ['true', 'yes', 'y']
        fp.false_types = ['false', 'no', 'n']
        for test in test_cases:
            self.assertEqual(fp.parse(test[0]), test[1])

    def test_locality_specific_parse(self):

        test_cases = [(u'23.3450,00', 23.345)]

        fp = FormatDetect()
        for test in test_cases:
            self.assertEqual(fp.parse(test[0]), test[1])

    def test_int_detect(self):

        test_cases = [(12, 12), ('12', 12)]

        fp = FormatDetect()
        for test in test_cases:
            self.assertEqual(fp.parse(test[0], target_type='integer'), test[1])
