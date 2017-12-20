# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

from autobahn.wamp.types import RegisterOptions
from cerise_interface import (
    call_cerise_gromit, create_cerise_config)
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

        # Run the MD and retrieve the energies
        output = call_cerise_gromit(
            gromacs_config, cerise_config, self.db['cerise'])

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
