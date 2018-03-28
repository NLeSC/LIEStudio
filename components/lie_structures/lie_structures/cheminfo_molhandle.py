# -*- coding: utf-8 -*-

"""
file: cheminfo_molhandle.py

Cinfony driven cheminformatics molecule read, write and manipulate functions
"""

import os
import logging

from twisted.logger import Logger

from . import toolkits

logging = Logger()


def mol_read(
        mol, mol_format=None, from_file=False, toolkit='pybel', default_mol_name='ligand'):
    """
    Import molecular structure file in cheminformatics toolkit molecular object
    """

    toolkit_driver = toolkits.get(toolkit)
    if not toolkit_driver:
        logging.error('Cheminformatics toolkit {0} not active'.format(toolkit))
        return

    # Get molecular file format from file extension if path
    if not mol_format and from_file:
        mol_format = mol.split('.')[-1] or None

    # Is the file format supported by the toolkit
    if mol_format not in toolkit_driver.informats:
        logging.error('Molecular input file format "{0}" not supported by {1}'.format(mol_format, toolkit))
        return

    try:
        if from_file:
            molobject = toolkit_driver.readfile(mol_format, mol).next()
        else:
            molobject = toolkit_driver.readstring(mol_format, mol)
    except IOError, e:
        logging.error(e)
        return

    # Set the molecular title to something meaningful
    if not getattr(molobject, 'title', None):
        molobject.title = default_mol_name
    if not all([i.isalnum() for i in molobject.title]):
        molobject.title = default_mol_name

    # Register import file format and toolkit in molobject
    molobject.mol_format = mol_format
    molobject.toolkit = toolkit

    return molobject


def mol_write(molobject, mol_format=None, file_path=None):

    toolkit_driver = toolkits.get(molobject.toolkit)
    if not toolkit_driver:
        logging.error('Cheminformatics toolkit {0} not active'.format(molobject.toolkit))
        return

    mol_format = mol_format or getattr(molobject, 'mol_format', None)
    if mol_format not in toolkit_driver.outformats:
        logging.error('Molecular output file format "{0}" not supported by {1}'.format(mol_format, molobject.toolkit))
        return

    output = molobject.write(mol_format, file_path, overwrite=True)
    if file_path and os.path.isfile(file_path):
        return file_path

    return output.strip()


def mol_attributes(molobject):
    """
    Common and toolkit specific molecular attributes
    """

    attributes = {}
    attributes.update(molobject.data)
    opts = (
        'formula', 'molwt', 'title', 'charge', 'dim', 'energy', 'exactmass')
    for attr in opts:
        attributes[attr] = getattr(molobject, attr, None)

    return attributes


def mol_addh(molobject, polaronly=False, correctForPH=False, pH=7.4):

    if molobject.toolkit == 'pybel':
        logging.info(
            'Add hydrogens. Toolkit: {0}, only polar: {1}, correct pH: {2}, pH: {3}'.format(molobject.toolkit, polaronly, correctForPH, pH))
        molobject.OBMol.AddHydrogens(polaronly, correctForPH, pH)
    else:
        molobject.addh()

    return molobject


def mol_removeh(molobject):
    """
    Remove hydrogens from the structure
    """
    logging.info(
        'Remove hydrogen atoms from structure: {0}'.format(molobject.title))
    molobject.removeh()

    return molobject


def mol_make3D(molobject, forcefield='mmff94', localopt=True, steps=50):
    """
    Convert 1D or 2D to a 3D representation.

    In case of the PyBel toolkit, hydrogens are first added.
    Not available for the CDK and Webel toolkits.
    """

    # RDKit has no 'dim' variable, add it
    if molobject.toolkit in ('rdk', 'webel'):
        try:
            molobject.dim = len(molobject.atoms[0].coords)
        except AttributeError:
            molobject.dim = 0

    # If molobject has 3 dimensions, check if coordinates are 3D
    if molobject.dim == 3:
        coord_sum = [0, 0, 0]
        for atom in molobject.atoms:
            coord_sum = [a + abs(b) for a, b in zip(coord_sum, atom.coords)]

        # If truely 3D, the sum of all dimensions should be larger than 0
        if all(dim > 0 for dim in coord_sum):
            logging.info('Molecule {0} already in 3D'.format(molobject.title))
            return molobject

    if molobject.toolkit in ('cdk', 'webel'):
        logging.error(
            'Conversion to 3D coordinate set not supported by {0} toolkit'.format(molobject.toolkit))
        return None

    molobject.make3D(forcefield=forcefield, steps=steps)
    if localopt:
        molobject.localopt(forcefield=forcefield, steps=500)

    return molobject


def mol_rotate(molobject, vector=[0, 0, 0, 0]):
    """
    Rotate molecule coordinate frame by a vector describing x,y,z and angle
    """

    if molobject.toolkit != 'pybel':
        logging.error('Rotation only supported by OpenBabel Pybel object')
        return

    toolkit_driver = toolkits.get(molobject.toolkit)
    x, y, z, angle = vector
    matrix = toolkit_driver.ob.matrix3x3()

    # calculates a rotation matrix around the axes specified,
    # by angle specified
    matrix.RotAboutAxisByAngle(
        toolkit_driver.ob.vector3(x, y, z), angle)
    rotarray = toolkit_driver.ob.doubleArray(9)

    # convert the matrix to an array
    matrix.GetArray(rotarray)

    # rotates the supplied molecule object
    molobject.OBMol.Rotate(rotarray)

    return molobject


def mol_copy(molobject):
    """
    Make a copy of a molobject
    """

    mol_to_string = mol_write(molobject)
    return mol_read(mol_to_string, mol_format=molobject.mol_format)


def mol_combine_rotations(molobject, rotations=[]):
    """
    Takes a pybel molecule and array of rotations to perform on it
    Returns array with rotated pybel molecules
    """

    rotated_mols = [molobject]
    for i in rotations:

        mol = mol_copy(molobject)
        mol = mol_rotate(mol, vector=i)
        rotated_mols.append(mol)
        logging.debug("Rotating x,y,z,angle {0}".format(i))

    # Combine rotated structure into new file
    toolkit_driver = toolkits.get(molobject.toolkit)
    rotated_file = toolkit_driver.Outputfile(
        molobject.mol_format, "multipleSD.mol2")
    for rotated_mol in rotated_mols:
        rotated_file.write(rotated_mol)
    rotated_file.close()

    combined = None
    if os.path.isfile('multipleSD.mol2'):
        with open('multipleSD.mol2', 'r') as cf:
            combined = cf.read()
        os.remove('multipleSD.mol2')

    return combined