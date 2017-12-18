# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

import json
import jsonschema
import os
import six
import tempfile

from StringIO import StringIO
from autobahn import wamp
from Bio.PDB import PDBList
from Bio.PDB.PDBIO import PDBIO
from Bio.PDB.PDBParser import PDBParser

from lie_system import LieApplicationSession, WAMPTaskMetaData
from lie_structures import settings
from lie_structures.settings import _schema_to_data, STRUCTURES_SCHEMA, BIOPYTHON_SCHEMA
from lie_structures.cheminfo_utils import (
     mol_addh, mol_attributes, mol_make3D, mol_read, mol_removeh, mol_write, mol_combine_rotations)

STRUCTURES_SCHEMA = json.load(open(STRUCTURES_SCHEMA))
BIOPYTHON_SCHEMA = json.load(open(BIOPYTHON_SCHEMA))


class StructuresWampApi(LieApplicationSession):
    """
    Structure database WAMP methods.
    """

    require_config = ['system']

    @wamp.register(u'liestudio.structures.get_structure')
    def get_structure(self, structure=None, session=None, **kwargs):
        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session)

        result = ''
        tmpdir = kwargs['tmpdir']
        structure_file = os.path.join(tmpdir, structure)
        if os.path.exists(structure_file):
            with open(structure_file, 'r') as sf:
                result = sf.read()
        else:
            self.log.error("No such file {0}".format(structure_file))

        self.log.info(
            "Return structure: {structure}",
            structure=structure, **self.session_config.dict())

        # Pack result in session
        session.status = 'completed'
        return {'session': session.dict(), 'structure': result}

    @wamp.register(u'liestudio.structure.remove_residues')
    def remove_residues(self, session=None, **kwargs):
        """
        Remove residues from a PDB structure
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        # Parse the structure
        parser = PDBParser(PERMISSIVE=True)

        if kwargs.get('from_file', False):
            struc_obj = open(kwargs.get('mol'), 'r')
        else:
            struc_obj = StringIO(kwargs.get('mol'))

        structure = parser.get_structure('mol_object', struc_obj)
        struc_obj.close()

        to_remove = [r.upper() for r in kwargs.get('residues', [])]
        removed = []
        for model in structure:
            for chain in model:
                for residue in chain:
                    if residue.get_resname() in to_remove:
                        chain.detach_child(residue.id)
                        removed.append(residue.get_resname())
                if len(chain) == 0:
                    model.detach_child(chain.id)
        self.log.info('Removed residues: {0}'.format(','.join(removed)))

        # Save to file or string
        pdbio = PDBIO()
        pdbio.set_structure(structure)

        session['status'] = 'completed'
        if kwargs.get('workdir'):
            outfile = os.path.join(kwargs.get('workdir'), 'structure.pdb')
            pdbio.save(outfile)
            return {'session': session, 'mol': outfile}
        else:
            outfile = StringIO()
            pdbio.save(outfile)
            outfile.seek(0)
            return {'session': session, 'mol': outfile.read()}

    @wamp.register(u'liestudio.structure.retrieve_rcsb_structure')
    def fetch_rcsb_structure(self, session=None, **kwargs):
        """
        Download a structure file from the RCSB database using a PDB ID
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        # Load configuration and update
        config = _schema_to_data(BIOPYTHON_SCHEMA)
        config.update(kwargs)

        # Validate the configuration
        try:
            jsonschema.validate(config, BIOPYTHON_SCHEMA)
        except ValueError, e:
            self.logger.error('Unvalid function arguments: {0}'.format(e))
            session['status'] = 'failed'
            return {'session': session}

        # Create workdir and save file
        workdir = os.path.join(config.get('workdir', tempfile.gettempdir()))
        if not os.path.isdir(workdir):
            os.makedirs(workdir)

        # Retrieve the PDB file
        pdb_id = config['pdb_id'].upper()
        pdb = PDBList()
        dfile = pdb.retrieve_pdb_file(pdb_id,
                              file_format=config.get('rcsb_file_format', 'pdb'),
                              pdir=workdir,
                              overwrite=True)

        # Change file extension
        base, ext = os.path.splitext(dfile)
        if ext == '.ent':
            os.rename(dfile, '{0}.pdb'.format(base))
            dfile = '{0}.pdb'.format(base)

        # Return file path if workdir in function arguments else return
        # file content inline.
        if os.path.isfile(dfile):
            session['status'] = 'completed'
            if 'workdir' in config:
                return {'session': session, 'mol': dfile}
            else:
                return {'session': session, 'mol': open(dfile).read()}

        self.logger.error('Unable to download structure: {0}'.format(pdb_id), **session)
        session['status'] = 'failed'
        return {'session': session}

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

        # Create workdir and save file
        workdir = os.path.join(kwargs.get('workdir', tempfile.gettempdir()))

        # Input/output molecule
        inp_fmt = config.get('input_format')
        out_fmt = config.get('output_format')
        self.log.info(
            "Reading Molecule in {} format".format(inp_fmt))

        mol = config['mol']
        if os.path.isfile(mol):
            with open(mol, 'r') as f:
                mol = f.read(mol)

        molobject = mol_read(mol, mol_format=inp_fmt)

        self.log.info("Writing Molecule in {} format".format(out_fmt))
        output = mol_write(
            molobject,  mol_format=out_fmt)

        path = os.path.join(workdir, 'output.{}'.format(out_fmt))
        with open(path, 'w') as f:
            f.write(output)

        # Update session
        session.status = 'completed'

        return {'mol': six.text_type(path), 'session': session.dict()}

    @wamp.register(u'liestudio.structure.addh')
    def addh_structures(self, session=None,  **kwargs):
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
                             from_file=config.get('from_file', False))
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
    def removeh_structures(self, session=None,  **kwargs):
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
                             from_file=config.get('from_file', False))
        molobject = mol_removeh(molobject)

        file_path = None
        if 'workdir' in config:
            file_path = os.path.join(config.get('workdir'), 'structure.{0}'.format(config.get('input_format')))

        output = mol_write(molobject, mol_format=config.get('output_format'), file_path=file_path)

        # Update session
        session['status'] = 'completed'

        return {'mol': output, 'session': session}

    @wamp.register(u'liestudio.structure.make3d')
    def make3d_structures(self, session=None,  **kwargs):
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
                             from_file=config.get('from_file', False))
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
                             from_file=config.get('from_file', False))
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
                             from_file=config.get('from_file', False))

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
        return StructuresWampApi(config, package_config=settings)
    else:
        # if no config given, return a description of this WAMPlet ..
        return {
            'label': 'LIEStudio structure management WAMPlet',
            'description':
            'WAMPlet proving LIEStudio structure management endpoints'}
