# -*- coding: utf-8 -*-

"""
file: module_model_test.py

Test the pylie LIEModelBuilder methods
"""

import os
import unittest2

from pandas import DataFrame, read_csv

from pylie import LIEDataFrame, LIEModelBuilder


class TestLIEModelBuilder(unittest2.TestCase):
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

        self.model = LIEModelBuilder(dataframe=liedata)

    def tearDown(self):
        """
        tearDown method called after each unittest to cleanup
        the working directory
        """

        for tmpfile in self.tempfiles:
            if os.path.isfile(tmpfile):
                os.remove(tmpfile)

        self.tempfiles = []

    def test_modelbuilder_instance(self):
        """
        Test initiation of empty LIEModelBuilder class
        """

        self.assertTrue(self.model.empty)
        self.assertEqual(self.model._class_name, 'modelbuilder')
        self.assertListEqual(list(self.model.columns),
                             ['set', 'regressor', 'converge', 'L0', 'L1', 'filter_mask', 'N', 'rmsd', 'fit',
                              'iteration', 'rsquared'])

    def test_modelbuilder_model(self):
        """
        Test LIEModelBuilder model method
        """
        m = self.model.model()
        print(m.model.summary())