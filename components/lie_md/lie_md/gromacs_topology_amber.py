# -*- coding: utf-8 -*-

"""
This file contains the functions for creation of topologies in amber format.
createTopology function should receive an input file
 (already processed  e.g. protonated)
and return a tuple containing itp and pdb of the ligand.
"""
import fnmatch
import numpy as np
import os
from lie_md.parsers import (itp_parser, parser_atoms_mol2, parse_file)
from twisted.logger import Logger

logger = Logger()

formats_dict = {
    "defaults":
    "{:>16s}{:>16s}{:>16s}{:>8s}{:>8s}\n",
    "atomtypes":
    "{:>3s}{:>9s}{:>17s}{:>9s}{:>4s}{:>16s}{:>14s}\n",
    "moleculetype": "{:>5s}{:>4s}\n",
    "atoms":
    "{:>6s}{:>5s}{:>6s}{:>6s}{:>6s}{:>5s}{:>13s}{:>13s}\n",
    "pairs": "{:>6s}{:>7s}{:>7s}\n",
    "bonds": "{:>6s}{:>7s}{:>4s}{:>14s}{:>14s}\n",
    "angles":
    "{:>6s}{:>7s}{:>7s}{:>6s}{:>14s}{:>14s}\n",
    "dihedrals":
    "{:>6s}{:>7s}{:>7s}{:>7s}{:>7s}{:>11s}{:>11s}{:>11s}{:>11s}{:>11s}{:>11s}\n",
    "dihedrals_2":
    "{:>6s}{:>7s}{:>7s}{:>7s}{:>7s}{:>9s}{:>10s}{:>4s}\n",
    "exclusions": "{:>5s}{:>5s}\n"}


def correctItp(itp_file, new_itp_file, posre=True):
    '''Correct hydrogen and heavy atom masses in the .itp file
       makes position restraint file for the ligand'''
    if posre:
        posre_filename = "{}-posre.itp".format(
            os.path.splitext(new_itp_file)[0])
    else:
        posre_filename = None

    # read itp
    itp_dict, ordered_keys = read_include_topology(itp_file)

    # apply heavy hydrogens(HH)
    itp_dict = adjust_heavyH(itp_dict)

    # write corrected itp (with HH and no atomtype section
    write_itp(itp_dict, ordered_keys, new_itp_file, posre=posre_filename)

    # create positional restraints file
    if posre:
        write_posre(itp_dict, posre_filename)
    # get charge ligand
    charge = sum(float(atom[6]) for atom in itp_dict['atoms'])

    return {'itp_filename': new_itp_file,
            'posre_filename': posre_filename,
            'attypes': itp_dict['atomtypes'],
            'charge': int(charge)}


def fix_atom_types_file(include_files, atomtypes_ligand, workdir):
    """
    added the missing atomtypes into the attypes.itp file.
    """
    attypes_file = fnmatch.filter(include_files, "*typ*.itp")[0]

    # get a dictionary of atomtypes sections together with its sorted keys
    itp_dict, keys = read_include_topology(attypes_file)

    # fix the atom types using the ligand topology
    itp_dict['atomtypes'] = fix_atom_types(itp_dict['atomtypes'], atomtypes_ligand)

    # rewrite the atom file
    write_itp(
        itp_dict, keys, attypes_file, posre=None, excludeList=[])


def fix_atom_types(atomtypes, ligand_atomtypes):
    """
    Add the atom types of the ligand `ligand_atomtypes` that are not already
    present at `atomtypes`.
    """
    ligand_atomtypes = ligand_atomtypes.reshape(ligand_atomtypes.size // 7, 7)
    atomtypes = atomtypes.reshape(atomtypes.size // 7, 7)
    labels = atomtypes[:, 0]
    new_types = [atom for atom in ligand_atomtypes if atom[0] not in labels]

    if new_types:
        return np.vstack((atomtypes, new_types))
    else:
        return atomtypes


def read_include_topology(itp_file):
    """
    Read an include topology file and returns a dictionary
    based on the sections.

    :param itp_file: path to the itp file
    :returns: dict
    """
    rs = parse_file(itp_parser, itp_file)

    # tranform the result into a dict
    vals = rs[0][1::2]
    unique_keys = create_unique_keys(rs[0][0::2])
    d = {k: np.array(v) for k, v in zip(unique_keys, vals)}

    return d, unique_keys


def create_unique_keys(xs):
    """
    List of unique block names
    """
    ys = []
    for key in xs:
        ys.append(check_name(key, ys))

    return ys


def check_name(key, ys):
    """Rename a key if already present in the list"""
    if key in ys:
        key = '{}_2'.format(key)
    return key


def adjust_heavyH(itp_dict):
    """
    Adjust the weights of hydrogens, and their heavy atom partner
    """
    # Indices of the hydrogens and their heavy companions
    hs, ps = compute_index_hs_and_partners(itp_dict)

    # Count the number of hydrogens attached to the heavy atoms
    heavy, coordination = np.unique(ps, return_counts=True)

    # Update the weights
    new_atoms = adjust_atom_weight(
        itp_dict['atoms'], hs, heavy, coordination)
    itp_dict['atoms'] = new_atoms

    return itp_dict


def adjust_atom_weight(atoms, hs, heavy, coordination):
    """
    Weight the masses of the `atoms` specificied  in `indices`
    using the `weights`.
    """
    mass_hydrogen = float(atoms[hs[0], 7])
    masses_hs = 4 * np.array(atoms[hs, 7], dtype=np.float)
    masses_heavy = np.array(atoms[heavy, 7], dtype=np.float)
    new_heavy_mass = masses_heavy - 3 * mass_hydrogen * coordination

    # Array to string
    fmt_hs = ['{:.4f}'.format(x) for x in masses_hs]
    fmt_heavy = ['{:.4f}'.format(x) for x in new_heavy_mass]

    # Update weights
    atoms[hs, 7] = fmt_hs
    atoms[heavy, 7] = fmt_heavy

    return atoms


def compute_index_hs_and_partners(itp_dict):
    """
    Extract the indices of the hydrogens and their heavy partners
    Assuming the the hydrogens are always listed after the heavy
    partner.
    """
    atoms = itp_dict['atoms']
    bonds = itp_dict['bonds']

    # Extract the bond indices
    bs = np.array(bonds[:, :2], dtype=np.int) - 1

    # Hydrogen indices
    symbols = atoms[bs[:, 1], 1]
    idxs = np.where([x.startswith(('h', 'H')) for x in symbols])
    hs = bs[idxs, 1]

    # Heavy partners
    ps = bs[idxs, 0]

    return hs.flatten(), ps.flatten()


def write_itp(
        itp_dict, keys, itp_filename, posre=None, excludeList=['atomtypes']):
    """
    write new itp. atomtype block is removed
    """
    with open(itp_filename, "w") as outFile:
        for block_name in keys:
            if block_name not in excludeList:
                outFile.write("[ {} ]\n".format(check_block_name(block_name)))
                for item in itp_dict[block_name]:
                    outFile.write(formats_dict[block_name].format(*item))
        outFile.write("\n")
        if posre is not None:
            basename = os.path.basename(posre)
            outFile.write(
                '#ifdef POSRES\n#include "%s"\n#endif\n' % basename)


def check_block_name(block_name):
    """
    Check whether a block_name has been rename
    """
    if block_name.endswith('_2'):
        block_name = block_name[:-2]

    return block_name


def write_posre(itp_dict, output_itp):
    """
    Write position restraint itp file.
    """
    header = """
#ifndef 3POSCOS
  #define 2POSCOS 5000
#endif

#ifndef 5POSCOS
  #define 5POSCOS 0
#endif

[ position_restraints ]
"""
    with open(output_itp, "w") as f:
        f.write(header)
        for atom in itp_dict['atoms']:
            if atom[1].lower().startswith("h"):
                f.write(
                    "{:4}    1  5POSCOS 5POSCOS 5POSCOS\n".format(atom[0]))
            else:
                f.write(
                    "{:4}    1  2POSCOS 2POSCOS 2POSCOS\n".format(atom[0]))


def reorderhem(
        file_input, file_output='reordered.pdb',
        path_to_hem_template=None,
        listchange=None, diffres=0):
    """
    reorder the atom names for heme according to:
    J Comput Chem. 2012 Jan 15;33(2):119-33

    patch non standard water residue names and other pdb feature
    for amber topology creation
    """
    # Read HEME file specification
    new_order = read_hem_template(path_to_hem_template)

    with open(file_output, 'w') as f_out, open(file_input, 'r') as f_inp:
        pdb_lines = f_inp.readlines()
        f_out.write(create_new_pdb(pdb_lines, new_order))


def read_hem_template(path_to_hem_template):
    """
    Retrieve all the atoms in the @<TRIPOS>ATOM section.
    """
    rs = parse_file(parser_atoms_mol2, path_to_hem_template)
    return np.array(rs[0])


def create_new_pdb(pdb_lines, new_order):
    """
    Write the new order PDB file
    """
    pass
