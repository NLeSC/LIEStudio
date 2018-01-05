# -*- coding: utf-8 -*-

"""
Unit tests for the Open Babel methods
"""

import unittest2
import filecmp

from lie_structures import toolkits
from lie_structures.cheminfo_molhandle import *


class _CheminfoMolhandleBase(object):

    tmp_files = []
    currpath = os.path.dirname(__file__)
    formatexamples = {'mol': os.path.join(currpath, '../files/asperine.mol'),
                      'mol2': os.path.join(currpath, '../files/asperine.mol2'),
                      'cml': os.path.join(currpath, '../files/asperine.cml'),
                      'sdf': os.path.join(currpath, '../files/asperine.sdf'),
                      'inchi': 'InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)',
                      'inchikey': 'BSYNRYMUTXBXSQ-UHFFFAOYSA-N',
                      'iupac': '2-acetyloxybenzoic acid',
                      'can': 'CC(=O)OC1=CC=CC=C1C(=O)O'}

    @classmethod
    def setUpClass(cls):
        """
        PlantsDockingTest class setup

        Read structure files for docking
        """
        
        with open(os.path.join(cls.currpath, '../files/ligand.mol2'), 'r') as lfile:
            cls.ligand = lfile.read()

    def tearDown(self):
        """
        tearDown method called after each unittest to cleanup
        the working directory
        """
        
        for tmp_file in self.tmp_files:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)

    def test_attributes(self):
        """
        Test attributes like informats, descs and so on
        """

        toolkit = toolkits[self.toolkit_name]
        self.assertNotEqual(len(toolkit.informats.keys()), 0)
        self.assertNotEqual(len(toolkit.outformats.keys()), 0)

        if not self.toolkit_name in ('opsin', 'indy', 'webel'):
            self.assertNotEqual(len(toolkit.descs), 0)
            self.assertNotEqual(len(toolkit.forcefields), 0)

        elif not self.toolkit_name == 'opsin':
            self.assertNotEqual(len(toolkit.fps), 0)

    def test_readfile(self):
        """
        Test importing structure file with correct format.
        """

        for molformat in ('sdf', 'mol', 'mol2', 'cml'):
            if molformat in toolkits[self.toolkit_name].informats:

                # Explicit import, format defined
                mol = mol_read(self.formatexamples[molformat], mol_format=molformat, from_file=True,
                               toolkit=self.toolkit_name)
                self.assertEqual(len(mol.atoms), 21)
                self.assertAlmostEqual(mol.molwt, 180.1574, places=4)

                # Implicit import, format from file extension
                mol = mol_read(self.formatexamples[molformat], from_file=True, toolkit=self.toolkit_name)
                self.assertEqual(len(mol.atoms), 21)
                self.assertAlmostEqual(mol.molwt, 180.1574, places=4)
    
    def test_readfile_unsupported(self):
        """
        Test importing of structure files with wrong format
        """
        
        self.assertIsNone(mol_read(self.ligand, mol_format='non', from_file=True, toolkit=self.toolkit_name))
        self.assertIsNone(mol_read('/path/not/exist', from_file=True, toolkit=self.toolkit_name))

    def test_readstring(self):
        """
        Test importing structure from string
        """

        for molformat, infile in self.formatexamples.items():
            if molformat in toolkits[self.toolkit_name].informats:
                 if molformat in ('sdf', 'mol', 'mol2', 'cml'):
                     with open(infile, 'r') as lfile:
                         mol = mol_read(lfile.read(), mol_format=molformat, toolkit=self.toolkit_name)
                 else:
                    mol = mol_read(infile, mol_format=molformat, toolkit=self.toolkit_name)

                 # Opsin has no molwt property:
                 if not self.toolkit_name == 'opsin':
                    self.assertAlmostEqual(mol.molwt, 180.1574, places=4)

    def test_conversion(self):
        """
        Test convert from acetylsaliclyic acid to INCHI and SMILES
        """

        for f,v in self.informats.items():

            mol = mol_read(v, mol_format=f, toolkit=self.toolkit_name)

            for a,b in self.outformats.items():
                self.assertEqual(mol_write(mol, mol_format=a), b)

    def test_readstring_noconversion(self):
        """
        Test import iupac with unsuported notation.
        """

        self.assertIsNone(mol_read("Nosuchname", mol_format='iupac', toolkit=self.toolkit_name))

    def test_readstring_noformat(self):
        """
        Test import benzene with unsupported format. Should raise ValueError
        """

        self.assertIsNone(mol_read("benzene", mol_format='noel', toolkit=self.toolkit_name))

    def test_removeh(self):
        """
        Test removing hydrogens from structure
        """

        mol = mol_read(self.ligand, mol_format='mol2', toolkit=self.toolkit_name)
        numhatoms = len(mol.atoms)
        self.assertEqual(numhatoms, 62)

        mol = mol_removeh(mol)
        self.assertEqual(len(mol.atoms), 35)

    def test_addh(self):
        """
        Test addition of hydrogens
        """

        mol = mol_read(os.path.join(self.currpath, '../files/ccncc_3d_noh.mol2'), from_file=True,
                       toolkit=self.toolkit_name)
        mol = mol_addh(mol)

        out = os.path.join(self.currpath, '../files/test_addh.mol2')
        self.tmp_files.append(out)
        mol_write(mol, file_path=out, mol_format='mol2')
        self.assertTrue(filecmp.cmp(out, os.path.join(self.currpath, '../files/ccncc_3d.mol2')))

    def test_make3D(self):
        """
        Test conversion 1D/2D to 3D structure representation
        """

        mol = mol_read('CCNCC', mol_format='smi', toolkit=self.toolkit_name)
        out = os.path.join(self.currpath, '../files/test1d.mol2')
        self.tmp_files.append(out)
        mol_write(mol, file_path=out, mol_format='mol2')
        self.assertTrue(filecmp.cmp(out, os.path.join(self.currpath, '../files/ccncc_1d.mol2')))

        mol = mol_read('CCNCC', mol_format='smi', toolkit=self.toolkit_name)
        out = os.path.join(self.currpath, '../files/test3d.mol2')
        self.tmp_files.append(out)
        mol_write(mol_make3D(mol, localopt=False), file_path=out, mol_format='mol2')
        self.assertTrue(filecmp.cmp(out, os.path.join(self.currpath, '../files/ccncc_3d.mol2')))

        mol = mol_read('CCNCC', mol_format='smi', toolkit=self.toolkit_name)
        out = os.path.join(self.currpath, '../files/test3dopt.mol2')
        self.tmp_files.append(out)
        mol_write(mol_make3D(mol), file_path=out, mol_format='mol2')
        self.assertTrue(filecmp.cmp(out, os.path.join(self.currpath, '../files/ccncc_1d.mol2')))
    #
    # def test_rotation(self):
    #
    #     mol = mol_read(self.ligand, mol_format='mol2', toolkit=self.toolkit_name)
    #     mols = mol_combine_rotations(mol, rotations=[[1, 0, 0, 90], [1, 0, 0, -90], [0, 1, 0, 90],
    #                                                  [0, 1, 0, -90], [0, 0, 1, 90], [0, 0, 1, -90]])


@unittest2.skipIf('pybel' not in toolkits, "Pybel software not available.")
class CheminfoPybelMolhandleTests(_CheminfoMolhandleBase, unittest2.TestCase):

    toolkit_name = 'pybel'
    informats = {'inchi': "InChI=1/C6H6/c1-2-4-6-5-3-1/h1-6H"}
    outformats = {'smi': 'c1ccccc1',
                  'inchi': 'InChI=1/C6H6/c1-2-4-6-5-3-1/h1-6H',
                  'inchikey': 'UHOVQNZJYSORNB-UHFFFAOYNA-N',
                  'can': 'c1ccccc1'}

@unittest2.skipIf('rdk' not in toolkits, "RDKit software not available.")
class CheminfoRDkitMolhandleTests(_CheminfoMolhandleBase, unittest2.TestCase):

    toolkit_name = 'rdk'
    informats = {'inchi': "InChI=1/C6H6/c1-2-4-6-5-3-1/h1-6H"}
    outformats = {'smi': 'c1ccccc1',
                  'inchi': 'InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H',
                  'inchikey': 'UHOVQNZJYSORNB-UHFFFAOYSA-N',
                  'can': 'c1ccccc1'}


@unittest2.skipIf('pydpi' not in toolkits, "PyDPI software not available.")
class CheminfoPyDPIMolhandleTests(_CheminfoMolhandleBase, unittest2.TestCase):

    toolkit_name = 'pydpi'
    informats = {'inchi': "InChI=1/C6H6/c1-2-4-6-5-3-1/h1-6H",
                 #'casid': "50-12-4",
                 'ncbiid': "2244",
                 'drugbankid': "DB00133",
                 'keggid': "D02176"}
    outformats = {'smi': 'c1ccccc1',
                  'inchi': 'InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H',
                  'inchikey': 'UHOVQNZJYSORNB-UHFFFAOYSA-N',
                  'can': 'c1ccccc1'}


@unittest2.skipIf('cdk' not in toolkits, "CDK software not available.")
class CheminfoCDKMolhandleTests(_CheminfoMolhandleBase, unittest2.TestCase):

    toolkit_name = 'cdk'


@unittest2.skipIf('webel' not in toolkits, "Webel software not available.")
class CheminfoWebelMolhandleTests(_CheminfoMolhandleBase, unittest2.TestCase):

    toolkit_name = 'webel'
    informats = {'inchi': "InChI=1/C6H6/c1-2-4-6-5-3-1/h1-6H"}
    outformats = {'smi': 'c1ccccc1',
                  'inchi': 'InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H',
                  'inchikey': 'InChIKey=UHOVQNZJYSORNB-UHFFFAOYSA-N',
                  'can': 'c1ccccc1'}

    def test_addh(self):

        pass

    def test_removeh(self):

        pass


@unittest2.skipIf('opsin' not in toolkits, "Opsin software not available.")
class CheminfoOpsinMolhandleTests(_CheminfoMolhandleBase, unittest2.TestCase):

    toolkit_name = 'opsin'
    informats = {'iupac': 'benzene'}
    outformats = {'smi': 'C1=CC=CC=C1',
                  'inchi': 'InChI=1/C6H6/c1-2-4-6-5-3-1/h1-6H'}

    def test_readfile(self):
        """
        The Cinfony readfile method is not supported in Opsin
        """
        pass

    def test_removeh(self):

        pass

    def test_addh(self):

        pass

    def test_make3D(self):

        pass


@unittest2.skipIf('indy' not in toolkits, "Indigo software not available.")
class CheminfoIndigoMolhandleTests(_CheminfoMolhandleBase, unittest2.TestCase):

    toolkit_name = 'indy'
    informats = {'inchi': "InChI=1/C6H6/c1-2-4-6-5-3-1/h1-6H"}
    outformats = {'smi': 'C1C=CC=CC=1',
                  'inchi': 'InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H',
                  'inchikey': 'UHOVQNZJYSORNB-UHFFFAOYSA-N',
                  'can': 'C1C=CC=CC=1'}

    def test_removeh(self):
        pass


@unittest2.skipIf('silverwebel' not in toolkits, "Silverwebel software not available.")
class CheminfoIndigoMolhandleTests(_CheminfoMolhandleBase, unittest2.TestCase):

    toolkit_name = 'silverwebel'


@unittest2.skipIf('jchem' not in toolkits, "JChem software not available.")
class CheminfoIndigoMolhandleTests(_CheminfoMolhandleBase, unittest2.TestCase):

    toolkit_name = 'jchem'