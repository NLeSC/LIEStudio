# -*- coding: utf-8 -*-

"""
Unit tests for the PropKa methods
"""

import os
import unittest2

from lie_propka import RunPropka


class TestPropKa(unittest2.TestCase):

    tmp_files = []
    currpath = os.path.dirname(__file__)
    tmp_dir = os.path.abspath(os.path.join(currpath, '../tmp'))

    def tearDown(self):
        """
        tearDown method called after each unittest to cleanup
        the working directory
        """

        for tmp_file in self.tmp_files:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)

    def test_propka_tmpdir(self):
        """
        Run propka in the systems temporary files directory
        """

        infile = os.path.abspath(os.path.join(self.currpath, '../files/3SGB.pdb'))

        pka = RunPropka()
        out = pka.run_propka(pdb=infile)

        for outputfile in ('pka_file', 'propka_input_file'):
            self.tmp_files.append(out.get(outputfile))
            self.assertIsNotNone(out.get(outputfile))
            self.assertTrue(os.path.isfile(out[outputfile]))

    def test_propka_customdir(self):
        """
        Run propka in the custom temporary files directory
        """

        infile = os.path.abspath(os.path.join(self.currpath, '../files/3SGB.pdb'))

        pka = RunPropka()
        out = pka.run_propka(pdb=infile, workdir=self.tmp_dir)

        for outputfile in ('pka_file', 'propka_input_file'):
            self.tmp_files.append(out.get(outputfile))
            self.assertIsNotNone(out.get(outputfile))
            self.assertTrue(os.path.isfile(out[outputfile]))

    def test_propka_pkaoutput(self):
        """
        Run default propka and validate pKa prediction
        """

        test_pdbs = ('../files/3SGB.pdb', '../files/4DFR.pdb', '../files/1FTJ-Chain-A.pdb',
                     '../files/1HPX.pdb')
        for pdb in test_pdbs:

            infile = os.path.abspath(os.path.join(self.currpath, pdb))
            pka = RunPropka()
            out = pka.run_propka(pdb=infile, workdir=self.tmp_dir)

            for outputfile in ('pka_file', 'propka_input_file'):
                self.tmp_files.append(out.get(outputfile))

            # Parse reference data
            ref = []
            with open('{0}.dat'.format(infile.strip('.pdb')), 'r') as rf:
                ref.extend([float(p.strip()) for p in rf.readlines() if p.strip()])

            calc = out['pka']['pKa'].values()
            self.assertListEqual(calc, ref)

    def test_propka_titrate(self):
        """
        Test PropKa option for predicting on subset of residues (titrate)
        """

        infile = os.path.abspath(os.path.join(self.currpath, '../files/3SGB-subset.pdb'))
        pka = RunPropka()
        out = pka.run_propka(pdb=infile, workdir=self.tmp_dir,
                             titrate_only='E:17,E:18,E:19,E:29,E:44,E:45,E:46,E:118,E:119,E:120,E:139')

        for outputfile in ('pka_file', 'propka_input_file'):
            self.tmp_files.append(out.get(outputfile))

        # Parse reference data
        ref = []
        with open('{0}.dat'.format(infile.strip('.pdb')), 'r') as rf:
            ref.extend([float(p.strip()) for p in rf.readlines() if p.strip()])

        calc = out['pka']['pKa'].values()
        self.assertListEqual(calc, ref)

    def test_propka_warning(self):
        """
        Test PropKa behaviour on input pdb with errors
        """

        infile = os.path.abspath(os.path.join(self.currpath, '../files/1HPX-warn.pdb'))
        pka = RunPropka()
        out = pka.run_propka(pdb=infile, workdir=self.tmp_dir)

        for outputfile in ('pka_file', 'propka_input_file'):
            self.tmp_files.append(out.get(outputfile))
