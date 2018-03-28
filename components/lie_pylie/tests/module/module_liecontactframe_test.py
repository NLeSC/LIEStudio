# -*- coding: utf-8 -*-

"""
file: module_liecontactframe_test.py

Test the pylie protein-ligand contact analysis
"""

import os
import unittest2

from pylie.model.liecontactframe import *


class TestLIEContactFrame(unittest2.TestCase):
    filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../files'))

    def run_test(self, case, ligand):

        # Load the molecule
        mol = os.path.join(self.filepath, '{0}.mol2'.format(case))

        contacts = LIEContactFrame()
        contacts.from_file(mol, filetype='mol2')

        # Get the ligand and resolve rings in the structure
        lig = contacts[contacts['resname'] == ligand]
        rings = find_rings(lig)

        # Get atoms in the neighbourhood of the ligand (binding cavity)
        # Expand to include full amino-acids
        aa = lig.neighbours()
        aa = contacts[contacts['resnum'].isin(set(aa['resnum'].values))]

        contact_frame = lig.contacts(aa)
        contact_frame = eval_hydrophobic_interactions(contact_frame, contacts)
        contact_frame = eval_hbonds(contact_frame, contacts)
        contact_frame = eval_water_bridges(contact_frame, contacts)
        contact_frame = eval_saltbridge(contact_frame, contacts)
        contact_frame = eval_pistacking(contact_frame, contacts, rings=[r[0] for r in rings if r[1] in ('RPA', 'RPN')])
        contact_frame = eval_pication(contact_frame, contacts)
        contact_frame = eval_halogen_bonds(contact_frame, contacts)
        contact_frame = eval_heme_coordination(contact_frame, contacts,
                                               rings=[r[0] for r in rings if r[1] in ('RPA', 'RPN')])

        return contact_frame

    def test_contacts_1acj(self):

        df = self.run_test('1acj', 'THA')

    def test_contacts_1aku(self):

        df = self.run_test('1aku', 'FMN')

    def test_contacts_1ay8(self):

        df = self.run_test('1ay8', 'HCI')

    def test_contacts_1bju(self):

        df = self.run_test('1bju', 'GP6')

    def test_contacts_1bma(self):

        df = self.run_test('1bma', '0QH')
