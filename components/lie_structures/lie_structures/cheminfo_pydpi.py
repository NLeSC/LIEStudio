# -*- coding: utf-8 -*-

"""
file: cheminfo_pydpi.py

PyDPI package wrapper.
Exposes the PyDPI functionality using a Cinfony like interface

Citation:
D. Cao, Y. Liang, J. Yan, G. Tan, Q. Xu and S. Liu, "PyDPI: Freely Available
Python Package for Chemoinformatics, Bioinformatics, and Chemogenomics Studies"
Journal of Chemical Information and Modeling 2013 53 (11), 3086-3096
DOI: 10.1021/ci400127q
"""

import os
import logging

from rdkit import Chem
from pydpi.drug import getmol, fingerprint
from pydpi.pydrug import PyDrug
from cinfony.rdk import Molecule as RdkMolecule
from cinfony.rdk import descs as rdk_descs
from cinfony.rdk import readstring as rdk_readstring
from cinfony.rdk import informats, outformats, forcefields, Fingerprint

# Available descriptors
descs = rdk_descs

# Available fingerprints
fps = ['topological', 'Estate', 'atompairs', 'torsions', 'morgan', 'MACCS']

# PyDPI specific formats (online database support)
_formats = {'casid': 'CAS database ID',
            'ncbiid': 'NCBI database ID',
            'keggid': 'KEGG database ID',
            'drugbankid': 'DrugBank ID'}
informats.update(_formats)


def readstring(format, string):
    """
    Read a molecule from a string

    PyDPI adds the following string input formats on top of the ones
    supported by rdk (RDKit):

    * casid:      download molecule by CAS ID
    * ncbiid:     download molecule by NCBI ID
    * keggid:     download molecule by KEGG ID
    * drugbankid: download molecule by DrugBank ID

    :param format: see the informats variable for a list of available
                   input formats
    :type format:  :py:str
    :param string: string to import
    :type string:  :py:str

    :return:       :Molecule
    """

    # PyDPI support for online databases. Downloaded as smiles string
    # and subsequently imported into rdk Molecule
    if format in _formats:
        smi = None
        if format == 'casid':
            smi = getmol.GetMolFromCAS(string)
        elif format == 'ncbiid':
            smi = getmol.GetMolFromNCBI(string)
        elif format == 'keggid':
            smi = getmol.GetMolFromKegg(string)
        elif format == 'drugbankid':
            smi = getmol.GetMolFromDrugbank(string)
        else:
            pass

        if smi:
            format = 'smi'
            string = smi

    molobj = rdk_readstring(format, string)
    return Molecule(molobj.Mol)


def readfile(format, filename):
    """
    Iterate over the molecules in a file.

    You can access the first molecule in a file using the next() method
    of the iterator:
        mol = readfile("smi", "myfile.smi").next()

    You can make a list of the molecules in a file using:
        mols = list(readfile("smi", "myfile.smi"))

    :param format:   see the informats variable for a list of available
                     input formats
    :type format:    :py:str
    :param filename: filename to import
    :type filename:  :py:str
    """
    if not os.path.isfile(filename):
        raise IOError, "No such file: '%s'" % filename
    format = format.lower()
    # Eagerly evaluate the supplier functions in order to report
    # errors in the format and errors in opening the file.
    # Then switch to an iterator...
    if format == "sdf":
        iterator = Chem.SDMolSupplier(filename)

        def sdf_reader():
            for mol in iterator:
                yield Molecule(mol)
        return sdf_reader()
    elif format == "mol":

        def mol_reader():
            yield Molecule(Chem.MolFromMolFile(filename))
        return mol_reader()
    elif format == "mol2":

        def mol_reader():
            yield Molecule(Chem.MolFromMol2File(filename))
        return mol_reader()
    elif format == "smi":
        iterator = Chem.SmilesMolSupplier(filename, delimiter=" \t",
                                          titleLine=False)

        def smi_reader():
            for mol in iterator:
                yield Molecule(mol)
        return smi_reader()
    elif format == 'inchi' and Chem.INCHI_AVAILABLE:

        def inchi_reader():
            for line in open(filename, 'r'):
                mol = Chem.inchi.MolFromInchi(line.strip())
                yield Molecule(mol)
        return inchi_reader()
    else:
        raise ValueError("%s is not a recognised RDKit format" % format)


class Molecule(RdkMolecule):
    """
    Represents a PyDPI Molecule.

    PyDPI uses RDKit for representing molecules and calculating many of its
    descriptors and fingerprints.
    This class is essentially a wrapper around the Cinfony rdk Molecule class
    with methods supplemented with PyDPI functionality.
    """

    def calcdesc(self, descnames=None):
        """
        Calculate descriptor values.

        If descnames is not specified, all available descriptors are
        calculated. See the descs variable for a list of available
        descriptors.

        :param descnames: a list of names of descriptors
        :type descnames:  :py:list

        :return:          calculated descriptors
        :rtype:           :py:dict
        """

        drug = PyDrug()
        drug.mol = self.Mol
        calc_desc = drug.GetAllDescriptor()

        if descnames:
            non_avail = [d for d in descnames if d not in calc_desc]
            if non_avail:
                logging.error('PyDPI descriptors not available: {0}'.format(','.join(non_avail)))
            return dict([(d, calc_desc[d]) for d in descnames])

        return calc_desc

    def calcfp(self, fptype="topological", opt=None):
        """
        Calculate a molecular fingerprint
        """

        if fptype not in fps:
            raise ValueError('{0} is not a recognised PyDPI Fingerprint type'.format(fptype))

        fpfunc = fingerprint._FingerprintFuncs[fptype]
        fp = fpfunc(self.Mol)

        return Fingerprint(fp)
