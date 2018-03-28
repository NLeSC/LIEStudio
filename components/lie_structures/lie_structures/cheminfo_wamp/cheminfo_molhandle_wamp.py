# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

import os

from lie_structures.cheminfo_molhandle import (
     mol_addh, mol_attributes, mol_make3D, mol_read, mol_removeh, mol_write, mol_combine_rotations)

from mdstudio.api.endpoint import endpoint
from mdstudio.component.session import ComponentSession


class CheminfoMolhandleWampApi(ComponentSession):
    """
    Cheminformatics molecule handling WAMP API
    """
    def authorize_request(self, uri, claims):
        return True

    @staticmethod
    def read_mol(config):
        """Read molecular structure using `config` """

        return mol_read(
            config['mol'], mol_format=config['input_format'],
            from_file=config['from_file'],
            toolkit=config['toolkit'])

    @endpoint('convert', 'convert_request', 'convert_response')
    def convert_structures(self, request, claims):
        """
        Convert input file format to a different format. For a detailed
        input description see the file:
           lie_structures/schemas/endpoints/convert_request_v1.json
        And for a detailed description of the output see:
           lie_structures/schemas/endpoints/convert_response_v1.json
        """
        molobject = self.read_mol(request)

        file_path = None
        if 'workdir' in request:
            file_path = os.path.join(request['workdir'], 'structure.{0}'.format(request['output_format']))

        output = mol_write(molobject, mol_format=request['output_format'], file_path=file_path)

        # Update session
        status = 'completed'

        return {'mol': output, 'status': status}

    @endpoint('addh', 'addh_request', 'addh_response')
    def addh_structures(self, request, claims):
        """
        Add hydrogens to the input structue. For a detailed
        input description see the file:
           lie_structures/schemas/endpoints/addh_request_v1.json
        And for a detailed description of the output see:
           lie_structures/schemaS/endpoints/addh_response_v1.json
        """
        molobject = mol_addh(
            self.read_mol(request),
            polaronly=request['polaronly'],
            correctForPH=request['correctForPH'],
            pH=request['pH'])

        if 'workdir' in request:
            file_path = os.path.join(request['workdir'], 'structure.{0}'.format(request['input_format']))
        else:
            file_path = None

        output = mol_write(molobject, mol_format=request['output_format'], file_path=file_path)

        # Update session
        status = 'completed'

        return {'mol': output, 'status': status}

    @endpoint('removeh', 'removeh_request', 'removeh_response')
    def removeh_structures(self, request, claims):
        """
        Remove hydrogens from the input structure. For a detailed
        input description see the file:
           lie_structures/schemas/endpoints/removeh_request_v1.json
        And for a detailed description of the output see:
           lie_structures/schemas/endpoints/removeh_response_v1.json
        """
        molobject = mol_removeh(self.read_mol(request))

        file_path = None
        if 'workdir' in request:
            file_path = os.path.join(request['workdir'], 'structure.{0}'.format(request['input_format']))

        output = mol_write(molobject, mol_format=request['output_format'], file_path=file_path)

        # Update session
        status = 'completed'

        return {'mol': output, 'status': status}

    @endpoint('make3d', 'make3d_request', 'make3d_response')
    def make3d_structures(self, request, claims):
        """
        Convert 1D or 2D structure representation to 3D.
        For a detailed
        input description see the file:
          lie_structures/schemas/endpoints/make3d_request_v1.json
        And for a detailed description of the output see:
          lie_structures/schemas/endpoints/make3d_response_v1.json
        """
        molobject = mol_make3D(
            self.read_mol(request),
            forcefield=request['forcefield'],
            localopt=request['localopt'],
            steps=request['steps'])

        file_path = None
        if 'workdir' in request:
            file_path = os.path.join(request['workdir'], 'structure.{0}'.format(request['input_format']))

        output = mol_write(molobject, mol_format=request['output_format'], file_path=file_path)

        # Update session
        status = 'completed'

        return {'mol': output, 'status': status}

    @endpoint('info', 'info_request', 'info_response')
    def structure_attributes(self, request, claims):
        """
        Return common structure attributes
        For a detailed input description see the file:
          lie_structures/schemas/endpoints/info_request_v1.json

        And for a detailed description of the output see:
          lie_structures/schemas/endpoints/info_response_v1.json
        """
        # Retrieve the WAMP session information
        molobject = self.read_mol(request)
        attributes = mol_attributes(molobject) or {}

        # Update session
        status = 'completed'

        return {'status': status, 'attributes': attributes}

    @endpoint('rotate', 'rotate_request', 'rotate_response')
    def rotate_structures(self, request, claims):
        """
        Rotate the structure around an axis defined by x,y,z.
        For a detailed input description see the file:
          lie_structures/schemas/endpoints/rotate_request_v1.json

        And for a detailed description of the output see:
          lie_structures/schemas/endpoints/rotate_response_v1.json

        """
        # Read in the molecule
        molobject = self.read_mol(request)

        rotations = request['rotations']
        if rotations:
            result = mol_combine_rotations(molobject, rotations=rotations)

            if 'workdir' in request:
                file_path = os.path.join(request['workdir'], 'rotations.mol2')
                with open(file_path, 'w') as otp:
                    otp.write(result)
                output = file_path
            status = 'completed'
        else:
            status = 'failed'
            output = None

        return {'status': status, 'mol': output}
