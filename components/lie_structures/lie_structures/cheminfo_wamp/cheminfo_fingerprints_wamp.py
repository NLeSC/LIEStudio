# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

import os
import numpy
import pandas

from lie_structures.cheminfo_molhandle import mol_read
from lie_structures.cheminfo_fingerprint import mol_fingerprint_cross_similarity
from mdstudio.api.endpoint import endpoint
from mdstudio.component.session import ComponentSession


class CheminfoFingerprintsWampApi(ComponentSession):
    """
    Cheminformatics fingerprints WAMP API
    """
    def authorize_request(self, uri, claims):
        return True

    @endpoint('chemical_similarity', 'chemical_similarity_request', 'chemical_similarity_response')
    def calculate_chemical_similarity(self, request, claims):
        """
        Calculate the chemical similarity between two sets each containing one
        or more structures.
        The structure formats needs to be identical for all structures in both
        sets.

        see the file schemas/endpoints/chemical_similarity_request.v1.json file
        for a detail description of the input.
        """
        metric = request['metric']
        toolkit = request['toolkit']
        mol_format = request['mol_format']
        test_set = request['test_set']
        reference_set = request['reference_set']
        fp_format = request['fp_format']
        ci_cutoff = request['ci_cutoff']

        # Import the molecules
        test_mols = [mol_read(x, mol_format=mol_format, toolkit=toolkit) for x in test_set]
        reference_mols = [mol_read(x, mol_format=mol_format, toolkit=toolkit) for x in reference_set]

        # Calculate the fingerprints
        test_fps = [m.calcfp(fp_format) for m in test_mols]
        reference_fps = [m.calcfp(fp_format) for m in reference_mols]

        # Calculate the similarity matrix
        simmat = mol_fingerprint_cross_similarity(test_fps, reference_fps, toolkit, metric=metric)

        # Calculate average similarity, maximum similarity and report the index
        # of the reference case with maximum similarity.
        stats = [numpy.mean(simmat, axis=1), numpy.max(simmat, axis=1), numpy.argmax(simmat, axis=1)]

        # Format as Pandas DataFrame and export as JSON
        stats = pandas.DataFrame(stats).T
        stats.columns = ['average', 'max_sim', 'idx_max_sim']
        stats['idx_max_sim'] = stats['idx_max_sim'].astype(int)

        # Calculate applicability domain CI value if ci_cutoff defined
        if ci_cutoff:
            stats['CI'] = (stats['average'] >= ci_cutoff).astype(int)
            self.log.info('Chemical similarity AD analysis with cutoff {0}'.format(ci_cutoff))

        # Create workdir and save file
        workdir = request['workdir']
        if not os.path.isdir(workdir):
            os.mkdir(workdir)
            self.log.debug('Create working directory: {0}'.format(workdir))
        filepath = os.path.join(workdir, 'adan_chemical_similarity.csv')
        stats.to_csv(filepath)

        status = 'completed'
        return {'status': status, 'result': stats.to_dict()}
