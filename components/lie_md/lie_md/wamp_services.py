# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

<<<<<<< HEAD
from autobahn.wamp.types import RegisterOptions
from cerise_interface import (
    call_cerise_gromit, create_cerise_config)
=======
import os
import tempfile
import shutil
import json

from autobahn import wamp

>>>>>>> master
from lie_system import LieApplicationSession, WAMPTaskMetaData
from lie_md.settings import SETTINGS
from md_config import set_gromacs_input
from pymongo import MongoClient
from twisted.internet.defer import inlineCallbacks
from twisted.logger import Logger
import os

logger = Logger()


class MDWampApi(LieApplicationSession):
    """
    Molecular dynamics WAMP methods.
    """
    db = None
    require_config = ['system']

    def __init__(self, config, package_config=None, **kwargs):

        super(MDWampApi, self).__init__(config, package_config, **kwargs)

        if self.db is None:
            host = os.getenv('MONGO_HOST', 'localhost')
            self.db = MongoClient(
                host=host, port=27017, serverSelectionTimeoutMS=1)['mdstudio']

    @inlineCallbacks
    def onRun(self, details):
        """
        Register WAMP MD simulation with support for `roundrobin` load
        balancing.
        """
        # Register WAMP methods
        yield self.register(
            self.run_gromacs_liemd, u'liestudio.gromacs.liemd',
            options=RegisterOptions(invoke=u'roundrobin'))

    def run_gromacs_liemd(
<<<<<<< HEAD
            self, session={}, path_cerise_config=None, cwl_workflow=None,
            protein_pdb=None, protein_top=None, ligand_pdb=None,
            ligand_top=None, include=[], residues=None, **kwargs):
        """
        Call gromit using the Cerise-client infrastructure:
        http://cerise-client.readthedocs.io/en/master/index.html

        This function expects the following keywords files to call gromit:
            * protein_pdb
            * protein_top
            * ligand_pdb
            * ligand_top

        Further include files (e.g. *itp files) can be included as a list:
        include=[atom_types.itp, another_itp.itp]

        To perform the energy decomposition a list of the numerical residues
        identifiers is expected, for example:
        residues=[1, 5, 7, 8]
        """
        logger.info("starting liemd task_id:{}".format(session['task_id']))
        workdir = kwargs.get('workdir', os.getcwd())
=======
            self, session=None, protein_file=None, ligand_file=None,
            topology_file=None, **kwargs):
>>>>>>> master

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()
        session['workdir'] = workdir

        # Load GROMACS configuration and update it
        input_dict = {
            'protein_pdb': protein_pdb, 'protein_top': protein_top,
            'ligand_pdb': ligand_pdb, 'ligand_top': ligand_top,
            'include': include, 'residues': residues}
        gromacs_config = set_gromacs_input(
            self.package_config.dict(), workdir, input_dict)

        # Cerise Configuration
        cerise_config = create_cerise_config(
            path_cerise_config, session, cwl_workflow)

<<<<<<< HEAD
        # Run the MD and retrieve the energies
        output = call_cerise_gromit(
            gromacs_config, cerise_config, self.db['cerise'])
=======
        # Load GROMACS configuration and update
        gromacs_config = self.package_config.dict()

        # Create workdir and save file
        workdir = os.path.join(kwargs.get('workdir', tempfile.gettempdir()))
        if not os.path.isdir(workdir):
            os.mkdir(workdir)
        os.chdir(workdir)

        # Store protein file if available
        if protein_file:
            protdsc = os.path.join(workdir, 'protein.pdb')
            try:
                if os.path.isfile(protein_file):
                    shutil.copy(protein_file, protdsc)
            except:
                with open(protdsc, 'w') as inp:
                    inp.write(protein_file)

        # Store ligand file if available
        if ligand_file:
            ligdsc = os.path.join(workdir, 'ligand.pdb')
            try:
                if os.path.isfile(ligand_file):
                    shutil.copy(ligand_file, ligdsc)
            except:
                with open(ligdsc, 'w') as inp:
                    inp.write(ligand_file)

        # Save ligand topology files
        if topology_file:
            topdsc = os.path.join(workdir, 'ligtop.itp')
            try:
                if os.path.isfile(topology_file):
                    shutil.copy(topology_file, topdsc)
            except:        
                with open(topdsc, 'w') as inp:
                    inp.write(topology_file)

        # Copy script files to the working directory
        for script in ('getEnergies.py', 'gmx45md.sh'):
            src = os.path.join(__rootpath__, 'scripts/{0}'.format(script))
            dst = os.path.join(workdir, script)
            shutil.copy(src, dst)

        # Fix topology ligand
        itpOut = 'ligand.itp'
        #results = correctItp(topdsc, itpOut, posre=True)
        results = {'charge': 0, 'itp': itpOut}

        # Prepaire simulation
        gromacs_config['charge'] = results['charge']
        gmxRun = gromit_cmd(gromacs_config)

        if protein_file:
            gmxRun += '-f {0} '.format(os.path.basename(protdsc))

        if ligand_file:
            gmxRun += '-l {0},{1} '.format(
                os.path.basename(ligdsc), os.path.basename(results['itp']))

        # Prepaire post analysis (energy extraction)
        GMXRC = 'mock_path_to_gmxrc'
        eneRun = 'python getEnergies.py -gmxrc {0} -ene -o ligand.ene'.format(GMXRC)

        # write executable
        with open('run_md.sh', 'w') as outFile:
            outFile.write("{0}\n".format(gmxRun))
            outFile.write("{0}\n".format(eneRun))
>>>>>>> master

        session['status'] = 'completed'

        return {'session': session, 'output': output}


def make(config):
    """
    Component factory

    This component factory creates instances of the application component
    to run.

    The function will get called either during development using an
    ApplicationRunner, or as a plugin hosted in a WAMPlet container such as
    a Crossbar.io worker.
    The LieApplicationSession class is initiated with an instance of the
    ComponentConfig class by default but any class specific keyword arguments
    can be consument as well to populate the class session_config and
    package_config dictionaries.

    :param config: Autobahn ComponentConfig object
    """

    if config:
        return MDWampApi(config, package_config=SETTINGS)
    else:
        # if no config given, return a description of this WAMPlet ..
        return {'label': 'LIEStudio Molecular Dynamics WAMPlet',
                'description': 'WAMPlet proving LIEStudio molecular dynamics endpoints'}
