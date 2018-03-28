# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""
from lie_md.cerise_interface import (
    call_cerise_gromit, create_cerise_config)
from lie_md.md_config import set_gromacs_input
from mdstudio.api.endpoint import endpoint
from mdstudio.deferred.chainable import chainable
from mdstudio.component.session import ComponentSession
from mdstudio.deferred.return_value import return_value
from os.path import join
import json


class MDWampApi(ComponentSession):
    """
    Molecular dynamics WAMP methods.
    """
    def authorize_request(self, uri, claims):
        return True

    @endpoint('liemd', 'liemd_request', 'liemd_response')
    @chainable
    def run_gromacs_liemd(self, request, claims):
        """
        First it calls gromit to compute the Ligand-solute energies, then
        calls gromit to calculate the protein-ligand energies.

        The Cerise-client infrastructure is used to perform the computations
        in a remote server, see:
        http://cerise-client.readthedocs.io/en/master/index.html

        This function expects the following keywords files to call gromit:
            * cerise_file
            * protein_file (optional)
            * protein_top
            * ligand_file
            * topology_file
            * reSidues

        The cerise_file is the path to the file containing the configuration
        information required to start a Cerise service.

        Further include files (e.g. *itp files) can be included as a list:
        include=[atom_types.itp, another_itp.itp]

        To perform the energy decomposition a list of the numerical residues
        identifiers is expected, for example:
        residues=[1, 5, 7, 8]

        Note: the protein_file arguments is optional if you do not provide it
        the method will perform a SOLVENT LIGAND MD if you provide the
        `protein_file` it will perform a PROTEIN-LIGAND MD.
        """
        task_id = self.component_config.session.session_id
        request.update({"task_id": task_id})
        self.log.info("starting liemd task_id:{}".format(task_id))

        # Load GROMACS configuration
        gromacs_config = set_gromacs_input(request)

        # Load Cerise configuration
        cerise_config = create_cerise_config(request)

        with open(join(request['workdir'], "cerise.json"), "w") as f:
            json.dump(cerise_config, f)

        # Run the MD and retrieve the energies
        output = yield call_cerise_gromit(
            gromacs_config, cerise_config, self.db)

        status = 'failed' if output is None else 'completed'
        # return {'status': status, 'output': output}

        return_value({'status': status, 'output': {"random": 42}})
