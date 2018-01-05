# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

import os
import json
import jsonschema

from autobahn import wamp

from lie_system import WAMPTaskMetaData
from lie_structures.settings import STRUCTURES_SCHEMA
from lie_structures.cheminfo_molhandle import (
     mol_addh, mol_attributes, mol_make3D, mol_read, mol_removeh, mol_write, mol_combine_rotations)

STRUCTURES_SCHEMA = json.load(open(STRUCTURES_SCHEMA))


class CheminfoMolhandleWampApi(object):
    """
    Cheminformatics molecule handling WAMP API
    """

    @wamp.register(u'liestudio.structure.convert')
    def convert_structures(self, session=None, **kwargs):
        """
        Convert input file format to a different format
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session or {})

        # Load configuration and update
        config = self.package_config.lie_structures.dict()
        config.update(kwargs)

        # Validate against JSON schema
        jsonschema.validate(config, STRUCTURES_SCHEMA)

        molobject = mol_read(config['mol'], mol_format=config.get('input_format'),
                             from_file=config.get('from_file', False), toolkit=config.get('toolkit', 'pybel'))

        file_path = None
        if 'workdir' in config:
            file_path = os.path.join(config.get('workdir'), 'structure.{0}'.format(config.get('output_format')))

        output = mol_write(molobject, mol_format=config.get('output_format'), file_path=file_path)

        # Update session
        session.status = 'completed'

        return {'mol': output, 'session': session.dict()}

    @wamp.register(u'liestudio.structure.addh')
    def addh_structures(self, session=None, **kwargs):
        """
        Add hydrogens to the input structure
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session or {}).dict()

        # Load configuration and update
        config = self.package_config.lie_structures.dict()
        config.update(kwargs)

        # Validate against JSON schema
        jsonschema.validate(config, STRUCTURES_SCHEMA)

        molobject = mol_read(config['mol'], mol_format=config.get('input_format'),
                             from_file=config.get('from_file', False), toolkit=config.get('toolkit', 'pybel'))
        molobject = mol_addh(
            molobject,
            polaronly=config.get('polaronly'),
            correctForPH=config.get('correctForPH'),
            pH=config.get('pH'))

        file_path = None
        if 'workdir' in config:
            file_path = os.path.join(config.get('workdir'), 'structure.{0}'.format(config.get('input_format')))

        output = mol_write(molobject, mol_format=config.get('output_format'), file_path=file_path)

        # Update session
        session['status'] = 'completed'

        return {'mol': output, 'session': session}

    @wamp.register(u'liestudio.structure.removeh')
    def removeh_structures(self, session=None, **kwargs):
        """
        Remove hydrogens from the input structure
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session or {}).dict()

        # Load configuration and update
        config = self.package_config.lie_structures.dict()
        config.update(kwargs)

        # Validate against JSON schema
        jsonschema.validate(config, STRUCTURES_SCHEMA)

        molobject = mol_read(config['mol'], mol_format=config.get('input_format'),
                             from_file=config.get('from_file', False), toolkit=config.get('toolkit', 'pybel'))
        molobject = mol_removeh(molobject)

        file_path = None
        if 'workdir' in config:
            file_path = os.path.join(config.get('workdir'), 'structure.{0}'.format(config.get('input_format')))

        output = mol_write(molobject, mol_format=config.get('output_format'), file_path=file_path)

        # Update session
        session['status'] = 'completed'

        return {'mol': output, 'session': session}

    @wamp.register(u'liestudio.structure.make3d')
    def make3d_structures(self, session=None, **kwargs):
        """
        Convert 1D or 2D structure representation to 3D
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session or {})

        # Load configuration and update
        config = self.package_config.lie_structures.dict()
        config.update(kwargs)

        # Validate against JSON schema
        jsonschema.validate(config, STRUCTURES_SCHEMA)

        molobject = mol_read(config['mol'], mol_format=config.get('input_format'),
                             from_file=config.get('from_file', False), toolkit=config.get('toolkit', 'pybel'))
        molobject = mol_make3D(
            molobject,
            forcefield=config.get('forcefield'),
            localopt=config.get('localopt', True),
            steps=config.get('steps', 50))

        file_path = None
        if 'workdir' in config:
            file_path = os.path.join(config.get('workdir'), 'structure.{0}'.format(config.get('input_format')))

        output = mol_write(molobject, mol_format=config.get('output_format'), file_path=file_path)

        # Update session
        session.status = 'completed'

        return {'mol': output, 'session': session.dict()}

    @wamp.register(u'liestudio.structure.info')
    def structure_attributes(self, session=None, **kwargs):
        """
        Return common structure attributes
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session or {}).dict()

        # Load configuration and update
        config = self.package_config.lie_structures.dict()
        config.update(kwargs)

        # Validate against JSON schema
        jsonschema.validate(config, STRUCTURES_SCHEMA)

        molobject = mol_read(config['mol'], mol_format=config.get('input_format'),
                             from_file=config.get('from_file', False), toolkit=config.get('toolkit', 'pybel'))
        attributes = mol_attributes(molobject) or {}

        # Update session
        session['status'] = 'completed'
        attributes['session'] = session

        return attributes

    @wamp.register(u'liestudio.structure.rotate')
    def rotate_structures(self, session=None, **kwargs):
        """
        Rotate the structure around an axis defined by x,y,z
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        # Load configuration and update
        config = self.package_config.lie_structures.dict()
        config.update(kwargs)

        # Validate against JSON schema
        jsonschema.validate(config, STRUCTURES_SCHEMA)

        # Read in the molecule
        molobject = mol_read(config['mol'], mol_format=config.get('input_format'),
                             from_file=config.get('from_file', False), toolkit=config.get('toolkit', 'pybel'))

        rotations = config.get('rotations')
        if rotations:
            output_file = mol_combine_rotations(molobject, rotations=rotations)

            if 'workdir' in config:
                file_path = os.path.join(config.get('workdir'), 'rotations.mol2')
                with open(file_path, 'w') as otp:
                    otp.write(output_file)
                output_file = file_path

            session['status'] = 'completed'
            return {'session': session, 'mol': output_file}

        session['status'] = 'failed'
        return {'session': session}
