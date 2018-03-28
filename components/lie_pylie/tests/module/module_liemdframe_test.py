# -*- coding: utf-8 -*-

"""
file: module_liemdframe_test.py

Test pylie filter functions and workflows
"""

import os
import glob
import unittest2

from pandas import DataFrame

from pylie import LIEMDFrame
from pylie.methods.fileio import read_gromacs_energy_file
from pylie.filters.filtersplines import FilterSplines


class TestMDFrame(unittest2.TestCase):
    filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../files'))

    def setUp(self):
        """
        Prepare a fresh LIEMDFrame by importing GROMACS MD energy files
        """

        self.mdframe = LIEMDFrame()
        self.mdframe.from_file(os.path.join(self.filepath, 'unbound.ene'),
                               {'vdwLIE': 'vdw_unbound', 'EleLIE': 'coul_unbound'}, filetype='gromacs')

        for pose, enefile in enumerate(glob.glob(os.path.join(self.filepath, 'bound-*.ene'))):
            self.mdframe.from_file(enefile, {'vdwLIE': 'vdw_bound_{0}'.format(pose+1),
                                             'EleLIE': 'coul_bound_{0}'.format(pose+1)}, filetype='gromacs')

    def test_liemdframe_get_average(self):
        """
        Test LIEMDFrame `get_average` method
        """

        ave = self.mdframe.get_average()

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
        self.assertAlmostEqual(ave['coul'][0], 60.12452, places=5)
        self.assertAlmostEqual(ave['vdw'][1], -53.78007, places=5)

    def test_liemdframe_calc_deltaE(self):
        """
        Test LIEMDFrame `calc_deltaE` method.
        The method should calculate deltaE values for every vdw/could energy
        value pair for every pose
        """

        self.mdframe.calc_deltaE()
        self.assertTrue({'vdw_1', 'coul_1', 'vdw_2', 'coul_2', 'vdw_3',
                         'coul_3', 'vdw_4', 'coul_4', 'vdw_5', 'coul_5'}.issubset(set(self.mdframe.columns)))
        self.assertEqual(self.mdframe['vdw_1'].count(), 1000)

    def test_liemdframe_poses(self):
        """
        Test LIEMDFrame poses property method.
        Should return a list with pose id's (5 in this case)
        """

        self.assertListEqual(self.mdframe.poses, [1, 2, 3, 4, 5])

    def test_liemdframe_inliers(self):
        """
        Test LIEMDFrame inlier method as result of filtering
        """

        # Default spline fit filtering.
        splines = FilterSplines(self.mdframe)
        filtered = splines.filter()

        # Inliers, 'single' method
        inliers = filtered.inliers(method='single')
        expected = [{'vdw_bound': (1000, 0, 999), 'coul_bound': (501, 0, 500)},
                    {'vdw_bound': (1000, 0, 999), 'coul_bound': (1000, 0, 999)},
                    {'vdw_bound': (1000, 0, 999), 'coul_bound': (158, 0, 157)},
                    {'vdw_bound': (1000, 0, 999), 'coul_bound': (1000, 0, 999)},
                    {'vdw_bound': (1000, 0, 999), 'coul_bound': (1000, 0, 999)}]
        for pose in inliers.poses:
            self.assertDictEqual(inliers.get_stable(pose), expected[pose-1])

        # Inliers, 'pairs' method. Pairs are the same
        inliers = filtered.inliers(method='pair')
        for pose in inliers.poses:
            stable = inliers.get_stable(pose)
            self.assertEqual(set(stable.values()), set([stable['vdw_bound']]))

        # Inliers, 'global' method. All the same
        inliers = filtered.inliers(method='global')
        for pose in inliers.poses:
            self.assertDictEqual(inliers.get_stable(pose), {'vdw_bound': (158, 0, 157), 'coul_bound': (158, 0, 157)})

    def test_liemdframe_set_stable(self):
        """
        Test LIEMDFrame set_stable method
        """

        # Default spline fit filtering.
        splines = FilterSplines(self.mdframe)
        filtered = splines.filter()

        # Result for pose 2
        orig_stable = filtered.inliers().get_stable(2)

        # Reset stable region for pose 2
        for column in filtered.get_columns('filter_*_*_2'):
            filtered.set_stable(column, 300, 600)
        new_stable = filtered.inliers().get_stable(2)
        self.assertNotEqual(new_stable['vdw_bound'], orig_stable['vdw_bound'])
        self.assertNotEqual(new_stable['coul_bound'], orig_stable['coul_bound'])
        self.assertEqual(new_stable['vdw_bound'], (301, 300, 600))
        self.assertEqual(new_stable['coul_bound'], (301, 300, 600))

        # Unable to set stable region outside trajectory boundaries
        for column in filtered.get_columns('filter_*_*_2'):
            filtered.set_stable(column, 1200, 1300)
        self.assertEqual(filtered.inliers().get_stable(2),
                         {'vdw_bound': (301, 300, 600), 'coul_bound': (301, 300, 600)})


class TestGromacsImport(unittest2.TestCase):
    filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../files'))

    def test_read_gromacs_energy_file(self):
        """
        Test import of GROMACS MD energy trajectories as Pandas DataFrame
        using read_gromacs_energy_file.
        """

        ene_traj_file = os.path.join(self.filepath, 'gromacs_enefile_correct.ene')

        # Default import
        mdframe = read_gromacs_energy_file(ene_traj_file)
        self.assertTrue(isinstance(mdframe, DataFrame))
        self.assertAlmostEqual(mdframe['elelie'].mean(), -143.55004, places=5)
        self.assertAlmostEqual(mdframe['vdwlie'].mean(), -65.15248, places=5)
        self.assertEqual(len(mdframe), 1000)
        self.assertEqual(len(mdframe.columns), 13)

        # Regular headers, lowercase=False
        mdframe = read_gromacs_energy_file(ene_traj_file, lowercase=False)
        self.assertTrue('EleLIE' in mdframe.columns)

        # Selective column import
        mdframe = read_gromacs_energy_file(ene_traj_file, columns=['EleLIE', 'vdwLIE'])
        self.assertEqual(len(mdframe.columns), 4)
        self.assertListEqual(list(mdframe.columns), ['frame', 'time', 'elelie', 'vdwlie'])

        # Wrong GROMACS trajectory file (header does not start with #)
        ene_traj_file = os.path.join(self.filepath, 'gromacs_enefile_wrongheader.ene')
        self.assertIsNone(read_gromacs_energy_file(ene_traj_file))

        # Wrong GROMACS trajectory file (no Time column)
        ene_traj_file = os.path.join(self.filepath, 'gromacs_enefile_wrongheader2.ene')
        self.assertIsNone(read_gromacs_energy_file(ene_traj_file))

    def test_liemdframe_from_file(self):
        """
        Test import of GROMACS MD energy trajectories into a Pandas LIEMDFrame
        """

        ene_traj_file = os.path.join(self.filepath, 'gromacs_enefile_correct.ene')

        # Default import
        mdframe = LIEMDFrame()
        mdframe.from_file(ene_traj_file, {'vdwLIE': 'vdw_unbound', 'EleLIE': 'coul_unbound'}, filetype='gromacs')
        self.assertTrue(isinstance(mdframe, LIEMDFrame))
        self.assertAlmostEqual(mdframe['coul_unbound'].mean(), -143.55004, places=5)
        self.assertAlmostEqual(mdframe['vdw_unbound'].mean(), -65.15248, places=5)
        self.assertEqual(len(mdframe), 1000)
        self.assertEqual(len(mdframe.columns), 6)

        # No right translation dictionary
        self.assertIsNone(LIEMDFrame().from_file(ene_traj_file, {'vdwLIE': 'no_vdw', 'EleLIE': 'no_coul'},
                                                 filetype='gromacs'))

        # Unsupported file type
        self.assertIsNone(LIEMDFrame().from_file(ene_traj_file, {'vdwLIE': 'vdw_unbound', 'EleLIE': 'coul_unbound'},
                                                 filetype='notsupported'))
