# -*- coding: utf-8 -*-

"""
file: module_filter_test.py

Test pylie filter functions and workflows
"""

import os
import glob
import unittest2

from pandas import read_csv

from pylie import LIEMDFrame, LIEDataFrame
from pylie.filters.filtersplines import FilterSplines
from pylie.filters.filtergaussian import  FilterGaussian


class TestSplineFilter(unittest2.TestCase):
    tempfiles = []
    filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../files'))

    def setUp(self):
        """
        Prepare a fresh LIEMDFrame by importing GROMACS MD energy files
        """

        self.mdframe = LIEMDFrame()
        self.mdframe.from_file(os.path.join(self.filepath, 'unbound.ene'),
                               {'vdwLIE': 'vdw_unbound', 'EleLIE': 'coul_unbound'}, filetype='gromacs')

        for pose, enefile in enumerate(glob.glob(os.path.join(self.filepath, 'bound-*.ene'))):
            self.mdframe.from_file(enefile, {'vdwLIE': 'vdw_bound_{0}'.format(pose + 1),
                                             'EleLIE': 'coul_bound_{0}'.format(pose + 1)},
                                   filetype='gromacs')

        self.tempfiles = []

    def tearDown(self):
        """
        tearDown method called after each unittest to cleanup
        the files directory
        """

        for tmp in self.tempfiles:
            if os.path.exists(tmp):
                os.remove(tmp)

    def test_filtersplines_filter(self):
        """
        Test the filter method of the  FilterSpline class
        """

        # Default spline fit filtering.
        splines = FilterSplines(self.mdframe)
        splines.filter()

        self.assertEqual(len(splines.stable['coul_bound_3']), 3)
        self.assertEqual(len(splines.stable['vdw_bound_3']), 1)

    def test_filtersplines_plot(self):
        """
        Test the plot method of the FilterSpline class
        """

        currpath = os.getcwd()

        # Default spline fit filtering.
        splines = FilterSplines(self.mdframe)
        filtered = splines.filter()

        os.chdir(self.filepath)

        # Save filter results as default png file
        expected = ['{0}-{1}.png'.format(filtered.cases[0], pose) for pose in filtered.poses]
        splines.plot(tofile=True)
        available = glob.glob('*.png')
        self.tempfiles.extend([os.path.abspath(p) for p in available])

        self.assertListEqual(sorted(available), sorted(expected))

        # Save filter results as pdf file
        expected = ['{0}-{1}.pdf'.format(filtered.cases[0], pose) for pose in filtered.poses]
        axis = splines.plot(tofile=True, filetype='pdf')
        available = [f for f in expected if os.path.isfile(f)]
        self.tempfiles.extend([os.path.abspath(p) for p in available])

        self.assertListEqual(sorted(available), sorted(expected))
        self.assertEqual(len(axis), 5)

        os.chdir(currpath)

    def test_filtersplines_average(self):
        """
        Test LIEMDFrame get_average method after filtering
        """

        # Default spline fit filtering.
        splines = FilterSplines(self.mdframe)
        filtered = splines.filter()
        ave = filtered.inliers().get_average()

        # Unbound energies should be same value for all poses
        self.assertEqual(len(ave['coul_unbound'].unique()), 1)
        self.assertEqual(len(ave['coul_unbound']), 5)
        self.assertEqual(len(ave['vdw_unbound'].unique()), 1)
        self.assertEqual(len(ave['vdw_unbound']), 5)

        # Bound energies mostly unique for all poses
        self.assertEqual(len(ave['coul'].unique()), 5)
        self.assertEqual(len(ave['vdw'].unique()), 5)
        self.assertEqual(len(ave['coul']), 5)
        self.assertEqual(len(ave['vdw']), 5)

        # Check values
        self.assertListEqual(list(ave.poses), [1, 2, 3, 4, 5])
        self.assertListEqual(list(ave.cases), [1])
        self.assertAlmostEqual(ave['coul'][0], 73.55964, places=5)
        self.assertAlmostEqual(ave['vdw'][1], -53.78007, places=5)


class TestFilterGaussian(unittest2.TestCase):
    tempfiles = []
    filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../files'))

    def setUp(self):
        """
        Import processed LIE VdW and Coulomb energies for several cases into a LIEDataFrame
        """

        cyp1a2 = os.path.join(self.filepath, 'liedata_CYP1a2.csv')
        self.liedata = LIEDataFrame(read_csv(cyp1a2))
        self.liedata.reset_trainset()
        if 'Unnamed: 0' in self.liedata:
            del self.liedata['Unnamed: 0']

    def tearDown(self):
        """
        tearDown method called after each unittest to cleanup
        the working directory
        """

        for tmpfile in self.tempfiles:
            if os.path.isfile(tmpfile):
                os.remove(tmpfile)

        self.tempfiles = []

    def test_filtergaussian_filter(self):
        """
        Test Multivariate Gaussian filter with different confidence levels
        Start with unfiltered LIEDataFrame
        """

        lentot = len(self.liedata)
        conf = {0.975: 21, 0.95: 29, 0.90: 41, 0.80: 61, 0.75: 74}
        for c in conf:
            gaussian = FilterGaussian(self.liedata)
            gaussian.settings.confidence = c
            filtered = gaussian.filter()
            lenin = len(filtered.outliers)

            self.assertIsInstance(filtered, LIEDataFrame)
            self.assertEqual(lenin, conf[c])
            self.assertEqual(len(filtered.inliers), lentot-lenin)

            outf = os.path.join(self.filepath, 'gauss-{0}.pdf'.format(c))
            self.tempfiles.append(outf)
            p = gaussian.plot()
            p.savefig(outf)
            self.assertTrue(os.path.isfile(outf))