#! /usr/bin/env python
'''
Tool to gather ensemble energies and per-residue decomposed energies from
gromacs md files (edr and trr for decomposition)
The program execute gromacs commands from inside

examples of execution:
1. To gather energies from edr:
 python getEnergies.py energy -o energy.dat

2. to obtained per-residue decompose contributes:
 python getEnergies.py decompose -gmxrc /opt/gromacs-4.6.7/bin/GMXRC -o energydec.dat -res "416,417,418,419,420,421,422,423"

For decomposition, configuration as in mdpName='md-prod-out.mdp' is used.
Rerun is performed for the trajectory: ext='trr',pref='*?MD*'
template index file is: ext='ndx',pref='*?sol'
top file is: 'top',pref='*?sol'
gro file for getting aton umber for residue is: ext='gro',pref='*?sol'
'''

import argparse
import collections
import fnmatch
import glob
import logging
import numpy as np
import pandas
import os
import re
import shutil
import subprocess
import sys
from multiprocessing import cpu_count
from panedr import edr_to_df
from subprocess import (PIPE, Popen)

# Container for the files
Files = collections.namedtuple(
    "FILES", ("gro", "ndx", "trr", "top", "mdp", "tpr"))


def main(args):
    if args.mode == 'energy':
        process_energies(args, args.outName)

    # Per-residue energy decomposition
    if args.mode == 'decompose':
        decompose(args)
    logging.info('SUCCESSFUL COMPLETION OF THE PROGRAM')


def process_energies(args, outName):
    """
    Read and format energies using a edr file contains in
    `dataDir` and write it in `outName`.

    :params dataDir: Directory where the job is execute.
    :params outName: Name of the output file.
    """
    path_edr = get_edr_file(args)
    frames = get_energy(path_edr)
    frames.rename(index=str, columns={'Kinetic En.': 'Kinetic_Energy'}, inplace=True)
    labs2print = [
        'Time', 'Potential', 'Kinetic_Energy', 'Temperature', 'ele',
        'vdw', 'Ligand-Ligenv-ele', 'Ligand-Ligenv-vdw']
    writeOut(frames, outName, labs2print)


def get_energy(paths, listRes=['Ligand']):
    """
    Read Energies from .edr files and
    use the `panedr` library to parse them.

    :params paths:  Path to the edr files.
    :returns: Pandas dataframe.
    """
    if not isinstance(paths, list):
        df = edr_to_df(paths)
    else:
        # concatenate the data frames and reduce with the mean function
        rs = [edr_to_df(p) for p in paths]
        df = pandas.concat(rs)
        df.groupby(df.index).mean()

    # Reindex dataframe using sequential integers
    df.reset_index(inplace=True)

    # Electrostatic Energy
    df['ele'] = sum_available_columns(
        df, ['Coulomb-14', 'Coulomb (SR)', 'Coulomb (LR)', 'Coul. recip.'])

    # Van der Waals terms
    df['vdw'] = sum_available_columns(
        df, ['LJ-14', 'LJ (SR)', 'LJ (LR)'])

    return extract_ligand_info(df, listRes)


def decompose(args):
    """
    Make a decomposition of the energy into some if its residue components.
    """
    if args.resList is None:
        msg = 'TERMINATED. List of residues not provided.'
        log_and_quit(msg)

    gmx = search_commands(['gmx', 'gmx_mpi'], args.gmxEnv)
    if gmx is None:
        log_and_quit('gmx executable was not found')

    # parse MD mdp
    args_dict = vars(args)
    mdpIn = search_file_in_args(args_dict, ext='mdp', pref='md-prod-out')
    mdp_dict = parseMdp(mdpIn)

    # search for gromacs output files
    gro = search_file_in_args(args_dict, ext='gro', pref='*sol')
    ndx = search_file_in_args(args_dict, ext='ndx', pref='*-sol')
    trr = search_file_in_args(args_dict, ext='trr', pref='*MD.part*')
    top = search_file_in_args(args_dict, ext='top', pref='*-sol')
    files = Files(gro, ndx, trr, top, mdpIn, None)

    # rerun the molecular dynamics
    energy_files = decomp(mdp_dict, args, files, gmx)

    energy_analysis(args, energy_files)


def decomp(
         mdp_dict, args, files, gmx, ligGroup='Ligand', output_prefix='decompose'):
    """
    Decompose the energy into its components for different residues.
    """
    # create a dictionary with the index of the atoms that belong
    # to a given residue
    dict_residues = create_residue_dict(files.gro)

    def compute_decomposition(res, folder):
        workdir = create_workdir(args.dataDir, folder)

        copy_include_files(args.dataDir, workdir)

        # Generate new mdp file including residues
        new_mdp_file = create_new_mdp_file(mdp_dict, res, workdir, ligGroup)

        # create new ndx file
        new_ndx_file = create_new_ndx_file(dict_residues, res, workdir, files.ndx)

        # Generate new tpr file
        files_tpr = Files(files.gro, new_ndx_file, files.trr, files.top, new_mdp_file, None)
        new_tpr_file = create_new_tpr_file(files_tpr, workdir, gmx, args.gmxEnv)

        return rerun_md(new_tpr_file, files.trr, workdir, gmx, args.gmxEnv)

    # it is only possible to compute with gromacs 64 energy groups of a time
    residues = chunksOf(args.resList, 62)

    return [compute_decomposition(res, folder='chunk_{}'.format(i))
            for i, res in enumerate(residues)]


def rerun_md(tpr_file, trr_file, workdir, gmx, gmx_env):
    """
    Rerun the molecular dynamics and create decomposition of the energy.
    """
    mdrun = set_gmx_mpi_run(gmx)
    cmd = ['-s', tpr_file, '-rerun', trr_file, '-deffnm', 'decompose']
    rs, err = call_subprocess(mdrun + cmd, gmx_env, workdir)
    logging.error(err)
    logging.info(rs)

    energy_file = os.path.join(workdir, 'decompose.edr')
    if not os.path.exists(energy_file):
        msg = 'Something went wrong in the rerun decomposition analysis'
        log_and_quit(msg)

    return energy_file


def energy_analysis(args, energy_files):
    """Analysis of energy decomposition files after rerun"""
    df = get_energy(energy_files)

    write_decomposition_ouput(df, args.outName, args.resList)


def create_new_tpr_file(files, workdir, gmx, gmx_env):
    """
    Call gromacs grompp `http://manual.gromacs.org/programs/gmx-grompp.html`.
    """
    outTpr = os.path.join(workdir, 'decompose.tpr')
    cmd = [gmx, 'grompp', '-f', files.mdp, '-c', files.gro, '-p',
           files.top, '-n', files.ndx, '-o', outTpr, '-maxwarn', '2']
    rs, err = call_subprocess(cmd, gmx_env, cwd=workdir)
    logging.error(err)

    if not os.path.exists(outTpr):
        msg = 'Something went wrong in the creation of the tpr file  \
        for decomposition analysis'
        log_and_quit(msg)

    return outTpr


def set_gmx_mpi_run(gmx):
    """
    Try to run gmx mdrun using MPI see:
    `http://manual.gromacs.org/documentation/5.1/user-guide/mdrun-performance.html`
    """
    nranks = compute_mpi_ranks()
    gmx_bin = ['mpirun'] + nranks + [gmx]

    return gmx_bin + ['mdrun']


def compute_mpi_ranks(ranks=''):
    """
    guess a reasonable default for the mpi ranks.
    """
    cpus = cpu_count()
    if cpus > 4:
        s = "-np 4 --map-by ppr:2:socket -v --display-map --display-allocation"
        ranks = s.split()

    return ranks


def create_new_ndx_file(residues_dict, residues, workdir, ndx_file):
    """
    Write a new ndx file mapping the residue numbers to their
    correspoding atoms, using a array `residues_dict` that contains
    in each row the lower and upper limit of the range of
    the atoms contained in a given residue.
    """
    new = ''
    for key in residues:
        new += '[ {} ]\n'.format(key)
        data = np.array2string(
            np.arange(*residues_dict[key]),
            formatter={'int': lambda s: '{:>7d}'.format(s)})[1:-1]
        new += ' {}\n'.format(data)

    new_ndx_file = os.path.join(workdir, 'decompose.ndx')
    with open(ndx_file, 'r') as f_inp, open(new_ndx_file, 'w') as f_out:
        old = f_inp.read()
        f_out.write(old + new)

    return new_ndx_file


def create_new_mdp_file(mdp_dict, residues, workdir, ligGroup):
    """
    Create a new input mdp file using the previous `mdp_dict` data.
    """

    listkeys = [
        'include', 'define', 'cutoff-scheme', 'ns-type', 'pbc',
        'periodic-molecules', 'rlist', 'rlistlong', 'nstcalclr',
        'coulombtype', 'coulomb-modifier', 'rcoulomb-switch', 'rcoulomb',
        'epsilon-r', 'epsilon-rf', 'vdw-type', 'vdw-modifier', 'rvdw-switch',
        'rvdw', 'DispCorr', 'table-extension', 'energygrp-table',
        'fourierspacing', 'fourier-nx', 'fourier-ny', 'fourier-nz',
        'pme-order', 'ewald-rtol', 'ewald-geometry', 'epsilon-surface',
        'optimize-fft', 'implicit-solvent', 'QMMM', 'constraints',
        'constraint-algorithm', 'continuation', 'Shake-SOR', 'shake-tol',
        'lincsorder', 'lincs-iter', 'lincs-warnangle', 'morse',
        'nwall', 'wall-type', 'wall-r-linpot', 'wall-atomtype', 'wall-density',
        'wall-ewald-zfac', 'pull', 'rotation', 'disre', 'orire',
        'free-energy', 'simulated-tempering']

    newKeys = {
        'nstxout': '0', 'nstvout': '0', 'nstfout': '0', 'nstlog': '0',
        'nstcalcenergy': '1', 'nstenergy': '1', 'nstxtcout': '0',
        'xtc-precision': '0', 'xtc-grps': '', 'nstlist': '1'}

    # the [1:-1] removes the [ ] from the beginning and the end
    str_residues = np.array_str(residues, max_line_width=1000)[1:-1]
    energygrps = '{} {}'.format(ligGroup, str_residues)

    newKeys['energygrps'] = energygrps

    new_input = ''
    fmt = "{:15s} = {}\n"
    for mdpKey in newKeys:
        new_input += fmt.format(mdpKey, newKeys[mdpKey])

    for mdpKey in (x for x in listkeys if x in mdp_dict):
        new_input += fmt.format(mdpKey, mdp_dict[mdpKey])

    mdp_file = os.path.join(workdir, "decompose.mdp")
    with open(mdp_file, 'w') as f:
        f.write(new_input)

    return mdp_file


def extract_ligand_info(df, listRes):
    """
    Get the Ligand information from a pandas dataframe `df`.
    """
    for res in listRes:
        names = get_residue_from_columns(res, df.columns)
        df = compute_terms_per_residue(df, names)

    return df


def get_residue_from_columns(name, columns):
    """
    Extract the ligand terms from the column names.

    :param name: Name of the residue
    :param columns: name of the columns in the dataframe
    :return: dictionary containing the residue's names as
           keys and electrostatic and vdw names as values.
    """
    names = collections.defaultdict(list)
    for c in filter(lambda x: name in x, columns):
        v, k = c.split(':')
        names[k].append(v)

    # Sort the list
    for xs in names.values():
        xs.sort()

    return names


def compute_terms_per_residue(df, names):
    """
    Split the names in the electrostatic and van der Waals terms
    and compute the electronic and VDW terms for each one of
    the residue terms specified in the `names` dictionary.

    :param df: Pandas dataframe
    :param names: dictionary of the names use in the dataframe.
    :return: updated dataframe
    """
    for key, vals in names.items():
        sufix_elec = vals[:2]
        sufix_vdw = vals[2:]
        names_elec = ['{}:{}'.format(x, key) for x in sufix_elec]
        names_vdw = ['{}:{}'.format(x, key) for x in sufix_vdw]
        res_elec = '{}-ele'.format(key)
        res_vdw = '{}-vdw'.format(key)

        df[res_elec] = df[names_elec].sum(axis=1)
        df[res_vdw] = df[names_vdw].sum(axis=1)

    return df


def sum_available_columns(df, labels):
    """
    Sum columns if they are in the dataframe
    """
    cols = [x for x in labels if x in df.columns]
    return df[cols].sum(axis=1)


def writeOut(frames, output_file, columns):
    """
    write columns as a table
    """
    with open(output_file, 'w') as f:
        s = '# FRAME ' + frames[columns].to_string()
        f.write(s)


def create_residue_dict(gro_file):
    """
    Read residues from the `gro_file` and create
    an array that map the the residues listed in `res_array`
    with their correspoding atoms.
    """
    def match_int(x):
        return re.match(r"([0-9]+)", x).groups()[0]

    arr = np.loadtxt(gro_file, dtype=np.bytes_, skiprows=2, usecols=0)
    arr = np.array(arr, dtype=np.str)
    xs = np.array(
        [match_int(x) for x in arr if 'SOL' not in x and '.' not in x],
        dtype=np.int32)

    # create range of the atoms for each residue
    unique, counts = np.unique(xs, return_counts=True)
    upper_limits = np.cumsum(counts) + 1
    lower_limits = np.insert(upper_limits[:-1], 0, 1)
    ranges = np.stack((lower_limits, upper_limits), axis=1)

    return dict(zip(unique, ranges))


def write_decomposition_ouput(listFrames, outName, resList):
    """ Write results for decomposition """
    hs1 = ['Time', 'Potential', 'ele', 'vdw']
    hs2 = ['Ligand-{}-vdw'.format(x) for x in resList]
    hs3 = ['Ligand-rest-vdw']
    hs4 = ['Ligand-{}-ele'.format(x) for x in resList]
    hs5 = ['Ligand-rest-ele']

    labs2print = hs1 + hs2 + hs3 + hs4 + hs5
    writeOut(listFrames, outName, labs2print)


def parseResidues(xs):
    """ return an array of the residues index """
    residues = np.array(xs.split(','), dtype=np.int32)

    return residues


def parseMdp(mdpIn):
    """ Read the mdp input file"""
    with open(mdpIn, 'r') as inFile:
        xss = inFile.readlines()

    rs = filter(lambda line: not line.startswith(';') and '=' in line, xss)

    return dict([check_lenght(x.split()[::2]) for x in rs])


def check_lenght(xs):
    """ transform list to tuples fixing the lenght """
    if len(xs) == 1:
        return xs[0], ''
    else:
        return tuple(xs)


def log_and_quit(msg):
    """
    Log a message and quit the program
    """
    logging.error(msg)
    sys.exit(-1)


def availProg(prog, myEnv):
    """ Check if a program is available """
    cmds = (os.path.join(path, prog)
            for path in myEnv["PATH"].split(os.pathsep))

    return any(os.path.isfile(cmd) and os.access(cmd, os.X_OK)
               for cmd in cmds)


def findFile(workdir, ext=None, pref=''):
    """
    Check whether a file starting with `pref` and ending with `ext` exists.
    """
    rs = fnmatch.filter(os.listdir(workdir), "{}.{}".format(pref, ext))
    if rs:
        return os.path.join(workdir, rs[0])

    else:
        logging.error(
            """
file not Found with prefix: {} and ext: {}
in dir: {}""".format(pref, ext, workdir))
        return None


def getGMXEnv(gmxrc):
    """ Use Gromacs environment """
    if gmxrc is None:
        return os.environ
    else:
        command = ['bash', '-c', 'source {} && env'.format(gmxrc)]
        rs = call_subprocess(command)[0]
        lines = rs.decode().splitlines()

        return dict(map(process_line, lines))


def get_edr_file(args):
    """
    """
    if args.edr is None:
        return findFile(args.dataDir, ext='edr', pref='*-MD.part*')
    else:
        return args.edr


def chunksOf(xs, n):
    """Yield successive n-sized chunks from xs"""
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def create_workdir(path, folder):
    """create a workdir if it does not exist """
    workdir = os.path.join(path, folder)
    if not os.path.isdir(workdir):
        os.mkdir(workdir)

    return workdir


def copy_include_files(path, workdir):
    """ Copy all the include topology files in the workdir"""
    for p in glob.glob("{}/*itp".format(path)):
        shutil.copy(p, workdir)


def process_line(line):
    """ Split a Line in key, value pairs """
    key, value = line.partition("=")[::2]
    return key, value.rstrip()


def search_file_in_args(args_dict, ext=None, pref=None):
    """
    Search if a file was passed as an argument otherwise look for it
    on the workdir.

    :params args: command line arguments
    :returns: path to file
    """
    file_path = args_dict.get(ext)
    if file_path is not None:
        return file_path
    else:
        return findFile(args_dict['dataDir'], ext=ext, pref=pref)


def call_subprocess(cmd, env=None, cwd=None):
    """
    Execute shell command `cmd`, using the environment `env`
    and wait for the results.
    """
    try:
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=env, cwd=cwd)
        rs = p.communicate()
        return rs

    except Exception as e:
        msg1 = "Subprocess fails with error: {}".format(e)
        msg2 = "Command: {}\n".format(cmd)
        log_and_quit(msg1 + msg2)


def check_command(cmd, env):
    try:
        with open(os.devnull, 'w') as f:
            r = subprocess.check_output(cmd, stderr=f, env=env)
            return r.split()[0]
    except subprocess.CalledProcessError:
        return None


def search_commands(cmds, env=None):
    xs = [check_command(["which", c], env) for c in cmds]
    rs = [x for x in xs if x is not None]
    if rs:
        return rs[0]
    else:
        return None


if __name__ == "__main__":
    logging.basicConfig(level='INFO')
    parser = argparse.ArgumentParser(
        description='Decompose the energy into its different components per residue')

    # Create separate parsers for the energy and decomposition
    subparsers = parser.add_subparsers(
        help='Parser for both energy and its decomposition',
        dest='mode')
    parser_energy = subparsers.add_parser(
        'energy', help='gather total energy')
    parser_dec = subparsers.add_parser(
        'decompose', help='perform residue decomposition analysis')

    # Arguments for total energy
    parser_energy.add_argument(
        '-edr', required=False,
        help='Gromacs energy output in edr format')

    # Arguments for energy decomposition
    parser_dec.add_argument(
        '-gmxrc', required=False, dest='gmxEnv', type=getGMXEnv,
        help='GMXRC file for environment loading')

    parser_dec.add_argument(
        '-res', '--residues', required=True, dest='resList',
        help='list of residue for which to decompose interaction energies (e.g.1 "1,2,3")',
        type=parseResidues)

    # Gromacs output files
    parser_dec.add_argument(
        '-gro', required=False, help='path to*.gro file')
    parser_dec.add_argument(
        '-ndx', required=False, help='path to*.ndx file')
    parser_dec.add_argument(
        '-trr', required=False, help='path to*.trr file')
    parser_dec.add_argument(
        '-top', required=False, help='path to*.top file')
    parser_dec.add_argument(
        '-mdp', required=False, help='path to*.mdp file')

    # Arguments for both parsers
    for p in [parser_energy, parser_dec]:
        p.add_argument(
            '-d', '--dir', required=False, dest='dataDir', type=os.path.abspath,
            help='directory with MD files to process', default=os.getcwd())
        p.add_argument(
            '-o', '--output', dest='outName', default='energy.out')

    args = parser.parse_args()
    main(args)
