# -*- coding: utf-8 -*-

"""
Unit tests for the docking component
"""

import glob
import os
import shutil
import unittest

from lie_plants_docking.plants_docking import PlantsDocking
from lie_plants_docking.utils import (prepaire_work_dir, settings)


# Add modules in package to path so we can import them
__rootpath__ = os.path.dirname(__file__)

# this executable is proprietary, and thus cannot be installed by default
# if the file does not exists we skip the tests involved
exec_path = "/app/bin/plants_linux"


class PlantsDockingTest(unittest.TestCase):

    workdir = None
    ligand_file = os.path.join(__rootpath__, 'files/ligand.mol2')
    protein_file = os.path.join(__rootpath__, 'files/protein.mol2')

    @classmethod
    def setUpClass(cls):
        """
        PlantsDockingTest class setup

        Read structure files for docking
        """

        with open(cls.protein_file, 'r') as pfile:
            cls.protein = pfile.read()

        with open(cls.ligand_file, 'r') as lfile:
            cls.ligand = lfile.read()

    def tearDown(self):
        """
        tearDown method called after each unittest to cleanup
        the working directory
        """
        if self.workdir and os.path.exists(self.workdir):
            shutil.rmtree(self.workdir)

    def test_plants_faultyworkdir(self):
        """
        Docking is unable to start if the working directory
        is not available and cannot be created
        """

        plants = PlantsDocking(workdir='/Users/_dummy_user/lie_plants_docking/tests/plants_docking',
                               exec_path=exec_path,
                               bindingsite_center=[7.79934, 9.49666, 3.39229])

        self.assertFalse(plants.run(self.protein, self.ligand))

    def test_plants_faultyexec(self):
        """
        Docking is unable to start if the PLANTS executable
        is not found
        """
        self.workdir = prepaire_work_dir(__rootpath__, create=True)
        plants = PlantsDocking(workdir=self.workdir,
                               exec_path='/Users/_dummy_user/lie_plants_docking/tests/plants',
                               bindingsite_center=[7.79934, 9.49666, 3.39229])

        self.assertFalse(plants.run(self.protein, self.ligand))

    @unittest.skipIf(not os.path.exists(exec_path), "This test requires proprietary software")
    def test_plants_docking(self):
        """
        A working plants docking
        """
        self.workdir = prepaire_work_dir(__rootpath__, create=True)
        settings['workdir'] = self.workdir
        settings['bindingsite_center'] = [7.79934, 9.49666, 3.39229]
        settings['exec_path'] = exec_path

        plants = PlantsDocking(**settings)
        self.assertTrue(plants.run(self.protein, self.ligand))

        outputfiles = glob.glob('{0}/_entry_00001_conf_*.mol2'.format(self.workdir))
        self.assertEqual(len(outputfiles), plants.config['cluster_structures'])
        self.assertEqual(len(outputfiles), len(plants.results()))
