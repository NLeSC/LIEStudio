# -*- coding: utf-8 -*-

"""
Unit tests for the Open Babel methods
"""

import os
import unittest2
import filecmp

from lie_structures.cheminfo_utils import *


class CheminfoTests(unittest2.TestCase):

    tmp_files = []
    currpath = os.path.dirname(__file__)
    ligand_file_mol2 = os.path.join(currpath, '../files/ligand.mol2')
    ligand_file_sdf = os.path.join(currpath, '../files/ligand.sdf')
    
    @classmethod
    def setUpClass(cls):
        """
        PlantsDockingTest class setup

        Read structure files for docking
        """
        
        with open(cls.ligand_file_mol2, 'r') as lfile:
            cls.ligand = lfile.read()

    def tearDown(self):
        """
        tearDown method called after each unittest to cleanup
        the working directory
        """
        
        for tmp_file in self.tmp_files:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)

    def test_readfile(self):
        """
        Test importing structure file with correct format.
        """
        
        moldata = {'molwt': 467.53898000000027, 'atoms': 62}
        
        # Explicit import, format defined
        mol = mol_read(self.ligand_file_mol2, mol_format='mol2', from_file=True)
        self.assertDictEqual({'molwt': mol.molwt, 'atoms': len(mol.atoms)}, moldata)
        
        # Inplicit import, format from file extention
        mol = mol_read(self.ligand_file_mol2, from_file=True)
        self.assertDictEqual({'molwt': mol.molwt, 'atoms': len(mol.atoms)}, moldata)
    
    def test_readfile_unsupported(self):
        """
        Test importing of structure files with wrong format
        """
        
        self.assertIsNone(mol_read(self.ligand_file_mol2, mol_format='non', from_file=True))
        self.assertIsNone(mol_read('/path/not/exist', from_file=True))
        self.assertRaises(AssertionError, mol_read, '/path/not/exist.sdf', from_file=True)
    
    def test_readstring(self):
        """
        Test importing structure from string
        """
        
        moldata = {'molwt': 467.53898000000027, 'atoms': 62}
        
        # Explicit import, format defined
        mol = mol_read(self.ligand, mol_format='mol2')
        self.assertDictEqual({'molwt': mol.molwt, 'atoms': len(mol.atoms)}, moldata)
    
    def test_removeh(self):
        """
        Test removing hydrogens from structure
        """
        
        mol = mol_read(self.ligand, mol_format='mol2')
        numhatoms = len(mol.atoms)
        self.assertEqual(numhatoms, 62)
        
        mol = mol_removeh(mol)
        self.assertEqual(len(mol.atoms), 35)
    
    def test_addh(self):
        """
        Test addition of hydrogens
        """
        
        mol = mol_read(os.path.join(self.currpath, '../files/ccncc_3d_noh.mol2'), from_file=True)
        mol = mol_addh(mol)
        
        out = os.path.join(self.currpath, '../files/test_addh.mol2')
        #self.tmp_files.append(out)
        mol_write(mol, file_path=out, mol_format='mol2')
        self.assertTrue(filecmp.cmp(out, os.path.join(self.currpath, '../files/ccncc_3d.mol2')))
    
    def test_make3D(self):
        """
        Test conversion 1D/2D to 3D structure representation
        """
        
        mol = mol_read('CCNCC', mol_format='smi')
        out = os.path.join(self.currpath, '../files/test1d.mol2')
        self.tmp_files.append(out)
        mol_write(mol, file_path=out, mol_format='mol2')
        self.assertTrue(filecmp.cmp(out, os.path.join(self.currpath, '../files/ccncc_1d.mol2')))
        
        mol = mol_read('CCNCC', mol_format='smi')
        out = os.path.join(self.currpath, '../files/test3d.mol2')
        self.tmp_files.append(out)
        mol_write(mol_make3D(mol, localopt=False), file_path=out, mol_format='mol2')
        self.assertTrue(filecmp.cmp(out, os.path.join(self.currpath, '../files/ccncc_3d.mol2')))
        
        mol = mol_read('CCNCC', mol_format='smi')
        out = os.path.join(self.currpath, '../files/test3dopt.mol2')
        self.tmp_files.append(out)
        mol_write(mol_make3D(mol), file_path=out, mol_format='mol2')
        self.assertTrue(filecmp.cmp(out, os.path.join(self.currpath, '../files/ccncc_1d.mol2')))
    
    def test_rotation(self):
        
        mol = mol_read(self.ligand, mol_format='mol2')
        mols = mol_combine_rotations(mol, rotations=[[1, 0, 0, 90], [1, 0, 0, -90], [0, 1, 0, 90],
                                                     [0, 1, 0, -90], [0, 0, 1, 90], [0, 0, 1, -90]])

