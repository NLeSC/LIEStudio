# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

import os
import tempfile

from StringIO import StringIO
from Bio.PDB import PDBList
from Bio.PDB.PDBIO import PDBIO
from Bio.PDB.PDBParser import PDBParser

from lie_structures import toolkits
from lie_structures.cheminfo_wamp.cheminfo_descriptors_wamp import CheminfoDescriptorsWampApi
from lie_structures.cheminfo_wamp.cheminfo_molhandle_wamp import CheminfoMolhandleWampApi
from lie_structures.cheminfo_wamp.cheminfo_fingerprints_wamp import CheminfoFingerprintsWampApi
from mdstudio.api.endpoint import endpoint
from mdstudio.component.session import ComponentSession


class StructuresWampApi(
        CheminfoDescriptorsWampApi, CheminfoMolhandleWampApi,
        CheminfoFingerprintsWampApi, ComponentSession):
    """
    Structure database WAMP methods.
    """
    def authorize_request(self, uri, claims):
        return True

    @endpoint('supported_toolkits', 'supported_toolkits_request', 'supported_toolkits_response')
    def supported_toolkits(self, request, claims):
        """
        Query available toolkits.

        For a detailed input description see the file:
           lie_structures/schemas/endpoints/supported_toolkits_request_v1.json
        And for a detailed description of the output see:
           lie_structures/schemas/endpoints/supported_toolkits_response_v1.json
        """
        return {'status': 'completed', 'toolkits': toolkits.keys()}

    @endpoint('remove_residues', 'remove_residues_request', 'remove_residues_response')
    def remove_residues(self, request, claims):
        """
        Remove residues from a PDB structure

        For a detailed input description see the file:
           lie_structures/schemas/endpoints/removed_residues_request_v1.json
        And for a detailed description of the output see:
           lie_structures/schemas/endpoints/removed_residues_response_v1.json
        """
        # Parse the structure
        parser = PDBParser(PERMISSIVE=True)

        if request.get('from_file', False):
            struc_obj = open(request.get('mol'), 'r')
        else:
            struc_obj = StringIO(request.get('mol'))

        structure = parser.get_structure('mol_object', struc_obj)
        struc_obj.close()

        to_remove = [r.upper() for r in request.get('residues', [])]
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

        status = 'completed'
        if request.get('workdir'):
            result = os.path.join(request.get('workdir'), 'structure.pdb')
            pdbio.save(result)
        else:
            outfile = StringIO()
            pdbio.save(outfile)
            outfile.seek(0)
            result = outfile.read()

        return {'status': status, 'mol': result}

    @endpoint('retrieve_rcsb_structure', 'retrieve_rcsb_structure_request', 'retrieve_rcsb_structure_response')
    def fetch_rcsb_structure(self, request, claims):
        """
        Download a structure file from the RCSB database using a PDB ID

        For a detailed input description see the file:
           lie_structures/schemas/endpoints/retrieve_rcsb_structures_request_v1.json
        And for a detailed description of the output see:
           lie_structures/schemas/endpoints/retrieve_rcsb_structures_response_v1.json
        """
        # Create workdir and save file
        workdir = os.path.join(request.get('workdir', tempfile.gettempdir()))
        if not os.path.isdir(workdir):
            os.makedirs(workdir)

        # Retrieve the PDB file
        pdb_id = request['pdb_id'].upper()
        pdb = PDBList()
        dfile = pdb.retrieve_pdb_file(
            pdb_id, file_format=request.get('rcsb_file_format', 'pdb'), pdir=workdir,
            overwrite=True)

        # Change file extension
        base, ext = os.path.splitext(dfile)
        if ext == '.ent':
            os.rename(dfile, '{0}.pdb'.format(base))
            dfile = '{0}.pdb'.format(base)

        # Return file path if workdir in function arguments else return
        # file content inline.
        if os.path.isfile(dfile):
            status = 'completed'
            if 'workdir' in request:
                molecule = dfile
            else:
                with open(dfile, 'r') as f:
                    molecule = f.read()

        else:
            self.log.error(
                'Unable to download structure: {0}'.format(pdb_id))
            status = 'failed'
            molecule = None

        return {'status': status, 'mol': molecule}
