# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

import os
import json
import jsonschema
import tempfile
import shutil

from autobahn import wamp

from lie_amber.settings import SETTINGS, AMBER_SCHEMA
from lie_amber.ambertools import amber_acpype, amber_reduce
from lie_system import LieApplicationSession, WAMPTaskMetaData

amber_schema = json.load(open(AMBER_SCHEMA))


class AmberWampApi(LieApplicationSession):
    """
    AmberTools WAMP methods.
    """

    require_config = ['system']

    @wamp.register(u'liestudio.amber.acpype')
    def run_amber_acpype(self, structure=None, session=None, from_file=False, **kwargs):

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        # Load ACPYPE configuration and update
        acpype_config = self.package_config.get('amber_acpype').dict()

        # Validate the configuration
        jsonschema.validate(amber_schema, acpype_config)

        # Create workdir and save file
        workdir = os.path.join(kwargs.get('workdir', tempfile.gettempdir()))
        tmpfile = os.path.join(workdir, 'input.mol2')
        if not os.path.isdir(workdir):
            os.mkdir(workdir)

        if from_file and os.path.exists(structure):
            shutil.copy(structure, tmpfile)
        else:
            with open(tmpfile, 'w') as inp:
                inp.write(structure)

        # Run ACPYPE
        output = amber_acpype(tmpfile, workdir=workdir, **acpype_config)
        if not output:
            session['status'] = 'failed'
            output = {}
        else:
            session['status'] = 'completed'

        output['session'] = session
        return output

    @wamp.register(u'liestudio.amber.reduce')
    def run_amber_reduce(self, structure=None, session=None, from_file=False, **kwargs):
        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        # Load ACPYPE configuration and update
        amber_reduce_config = self.package_config.get('amber_reduce').dict()

        # Validate the configuration
        jsonschema.validate(amber_schema, amber_reduce_config)

        # Create workdir and save file
        workdir = os.path.join(kwargs.get('workdir', tempfile.gettempdir()))
        tmpfile = os.path.join(workdir, 'input.mol2')
        if not os.path.isdir(workdir):
            os.mkdir(workdir)

        if from_file and os.path.exists(structure):
            tmpfile = structure
        else:
            with open(tmpfile, 'w') as inp:
                inp.write(structure)

        # Run ACPYPE
        output = amber_reduce(tmpfile, **amber_reduce_config)
        if not output:
            session['status'] = 'failed'
        else:
            session['status'] = 'completed'

        return {'session': session, 'path': output}


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
        return AmberWampApi(config, package_config=SETTINGS)
    else:
        # if no config given, return a description of this WAMPlet ..
        return {'label': 'LIEStudio AmberTools interface WAMPlet',
                'description': 'WAMPlet providing LIEStudio connectivity to the AmberTools software suite'}
