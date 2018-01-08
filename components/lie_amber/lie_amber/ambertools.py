# -*- coding: utf-8 -*-

import os
import copy
import glob

from .settings import SETTINGS
from subprocess import (PIPE, Popen)
from twisted.logger import Logger

logging = Logger()


def _collect_acpype_output(path):

    outfiles = {}
    compound_name = os.path.basename(path).rstrip('.acpype')
    for outfile in glob.glob('{0}/{1}_*.*'.format(path, compound_name)):
        fname = os.path.basename(outfile).lstrip('{0}_'.format(compound_name))
        varname = '_'.join([n.lower() for n in fname.split('.')])
        outfiles[varname] = outfile

    return outfiles


def set_bool_flags(options):
    return ['--{0}'.format(option) for option, flag
            in options.items() if isinstance(flag, bool) and flag]


def set_keyword_flags(options):
    return ['--{0} {1}'.format(option, flag) for option, flag
            in options.items()
            if flag is not None and not isinstance(flag, bool)]


def amber_acpype(mol, workdir=None, **kwargs):
    """
    Run the ACPYPE program (AnteChamber PYthon Parser interfacE)

    acpype reference:
    - Sousa da Silva AW, Vranken WF. ACPYPE - AnteChamber PYthon
      Parser interfacE. (2012), BMC Res Notes. 2012 Jul 23;5:367.
      doi: 10.1186/1756-0500-5-367.
    """
    # ACPYPE executable
    acepype_exe = 'acpype.py'

    # Check the input file
    if not os.path.exists(mol):
        logging.error('Input file does not exist {0}'.format(mol))

    # Construct CLI arguments
    options = copy.deepcopy(SETTINGS['amber_acpype'])
    options.update(
        {k.lower().strip('-'): v for k, v in kwargs.items()}
    )

    # Process sqm/mopac keywords
    if 'keyword' in options:
        options['keyword'] = '"{0}"'.format(options['keyword'].strip('"'))

    # Process boolean flags
    flags_1 = set_bool_flags(options)

    # Process keyword argument flags
    flags_2 = set_keyword_flags(options)

    flags = flags_1 + flags_2

    not_supported = ['--{0}'.format(n) for n in kwargs
                     if not n.lower() in SETTINGS['amber_acpype']]
    if not_supported:
        logging.warn(
            "Following command line arguments not supported by ACPYPE: {0}".format(
                ','.join(not_supported)))

    workdir_name = os.path.splitext(mol)[0]
    cmd = [acepype_exe, '-i', mol] + flags

    logging.info(
        "ACPYPE command: {0}".format(' '.join(cmd)))

    # Run the command
    os.chdir(workdir)
    p = Popen(' '.join(cmd), stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    cmd_out, cmd_err = p.communicate()
    logging.info("OUTPUT ACPYPE:\n{}".format(cmd_out))
    if cmd_err:
        logging.error("Error ACPYPE:\n{}".format(cmd_err))

    output_path = os.path.join(workdir, '{0}.acpype'.format(workdir_name))
    if os.path.isdir(output_path):
        outfiles = _collect_acpype_output(output_path)
        outfiles['path'] = output_path
        return outfiles
    else:
        logging.error('Acpype failed')


def amber_reduce(mol, output=None, return_output_path=False, exe='reduce', **kwargs):
    """
    Run AmberTools "reduce" program for adding hydrogens to molecular
    structures.

    The `amber_reduce` function supports all of the reduce command line
    options available in reduce version 3.24 shipped with AmberTools 16.
    Options may be turned on or off by default using the module wide
    settings or be set specifically by providing the command line option
    as keyword argument to the function.

    Options that may be added in future versions of reduce will be made
    availabe by adding them to the module wide settings.

    Please consult the reduce documentation in the pdf manual:
    - http://ambermd.org/doc12/Amber16.pdf

    reduce reference:
    - Word, et. al. (1999) Asparagine and Glutamine: Using Hydrogen Atom
      Contacts in the Choice of Side-chain Amide Orientation,
      J. Mol. Biol. 285, 1733-1747.

    :param mol:     file path to input structure in PDB file format
    :type mol:      :py:str
    :param output:  file path to output structure in PDB file format
                    Defaults to the input path with '_h.pdb' added as
                    prefix.
    :type output:   :py:str
    :param return_output_path: return the path to the output PDB file
                    instead of the contents of the file itself.
    :type return_output_path: :py:bool
    :param exe:     name of the 'reduce' executable as available in the
                    amber bin directory defined by the 'amberhome'
                    variable in the module settings (defaults to the
                    AMBER_HOME environmental variable).
    :type exe:      :py:str
    """

    # Define executable
    reduce_exe_path = os.path.join(SETTINGS['amberhome'], 'bin', exe)

    # Check the input file
    if not os.path.exists(mol):
        logging.error('Input file does not exist {0}'.format(mol))

    # Define output file
    if not output:
        output = '{0}_h{1}'.format(*os.path.splitext(mol))

    # Construct CLI arguments
    options = copy.deepcopy(SETTINGS['amber_reduce'])
    options.update({k.lower().strip('-'): v for k, v in kwargs.items()})

    # Process boolean flags
    flags = set_bool_flags(options)

    # Process keyword argument flags
    flags.extend(
        ['-{0}{1}'.format(option, flag) for option, flag in
         options.items() if type(flag) not in (bool, type(None))])

    logging.info("Running Amber 'reduce' with command line arguments: {0}".format(','.join(flags)))
    not_supported = ['-{0}'.format(n) for n in kwargs if not n.lower()
                     in SETTINGS['amber_reduce']]
    if not_supported:
        logging.warn("Following command line arguments not supported by Amber 'reduce': {0}".format(','.join(not_supported)))

    cmd = [reduce_exe_path] + flags
    cmd.extend([mol, '>', output])

    # Run the command
    p = Popen(' '.join(cmd), stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    cmd_out, cmd_err = p.communicate()
    logging.info("OUTPUT AMBER REDUCE:\n{}".format(cmd_out))
    if cmd_err:
        logging.error("Error AMBER REDUCE:\n{}".format(cmd_err))

    # Return output file
    if os.path.exists(output):
        if return_output_path:
            return output
        else:
            with open(output, 'r') as out:
                return out.read()
    else:
        logging.error('Reduce failed, not output file {0}'.format(output))
