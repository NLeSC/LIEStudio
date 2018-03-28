# -*- coding: utf-8 -*-

"""
file: cheminfo_molhandle.py

Cinfony driven cheminformatics fingerprint functions
"""

import logging

from itertools import combinations
from twisted.logger import Logger
from scipy.spatial.distance import squareform
from numpy import array

from . import toolkits

logging = Logger()

RDKIT_SYM_METRIC = {'tanimoto': 'TanimotoSimilarity', 'dice': 'DiceSimilarity',
                    'cosine': 'CosineSimilarity', 'sokal': 'SokalSimilarity',
                    'russel': 'RusselSimilarity', 'kulczynski': 'KulczynskiSimilarity',
                    'mcconnaughey': 'McConnaugheySimilarity', 'tversky': 'TverskySimilarity'}


def available_fingerprints():
    """
    List available molecular fingerprint methods for all active cheminformatics
    packages

    :rtype: :py:dict
    """

    available_fps = {}
    for toolkit, obj in toolkits.items():
        if hasattr(obj, 'fps'):
            available_fps[toolkit] = obj.fps

    return available_fps


def mol_fingerprint(molobject, fp=None):
    """
    Return a molecular fingerprint

    :param molobject: Cinfony molecular object
    :type molobject:  :cinfony:molobject
    :param fp:        fingerprint type
    :type fp:         :py:str

    :return:          fingerprint object
    :rtype:           :cinfony:Fingerprint
    """

    afp = available_fingerprints()
    if molobject.toolkit not in afp:
        logging.error('No fingerprint methods supported by toolkit {0}'.format(molobject.toolkit))
        return

    if fp:
        if fp not in afp[molobject.toolkit]:
            logging.error('Fingerprint methods {0} not supported by toolkit {1}'.format(
                afp, molobject.toolkit))
            return

        logging.info('Calculate {0} fingerprint using toolkit {1}'.format(fp, molobject.toolkit))
        fpobj = molobject.calcfp(fp)

        return fpobj

    logging.info('Calculate fingerprint using toolkit {0}'.format(molobject.toolkit))
    fpobj = molobject.calcfp()

    return fpobj


def mol_fingerprint_comparison(u, v, toolkit, metric='tanimoto'):
    """
    Compare two fingerprints using metric

    Tanimoto is the default metric supported by all toolkits.
    RDKit in addition supports: dice, cosine, sokal, russel,
    kulczynski, mcconnaughey, and tversky.

    TODO: cross-toolkit fingerprint bits generation and comparison metrics
    TODO: perhaps use Python 'chemfp' module

    :param toolkit: toolkit used to calculate fingerprint
    :type toolkit:  :py:str
    :param metric:  comparison metric
    :type metric:   :py:str

    :return:        similarity metric
    :rtype:         :py:float
    """

    # For Tanimoto use Cinfony wrapper
    if metric == 'tanimoto':
        return u | v

    # For RDKit use underlying similarity methods
    if toolkit == 'rdk':
        rdkit = toolkits.get('rdk')
        metric = getattr(rdkit.Chem.DataStructs, RDKIT_SYM_METRIC[metric])
        return rdkit.Chem.DataStructs.FingerprintSimilarity(u.fp, v.fp, metric=metric)

    logging.error('Fingerprint comparison metric {0} not supported by toolkit {1}'.format(metric, toolkit))


def mol_fingerprint_pairwise_similarity(fps, toolkit, metric='tanimoto'):
    """
    Build pairwise similarity matrix for fingerprints using the
    mol_fingerprint_comparison function

    :param fps:     Cinfony Fingerprint objects
    :type fps:      :cinfony:Fingerprints
    :param toolkit: toolkit used to calculate fingerprint
    :type toolkit:  :py:str
    :param metric:  comparison metric
    :type metric:   :py:str

    :return:        squareform of condensed similarity matrix
    :rtype:         :numpy:ndarray
    """

    condensed_matrix = []
    for comb in combinations(fps, 2):
        condensed_matrix.append(mol_fingerprint_comparison(comb[0], comb[1], toolkit, metric=metric))

    return squareform(array(condensed_matrix))


def mol_fingerprint_cross_similarity(fps1, fps2, toolkit, metric='tanimoto'):
    """
    Build a non-pairwise similarity matrix between the fingerprints of fps1 on
    the y-axis (rows) and fps2 in the x-axis (columns). This can result in a
    non-square matrix.

    :param fps1:    Cinfony Fingerprint objects for y-axis
    :type fps1:     :cinfony:Fingerprints
    :param fps2:    Cinfony Fingerprint objects for x-axis
    :type fps2:     :cinfony:Fingerprints
    :param toolkit: toolkit used to calculate fingerprint
    :type toolkit:  :py:str
    :param metric:  comparison metric
    :type metric:   :py:str

    :return:        non-square similarity matrix
    :rtype:         :numpy:ndarray
    """

    simmat = []
    for fp1 in fps1:
        row = []
        for fp2 in fps2:
            row.append(mol_fingerprint_comparison(fp1, fp2, toolkit, metric=metric))
        simmat.append(row)

    return array(simmat)