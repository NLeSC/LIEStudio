# -*- coding: utf-8 -*-

"""
Unit tests for the 2D depiction functionality of the
supported cheminformatics packages.
"""

import os
import unittest2

from lie_structures.cheminfo_molhandle import mol_read
from lie_structures import toolkits


class CheminfoMolDrawTests(unittest2.TestCase):

    tmp_files = []
    currpath = os.path.dirname(__file__)

    def tearDown(self):
        """
        tearDown method called after each unittest to cleanup
        the working directory
        """

        for tmp_file in self.tmp_files:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)

    def test_2d_draw(self):

        for toolkit in toolkits:
            mol = mol_read('c1(cccnc1Nc1cc(ccc1)C(F)(F)F)C(=O)O', mol_format='smi', toolkit=toolkit)
            outfile = os.path.join(self.currpath, '../files/{0}_draw.png'.format(toolkit))
            if mol:
                mol.draw(filename=outfile, show=False)
                self.tmp_files.append(outfile)

                self.assertTrue(os.path.isfile(outfile))