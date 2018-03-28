# -*- coding: utf-8 -*-

"""
file: module_io_test.py

Test the pylie file format parsers
"""

import os
import unittest2

from pylie.methods.fileio import MOL2Parser, PDBParser

DEFAULT_CONTACT_COLUMN_NAMES = {'atnum':'atnum',
                                'atname':'atname',
                                'atalt':'atalt',
                                'attype':'attype',
                                'resname':'resname',
                                'chain':'chain',
                                'model':'model',
                                'label':'label',
                                'resnum':'resnum',
                                'resext':'resext',
                                'xcoor':'xcoor',
                                'ycoor':'ycoor',
                                'zcoor':'zcoor',
                                'occ':'occ',
                                'b':'b',
                                'segid':'segid',
                                'elem':'elem',
                                'charge':'charge',
                                'group':'group'}


class TestFileIO(unittest2.TestCase):
    filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../files'))

    def test_mol2_parser(self):
        """
        Test import of Tripos MOL2 files
        """

        mol = os.path.join(self.filepath, 'example.mol2')

        parser = MOL2Parser(DEFAULT_CONTACT_COLUMN_NAMES)
        mol2 = parser.parse(open(mol, 'r'))

        # Check if required columns present and of appropriate type.
        for t in ('atname', 'attype', 'resname'):
            self.assertTrue(t in mol2)
            if len(mol2[t]):
                self.assertTrue(all([isinstance(i, str) for i in mol2[t] if i != None]))

        for t in ('xcoor', 'ycoor', 'zcoor', 'charge'):
            self.assertTrue(t in mol2)
            if len(mol2[t]):
                self.assertTrue(all([isinstance(i, float) for i in mol2[t] if i != None]))

        for t in ('resnum', 'atnum'):
            self.assertTrue(t in mol2)
            if len(mol2[t]):
                self.assertTrue(all([isinstance(i, int) for i in mol2[t] if i != None]))

        self.assertEqual(set([len(n) for n in mol2.values() if len(n)]), {50})

    def test_mol2_parser_error(self):
        """
        Not properly formatted MOL2 should raise IOError
        """

        mol = os.path.join(self.filepath, 'example2.mol2')

        parser = MOL2Parser(DEFAULT_CONTACT_COLUMN_NAMES)
        self.assertRaises(IOError, parser.parse, open(mol, 'r'))

        mol = os.path.join(self.filepath, 'example3.mol2')

        parser = MOL2Parser(DEFAULT_CONTACT_COLUMN_NAMES)
        self.assertRaises(IOError, parser.parse, open(mol, 'r'))

    def test_pdb_parser(self):
        """
        Test import of (pseudo) PDB file formats
        """

        mol = os.path.join(self.filepath, 'example.pdb')

        parser = PDBParser(DEFAULT_CONTACT_COLUMN_NAMES)
        pdb = parser.parse(open(mol, 'r'))

        # Check if required columns present and of appropriate type.
        for t in ('atname', 'atalt', 'elem', 'resname', 'resext', 'chain', 'segid'):
            self.assertTrue(t in pdb)
            if len(pdb[t]):
                self.assertTrue(all([isinstance(i, str) for i in pdb[t] if i != None]))

        for t in ('xcoor', 'ycoor', 'zcoor', 'b', 'occ'):
            self.assertTrue(t in pdb)
            if len(pdb[t]):
                self.assertTrue(all([isinstance(i, float) for i in pdb[t] if i != None]))

        for t in ('resnum', 'atnum'):
            self.assertTrue(t in pdb)
            if len(pdb[t]):
                self.assertTrue(all([isinstance(i, int) for i in pdb[t] if i != None]))

        self.assertEqual(set([len(n) for n in pdb.values() if len(n)]), {7527})


