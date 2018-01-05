# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

import numpy
import pandas

from autobahn import wamp

from lie_system import WAMPTaskMetaData
from lie_structures.cheminfo_molhandle import mol_read
from lie_structures.cheminfo_fingerprint import mol_fingerprint_cross_similarity


class CheminfoFingerprintsWampApi(object):
    """
    Cheminformatics fingerprints WAMP API
    """

    @wamp.register(u'liestudio.cheminfo.chemical_similarity')
    def calculate_chemical_similarity(self, test_set=None, reference_set=None, mol_format=None, toolkit='pybel',
                                      fp_format='maccs', metric='tanimoto', ci_cutoff=None, session=None, **kwargs):
        """
        Calculate the chemical similarity between two sets each containing one
        or more structures.
        The structure formats needs to be identical for all structures in both
        sets.

        :param test_set:        test set to calculate similarity for
        :param reference_set:   set to calculate similarity against
        :param mol_format:      structure format
        :param toolkit:         cheminformatics toolkit to use
        :param fp_format:       fingerprint format
        :param metric:          similarity metric
        :param ci_cutoff:       AP CI cutoff value
        :param session:         WAMP session information
        :return:
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session)

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

        session.status = 'completed'
        return {'session': session.dict(), 'result': stats.to_dict()}

