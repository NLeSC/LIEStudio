# -*- coding: utf-8 -*-

"""
Unit tests for fingerprint methods
"""

import unittest2

from lie_structures.cheminfo_descriptors import available_descriptors
from lie_structures.cheminfo_molhandle import mol_read

AVAIL_DESC = available_descriptors()
TEST_FILES = {'c1(cccnc1Nc1cc(ccc1)C(F)(F)F)C(=O)O': 'smi',
              'CC(Oc1ccccc1C(O)=O)=O': 'smi'}


class _CheminfoDescriptorBase(object):

    test_structures = {}

    @classmethod
    def setUpClass(cls):
        """
        Import a few structures
        """

        for a,b in TEST_FILES.items():
            cls.test_structures[a] = mol_read(a, mol_format=b, toolkit=cls.toolkit_name)

    def test_descriptor(self):
        """
        Test generation of all descriptors
        """

        for struc, molobject in self.test_structures.items():
            if self.toolkit_name in AVAIL_DESC:
                desc = molobject.calcdesc()

                self.assertEqual(len(desc), self.gen_desc[struc])


@unittest2.skipIf('pydpi' not in AVAIL_DESC, "PyDPI software not available or no desc.")
class CheminfoPyDPIDescriptorTests(_CheminfoDescriptorBase, unittest2.TestCase):

    toolkit_name = 'pydpi'
    gen_desc = {'c1(cccnc1Nc1cc(ccc1)C(F)(F)F)C(=O)O': 615,
                'CC(Oc1ccccc1C(O)=O)=O': 615}


@unittest2.skipIf('pybel' not in AVAIL_DESC, "Pybel software not available or no desc.")
class CheminfoPybelDescriptorTests(_CheminfoDescriptorBase, unittest2.TestCase):

    toolkit_name = 'pybel'
    gen_desc = {'c1(cccnc1Nc1cc(ccc1)C(F)(F)F)C(=O)O': 24,
                'CC(Oc1ccccc1C(O)=O)=O': 24}


@unittest2.skipIf('rdk' not in AVAIL_DESC, "RDKit software not available or no desc.")
class CheminfoRDkitDescriptorTests(_CheminfoDescriptorBase, unittest2.TestCase):

    toolkit_name = 'rdk'
    gen_desc = {'c1(cccnc1Nc1cc(ccc1)C(F)(F)F)C(=O)O': 200,
                'CC(Oc1ccccc1C(O)=O)=O': 200}


@unittest2.skipIf('cdk' not in AVAIL_DESC, "CDK software not available or no desc.")
class CheminfoCDKDescriptorTests(_CheminfoDescriptorBase, unittest2.TestCase):

    toolkit_name = 'cdk'


@unittest2.skipIf('webel' not in AVAIL_DESC, "Webel software not available or no desc.")
class CheminfoWebelDescriptorTests(_CheminfoDescriptorBase, unittest2.TestCase):

    toolkit_name = 'webel'
    gen_desc = {'c1(cccnc1Nc1cc(ccc1)C(F)(F)F)C(=O)O': 148,
                'CC(Oc1ccccc1C(O)=O)=O': 147}


@unittest2.skipIf('opsin' not in AVAIL_DESC, "Opsin software not available or no desc.")
class CheminfoOpsinDescriptorTests(_CheminfoDescriptorBase, unittest2.TestCase):

    toolkit_name = 'opsin'


@unittest2.skipIf('indy' not in AVAIL_DESC, "Indigo software not available or no desc.")
class CheminfoIndigoDescriptorTests(_CheminfoDescriptorBase, unittest2.TestCase):

    toolkit_name = 'indy'


@unittest2.skipIf('silverwebel' not in AVAIL_DESC, "Silverwebel software not available or no desc.")
class CheminfoIndigoDescriptorTests(_CheminfoDescriptorBase, unittest2.TestCase):

    toolkit_name = 'silverwebel'


@unittest2.skipIf('jchem' not in AVAIL_DESC, "JChem software not available or no desc.")
class CheminfoIndigoDescriptorTests(_CheminfoDescriptorBase, unittest2.TestCase):

    toolkit_name = 'jchem'