'''
Tool to gather ensemble energies and per-residue decomposed energies from
gromacs md files (edr and trr for decomposition)
The program execute gromacs commands from inside

examples of execution:
1. To gather energies from edr : python getEnergies.py -gmxrc /opt/gromacs-4.6.7/bin/GMXRC -ene -o energy.dat

2. to obtained per-residue decompose contributes: python getEnergies.py -gmxrc /opt/gromacs-4.6.7/bin/GMXRC -dec -o energydec.dat -res "416,417,418,419,420,421,422,423"

For decomposition, configuration as in mdpName='md-prod-out.mdp' is used.
Rerun is performed for the trajectory: ext='trr',pref='*?MD*'
template index file is: ext='ndx',pref='*?sol'
gro file for getting aton umber for residue is: ext='gro',pref='*?sol'
top file is: 'top',pref='*?sol'
'''

import argparse
import collections
import fnmatch
import logging
import numpy as np
import os
import re
import sys
from multiprocessing import cpu_count
from panedr import edr_to_df
from subprocess import (PIPE, Popen)

# Container for the files
Files = collections.namedtuple(
    "FILES", ("gro", "ndx", "trr", "top", "mdp", "tpr"))


def main(args):

    # Full energy gathering
    if args.energy and args.decompose:
        msg = 'Make a decision: decomposition (-dec) or ensemble energy gathering (-ene)!'
        log_and_quit(msg)

    if args.energy:
        process_energies(args.dataDir, args.outName)

    # Per-residue energy decomposition
    if args.decompose:
        decompose(args)
    logging.info('SUCCESSFUL COMPLETION OF THE PROGRAM')


def process_energies(dataDir, outName):
    """
    Read and format energies using a edr file contains in
    `dataDir` and write it in `outName`.
    """
    path = findFile(dataDir, ext='edr', pref='*energy*')
    if path is None:
        msg = 'TERMINATED. Program {} not found.'.format(path)
        log_and_quit(msg)
    else:
        frames = get_energy(path)
        labs2print = [
            'Time', 'Potential', 'Kinetic En.', 'Temperature', 'ele', 'vdw',
            'Ligand-Ligenv-ele', 'Ligand-Ligenv-vdw']
        writeOut(frames, outName, labs2print)


def get_energy(path, listRes=['Ligand']):
    """
    Read Energies from a .edr file and
    use the `panedr` library to parse it.

    :params path:  Path to the edr file.
    :returns: Pandas dataframe.
    """
    df = edr_to_df(path)
    # Electrostatic Energy
    df['ele'] = sum_available_columns(
        df, ['Coulomb-14', 'Coulomb (SR)', 'Coulomb (LR)', 'Coul. recip.'])

    # Van der Waals terms
    df['vdw'] = sum_available_columns(
        df, ['LJ-14', 'LJ (SR)', 'LJ (LR)'])

    return extract_ligand_info(df, listRes)


def decompose(args):
    """
    Make a decomposition of the energy into its residue components
    """
    if args.resList is None:
        msg = 'TERMINATED. List of residues not provided.'
        log_and_quit(msg)

    if not availProg('gmx', args.gmxEnv):
        log_and_quit('gmx executable was not found')

    # parse MD mdp
    mdpIn = findFile(args.dataDir, ext='mdp', pref='*')
    mdp_dict = parseMdp(mdpIn)

    # create decomposition mdp, ndx and run rerun
    gro = findFile(args.dataDir, ext='gro', pref='*sol')
    ndx = findFile(args.dataDir, ext='ndx', pref='*-sol')
    trr = findFile(args.dataDir, ext='trr', pref='*MD*')
    top = findFile(args.dataDir, ext='top', pref='*-sol')
    files = Files(gro, ndx, trr, top, mdpIn, None)

    prefix_result = decomp(mdp_dict, args, files)

    energy_analysis(args, prefix_result)


def decomp(
         mdp_dict, args, files, ligGroup='Ligand', output_prefix='decompose'):
    """
    Decompose the energy into its components for different residues.
    """
    new_mdp_file = create_new_mdp_file(mdp_dict, args, ligGroup)
    # create a dictionary with the index of the atoms that belong
    # to a given residue
    dict_residues = create_residue_dict(files.gro)

    # create new ndx file:
    new_ndx_file = create_new_ndx_file(dict_residues, args, files.ndx)

    # Generate new tpr file
    new_tpr_file = create_new_tpr_file(args, files)

    # update files tuple
    new_files = files._replace(
        mdp=new_mdp_file, ndx=new_ndx_file, tpr=new_tpr_file)

    return rerun_md(args, new_files)


def rerun_md(args, files):
    """
    Rerun the molecular dynamics and create decomposition of the energy.
    """
    mdrun = set_gmx_mpi_run(args.gmxEnv)
    cmd = ['-s', files.tpr, '-rerun', files.trr, '-deffnm', 'decompose']
    rs, err = call_subprocess(mdrun + cmd, args.gmxEnv)
    logging.error(err)

    energy_file = os.path.join(args.dataDir, 'decompose.edr')
    if not os.path.exists(energy_file):
        msg = 'Something went wrong in the rerun decomposition analysis'
        log_and_quit(msg)

    return energy_file


def energy_analysis(args, prefix):
    """Analysis of energy decomposition file after rerun"""
    path = findFile(args.dataDir, ext='edr',  prefix=prefix)
    logging.info(
        "Extracting decomposed energies from {} file".format(path))
    df = get_energy(path)

    write_decomposition_ouput(df, args.outName, args.resList)


def create_new_tpr_file(args, files):
    """
    Call gromacs grompp `http://manual.gromacs.org/programs/gmx-grompp.html`.
    """
    outTpr = os.path.join(args.dataDir, 'decompose.tpr')
    cmd = ['gmx', 'grompp', '-f', files.mdp, '-c', files.gro, '-p',
           files.top, '-n', files.ndx, '-o', outTpr]
    rs, err = call_subprocess(cmd, args.gmxEnv)
    logging.error(err)

    if not os.path.exists(outTpr):
        msg = 'Something went wrong in the creation of the tpr file  \
        for decomposition analysis'
        log_and_quit(msg)

    return outTpr


def set_gmx_mpi_run(env):
    """
    Try to run gmx mdrun using MPI see:
    `http://manual.gromacs.org/documentation/5.1/user-guide/mdrun-performance.html`
    """
    mpi_run = env.get('MPI_RUN', None)

    if mpi_run is not None:
        nranks = compute_mpi_ranks()
        gmx = [mpi_run] + nranks + ['gmx']
    else:
        gmx = ['gmx']

    return gmx + ['mdrun']


def compute_mpi_ranks(ranks=''):
    """
    guess a reasonable default for the mpi ranks
    """
    if cpu_count() > 1:
        xs = "-np 4 --map-by ppr:2:socket -v --display-map --display-allocation"
        ranks = xs.split()

    return ranks


def create_new_ndx_file(residues_dict, args, ndx_file):
    """
    Write a new ndx file mapping the residue numbers to their
    correspoding atoms, using a array `residues_map` that contains
    in each row the lower and upper limit of the range of
    the atoms contained in a given residue.
    """
    new = ''
    for key in args.resList:
        new += '[ {} ]\n'.format(key)
        data = np.array2string(
            np.arange(*residues_dict[key]),
            formatter={'int': lambda s: '{:>7d}'.format(s)})[1:-1]
        new += ' {}\n'.format(data)

    new_ndx_file = os.path.join(args.dataDir, 'decompose.ndx')
    with open(ndx_file, 'r') as f_inp, open(new_ndx_file, 'w') as f_out:
        old = f_inp.read()
        f_out.write(old + new)

    return new_ndx_file


def create_new_mdp_file(mdp_dict, args, ligGroup):
    """ Crate a new input mdp file """

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
    str_residues = np.array_str(args.resList)[1:-1]
    energygrps = '{} {}'.format(ligGroup, str_residues)

    newKeys['energygrps'] = energygrps

    new_input = ''
    fmt = "{:15s} = {}\n"
    for mdpKey in newKeys:
        new_input += fmt.format(mdpKey, newKeys[mdpKey])

    for mdpKey in (x for x in listkeys if x in mdp_dict):
        new_input += fmt.format(mdpKey, mdp_dict[mdpKey])

    mdp_file = os.path.join(args.dataDir, "decompose.mdp")
    with open(mdp_file, 'w') as f:
        f.write(new_input)

    return mdp_file


def extract_ligand_info(df, listRes):
    """
    Get the Ligand information.
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
        f.write(frames[columns].to_string(index=False))


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
    hs1 = ['time', 'Potential', 'ele', 'vdw']
    hs2 = ['Ligand-{}-vdw'.format(x) for x in resList]
    hs3 = ['Ligand-rest-vdw']
    hs4 = ['Ligand-{}-ele'.format(x) for x in resList]
    hs5 = ['Ligand-rest-ele']

    labs2print = hs1 + hs2 + hs3 + hs4 + hs5
    writeOut(listFrames, outName, labs2print)


def parseResidues(xs):
    """ return an array of the residues index """
    return np.array(xs.split(','), dtype=np.int32)


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
    """ Check whether a file exists"""
    rs = fnmatch.filter(os.listdir(workdir), "{}.{}".format(pref, ext))
    if rs:
        return os.path.join(workdir, rs[0])

    else:
        logging.error(
            "file not Found with prefix: {} and ext: {}".format(pref, ext))
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


def process_line(line):
    """ Split a Line in key, value pairs """
    key, value = line.partition("=")[::2]
    return key, value.rstrip()


def call_subprocess(cmd, env=None):
    """
    Execute shell command and wait for the results
    """
    try:
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=env)
        rs = p.communicate()
        return rs

    except Exception as e:
        msg1 = "Subprocess fails with error: {}".format(e)
        msg2 = "Command: {}\n".format(cmd)
        log_and_quit(msg1 + msg2)


if __name__ == "__main__":
    logging.basicConfig(level='INFO')
    parser = argparse.ArgumentParser(
        description='Dock sdf file into protein conformation')

    parser.add_argument(
        '-gmxrc', required=False, dest='gmxEnv', type=getGMXEnv,
        help='GMXRC file for environment loading')
    parser.add_argument(
        '-d', '--dir', required=False, dest='dataDir',
        help='directory with MD files to process', default=os.getcwd())
    parser.add_argument(
        '-dec', '--decompose', dest='decompose',
        help='perform residue decomposition analysis', action='store_true')
    parser.add_argument(
        '-ene', '--energy', dest='energy', help='gather total energy',
        action='store_true')
    parser.add_argument(
        '-res', '--residues', required=False, dest='resList',
        help='list of residue for which to decompose interaction energies (e.g.1 "1,2,3")',
        type=parseResidues)
    parser.add_argument(
        '-o', '--output', dest='outName', required=True)

    args = parser.parse_args()

    main(args)
