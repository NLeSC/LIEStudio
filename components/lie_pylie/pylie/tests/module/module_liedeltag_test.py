# -*- coding: utf-8 -*-

"""
file: module_liedeltag_test.py

Test pylie liedeltag method for calculating the free energy of binding
(delta G) using the LIE equation
"""

import os
import unittest2

from pandas import read_csv,pivot_table

from pylie import LIEDataFrame
from pylie.model.liedataframe import lie_deltag


class TestLIEDeltag(unittest2.TestCase):
    filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../files'))

    def setUp(self):
        """
        Import processed LIE VdW and Coulomb energies for several cases into a LIEDataFrame
        """

        cyp1a2 = os.path.join(self.filepath, 'liedata_CYP1a2.csv')
        self.liedata = LIEDataFrame(read_csv(cyp1a2))
        if 'Unnamed: 0' in self.liedata:
            del self.liedata['Unnamed: 0']

    def test_liedeltag(self):
        """
        Calculate free energy of binding (delta G) using the LIE equation
        """

        vdw = pivot_table(self.liedata, values='vdw', index=['case'], columns=['poses'])
        coul = pivot_table(self.liedata, values='coul', index=['case'], columns=['poses'])
        ref = self.liedata.groupby(['case', 'ref_affinity']).count().reset_index()['ref_affinity']

        dg_calc = lie_deltag([vdw, coul], params=[0.5, 0.5, 0], kBt=2.49)
        dg_calc['ref_affinity'] = ref
        dg_calc['error'] = abs(dg_calc['ref_affinity'] - dg_calc['dg_calc'])

    def test_liedeltag_framemethod(self):
        """
        Test the liedeltag convenience method part of the LIEDataFrame
        """

        dg_calc = self.liedata.liedeltag()
