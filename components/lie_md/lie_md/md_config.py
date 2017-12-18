# -*- coding: utf-8 -*-

from lie_md.gromacs_topology_amber import correctItp
from os.path import join
from twisted.logger import Logger

import os
import shutil

logger = Logger()


def set_gromacs_input(gromacs_config, workdir, dict_input):
    """
    Create input files for gromacs.
    """
    # Check if all the data is available
    gromacs_config = check_input(gromacs_config, dict_input)

    # residues
    gromacs_config['residues'] = dict_input['residues']

    # correct topology
    gromacs_config = fix_topology_ligand(gromacs_config, workdir)

    return fix_topology_protein(gromacs_config)


def check_input(gromacs_config, dict_input):
    """
    Check if all the data required to run gromacs is present
    """
    file_names = ['protein_pdb', 'protein_top', 'ligand_pdb',
                  'ligand_top']

    for f in file_names:
        path = dict_input.get(f, None)
        if path is not None and os.path.isfile(path):
            gromacs_config[f] = path
        else:
            logger.error("{}: {} not a valid file path".format(f, path))
            raise RuntimeError("the following files are required by the \
            liestudio.gromacs.liemd function: {}".format(file_names))

    # include files
    gromacs_config['include'] = dict_input['include']

    return gromacs_config


def fix_topology_protein(gromacs_config):
    """
    Adjust the topology of the protein
    """
    return gromacs_config


def fix_topology_ligand(gromacs_config, workdir):
    """
    Adjust topology for the ligand.
    """
    return gromacs_config
    # itp_file = join(workdir, 'ligand.itp')
    # results = correctItp(
    #     gromacs_config['ligand_itp'], itp_file, posre=True)

    # # Add charges and topology
    # gromacs_config['charge'] = results['charge']
    # gromacs_config['ligand_itp'] = itp_file

    # return gromacs_config


def copy_data_to_workdir(config, workdir):
    """
    Move Gromacs related files to the Workdir
    """
    # Store protein file if available
    config['protein_pdb'] = store_structure_in_file(
        config['protein_pdb'], workdir, 'protein')

    # Store ligand file if available
    config['ligand_pdb'] = store_structure_in_file(
        config['ligand_pdb'], workdir, 'ligand')

    # Save ligand topology files
    config['ligand_itp'] = store_structure_in_file(
        config['ligand_itp'], workdir, 'input_GMX', ext='itp')

    return config


def store_structure_in_file(mol, workdir, name, ext='pdb'):
    """
    Store a molecule in a file if possible.
    """
    file_name = '{}.{}'.format(name, ext)
    dest = join(workdir, file_name)

    if mol is None:
        raise RuntimeError(
            "There is not {} available".format(name))

    elif os.path.isfile(mol):
        shutil.copy(mol, dest)

    elif os.path.isdir(mol):
        path = join(mol, file_name)
        store_structure_in_file(path, workdir, name, ext)

    else:
        with open(dest, 'w') as inp:
            inp.write(mol)

    return dest
