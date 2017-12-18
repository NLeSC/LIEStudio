# -*- coding: utf-8 -*-

"""
file: module_gridscan_test.py

Test the pylie LIEScanDataFrame methods
"""

import os
import unittest2

from pandas import DataFrame, read_csv

from pylie import LIEScanDataFrame, LIEDataFrame


class TestLIEScanDataFrame(unittest2.TestCase):
    filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../files'))
    tempfiles = []

    def setUp(self):
        """
        Import processed LIE VdW and Coulomb energies for several cases into a LIEDataFrame.
        Create a scan dataframe using the LIEDataFrame
        """

        cyp1a2 = os.path.join(self.filepath, 'liedata_CYP1a2.csv')
        liedata = LIEDataFrame(read_csv(cyp1a2))
        if 'Unnamed: 0' in liedata:
            del liedata['Unnamed: 0']

        self.abscan = LIEScanDataFrame()
        self.abscan.scan(liedata)

    def tearDown(self):
        """
        tearDown method called after each unittest to cleanup
        the working directory
        """

        for tmpfile in self.tempfiles:
            if os.path.isfile(tmpfile):
                os.remove(tmpfile)

        self.tempfiles = []

    def test_scanframe_plots(self):
        """
        Test creation of custom LIEScanDataFrame plot types
        """

        for plot_type in ('simmatrix', 'optimal', 'error', 'density', 'vector', 'dendrogram'):
            export = os.path.join(self.filepath, 'alphabetascan_{0}.pdf'.format(plot_type))
            fig = self.abscan.plot(kind=plot_type)
            fig.savefig(export)

            self.tempfiles.append(export)
            self.assertTrue(os.path.isfile(export))

    def test_scanframe_get_matrix(self):
        """
        Test export of alpha x beta scan matrix as matrix with cases on y-axis
        and a double x-axis containg alpha and beta scan parameters.
        """

        matrix = self.abscan.get_matrix()
        self.assertEqual(matrix.shape, (len(self.abscan.cases), self.abscan.Sa * self.abscan.Sb))

    def test_scanframe_get_optimal(self):
        """
        Test LIEScanDataFrame 'get_optimal' method
        """

        optimal = self.abscan.get_optimal()

        self.assertIsInstance(optimal, DataFrame)
        self.assertEqual(list(optimal.index), self.abscan.cases)
        self.assertEqual(list(optimal.columns), ['alpha', 'beta', 'error'])

    def test_scanframe_get_cases(self):
        """
        Get all cases that are within 3 dg error within a defined
        alpha x beta scan range
        """

        print(self.abscan.get_cases([0.3,0.5], [0.3,0.5], error=3))

    def test_scanframe_propensity_distribution(self):

        propd = self.abscan.propensity_distribution()

        self.assertIsInstance(propd, DataFrame)
        self.assertEqual(list(propd['case']), self.abscan.cases)
        self.assertEqual(list(propd['pose']), self.abscan.cases)
        self.assertEqual(list(propd.columns), ['case', 'pose', 'tag', 'min', 'max',
                                               'mean', 'slope', 'total', 'overlap'])