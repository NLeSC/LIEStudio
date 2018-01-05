# -*- coding: utf-8 -*-

"""
Unit tests for fingerprint methods
"""

import numpy
import unittest2
import scipy.spatial.distance as hr

from lie_structures.cheminfo_fingerprint import (available_fingerprints, mol_fingerprint_comparison,
                                                 mol_fingerprint_pairwise_similarity,
                                                 mol_fingerprint_cross_similarity)
from lie_structures.cheminfo_molhandle import mol_read, mol_make3D

AVAIL_FPS = available_fingerprints()


class CheminfoFingerprintComparisonTests(unittest2.TestCase):
    toolkit_name = 'rdk'

    @classmethod
    def setUpClass(cls):
        """
        PlantsDockingTest class setup

        Read structure files for docking
        """

        smiles = ['c1(c(cccc1Nc1c(cccc1)C(=O)O)C)C',
                  'c12ccccc1nc1c(c2N)CCCC1',
                  'c1ccc(c(c1)[N+](=O)[O-])[C@H]1C(=C(NC(=C1C(=O)OC)C)C)C(=O)OC',
                  'c1cc(ccc1OCC)NC(=O)C',
                  'c12c3c(ccc1c(=O)cc(o2)c1ccccc1)cccc3',
                  'c1cc(cc(c1N/C=N/O)C)CCCC',
                  'c1(cccnc1Nc1cc(ccc1)C(F)(F)F)C(=O)O',
                  'c1ccc(c(c1C)OC[C@H](C)N)C',
                  'c1(OC[C@H](CNC(C)C)O)c2c(ccc1)cccc2',
                  'c12ccccc1cccc2']

        mols = [mol_read(x, mol_format="smi", toolkit=cls.toolkit_name) for x in smiles]
        cls.fps = [m.calcfp('maccs') for m in mols]

    def test_fingerprint_comparison(self):
        """
        Test Tanimoto fingerprint comparison
        """

        fp_sim = mol_fingerprint_comparison(self.fps[0], self.fps[1], self.toolkit_name)
        self.assertAlmostEqual(fp_sim, 0.3, places=4)

    def test_fingerprint_pairwise_similarity(self):
        """
        Test pairwise similarity matrix creation
        """

        simmat = mol_fingerprint_pairwise_similarity(self.fps, self.toolkit_name)
        self.assertTrue(hr.is_valid_dm(simmat))
        self.assertEqual(hr.num_obs_dm(simmat), 10)

    def test_fingerprint_cross_similarity(self):
        """
        Test non-pairwise similarity matrix creation
        """

        simmat = mol_fingerprint_cross_similarity(self.fps[:6], self.fps[3:], self.toolkit_name)
        self.assertEqual(simmat.shape, (6, 7))


# class _CheminfoFingerprintBase(object):
#
#     forcefield = 'mmff94'
#
#     def test_fingerprints_1D(self):
#         """
#         Test generation of fingerprints and Tanimoto coefficients based on
#         1D structure.
#         """
#
#         smiles = ['CCCC', 'CCCN']
#         mols = [mol_read(x, mol_format="smi", toolkit=self.toolkit_name) for x in smiles]
#
#         for fp in available_fingerprints()[self.toolkit_name]:
#             fps = [x.calcfp(fp) for x in mols]
#             self.assertIsNotNone(fps[0] | fps[1])
#
#     def test_fingerprints_3D(self):
#         """
#         Test generation of fingerprints and Tanimoto coefficients based on
#         3D structure. Different to 1D fingerprints for some classes
#         """
#
#         smiles = ['CCCC', 'CCCN']
#         mols = [mol_read(x, mol_format="smi", toolkit=self.toolkit_name) for x in smiles]
#         mols = [mol_make3D(m, forcefield=self.forcefield) for m in mols]
#
#         if all(mols):
#             for fp in available_fingerprints()[self.toolkit_name]:
#                 fps = [x.calcfp(fp) for x in mols]
#                 self.assertIsNotNone(fps[0] | fps[1])
#
#
# @unittest2.skipIf('pybel' not in AVAIL_FPS, "Pybel software not available or no fps.")
# class CheminfoPybelFingerprintTests(unittest2.TestCase, _CheminfoFingerprintBase):
#
#     toolkit_name = 'pybel'
#
# @unittest2.skipIf('rdk' not in AVAIL_FPS, "RDKit software not available or no fps.")
# class CheminfoRDkitFingerprintTests(unittest2.TestCase, _CheminfoFingerprintBase):
#
#     toolkit_name = 'rdk'
#     forcefield = 'uff'
#
#
# @unittest2.skipIf('cdk' not in AVAIL_FPS, "CDK software not available or no fps.")
# class CheminfoCDKFingerprintTests(unittest2.TestCase, _CheminfoFingerprintBase):
#
#     toolkit_name = 'cdk'
#
#
# @unittest2.skipIf('webel' not in AVAIL_FPS, "Webel software not available or no fps.")
# class CheminfoWebelFingerprintTests(unittest2.TestCase, _CheminfoFingerprintBase):
#
#     toolkit_name = 'webel'
#
#
# @unittest2.skipIf('opsin' not in AVAIL_FPS, "Opsin software not available or no fps.")
# class CheminfoOpsinFingerprintTests(unittest2.TestCase, _CheminfoFingerprintBase):
#
#     toolkit_name = 'opsin'
#
#
# @unittest2.skipIf('indy' not in AVAIL_FPS, "Indigo software not available or no fps.")
# class CheminfoIndigoFingerprintTests(unittest2.TestCase, _CheminfoFingerprintBase):
#
#     toolkit_name = 'indy'
#
#
# @unittest2.skipIf('silverwebel' not in AVAIL_FPS, "Silverwebel software not available or no fps.")
# class CheminfoIndigoFingerprintTests(unittest2.TestCase, _CheminfoFingerprintBase):
#
#     toolkit_name = 'silverwebel'
#
#
# @unittest2.skipIf('jchem' not in AVAIL_FPS, "JChem software not available or no fps.")
# class CheminfoIndigoFingerprintTests(unittest2.TestCase, _CheminfoFingerprintBase):
#
#     toolkit_name = 'jchem'