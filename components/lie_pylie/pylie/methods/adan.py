# -*- coding: utf-8 -*-

"""
eTOX ALLIES Applicability Domain Analysis

As described in:
Capoferri, L., van Dijk, M., Rustenburg, A. S., Wassenaar, T. A., Kooi, D. P.,
Rifai, E. A. and Geerke, D. P. "eTOX ALLIES: an automated pipeLine for linear
interaction energy-based simulations" Journal of Cheminformatics, 2017, 9, 58.
http://doi.org/10.1186/s13321-017-0243-x
"""

import pandas
import re
import logging
import numpy

from sklearn.covariance import EmpiricalCovariance

from ..model.liemdframe import LIEMDFrame


def parse_gromacs_decomp(ene_file, parse_rest=True):
    """
    Parse Gromacs per residue decomposition file into a pandas DataFrame
    and calculate trajectory average energy values

    :param ene_file:   Gromacs per-residue energy decomposition file
    :type ene_file:    :py:str
    :param parse_rest: parse the residual column (*-rest-*)
    :type parse_rest:  :py:bool

    :return:           pandas DataFrame
    :rtype:            :pandas:DataFrame
    """

    # Import file
    decomp = LIEMDFrame(pandas.read_csv(ene_file, sep='\s+'))

    # Select columns containing residue numbers
    residue_cols = decomp.get_columns('(\D+)?[0-9]+(\D+)?', regex=True)

    # Parse the residuals column
    if parse_rest:
        residue_cols.extend(decomp.get_columns('(.*?)rest(.*?)', regex=True, flags=re.I))

    # Select residue containing columns and calculate average
    decomp = decomp[residue_cols]
    select = decomp.mean()

    # Reformat DataFrame, VdW and Elec in seperate columns
    vdw_col = decomp.get_columns('(.*?)vdw(.*?)', regex=True, flags=re.I)
    ele_col = decomp.get_columns('(.*?)ele(.*?)', regex=True, flags=re.I)

    r = re.compile('\D')
    numbers = [r.sub('', n) for n in ele_col]

    return pandas.DataFrame({'residues': numbers, 'vdw': select[vdw_col].values, 'ele': select[ele_col].values})


def ad_residue_decomp(decomp_df_list, pca_vdw, pca_ele, cases=None):
    """
    eTOX ALLIES per-residue energy decomposition AD analysis

    - Note:
    The `pca_*` argument needs to be a dictionary of a trained eTOX ALLIES
    PCA model for the VdW and Elec component of the residue decomposition
    energie profile.

    :param decomp_df_list: list of DataFrames with average per-residue
                           decomposition energy values
    :type decomp_df_list:  :py:list
    :param pca_vdw:        VdW principle component model based on training set
    :type pca_vdw:         :py:dict
    :param pca_ele:        Ele principle component model based on training set
    :type pca_ele:         :py:dict
    :param cases:          List of case ID's
    :type cases:           :py:list

    :return:               decomposition AD test results
    :rtype:                :pandas:DataFrame
    """

    # Create DataFrame to hold results
    if not cases:
        cases = range(1, len(decomp_df_list) + 1)
    assert len(cases) == len(decomp_df_list), AssertionError('Number of cases does not match number of data sets')

    results = pandas.DataFrame({'cases': cases})

    # PCA based decomposition AD analysis
    columns = ('vdw', 'ele')
    for i, pca in enumerate((pca_vdw, pca_ele)):

        data_collection = []
        for df in decomp_df_list:
            data_collection.append(df[columns[i]].values)

        if 'scale_' not in dir(pca['scaler']):
            pca['scaler'].scale_ = None
        if 'std_' not in dir(pca['scaler']):
            pca['scaler'].std_ = None

        x_sc = pca['scaler'].transform(numpy.array(data_collection))
        p = pca['pca'].components_[:pca['n_pc']]
        transform = pca['pca'].transform(x_sc)
        transform = numpy.array(transform)[:, :pca['n_pc']]

        sd = numpy.sqrt(numpy.sum(numpy.divide(transform**2, pca['sdev']**2), axis=1))
        od = numpy.sqrt(numpy.sum(numpy.subtract(numpy.dot(transform, p), x_sc)**2, axis=1))

        results['{0}_sd'.format(columns[i])] = sd
        results['{0}_od'.format(columns[i])] = od

        # Calculate applicability domain CI value
        results['{0}_CI'.format(columns[i])] = ((results['{0}_od'.format(columns[i])] > pca['critOD']) | (
                results['{0}_sd'.format(columns[i])] > pca['critSD'])).astype(int)

    return results


def ad_dene(ene_df, cov, center=None, ci_cutoff=None, columns=['w_vdw', 'w_coul']):
    """
    eTOX ALLIES deltaG VdW/Elec energy applicability domain analysis

    Calculates the Mahalanobis distance for a set of deltaG VdW/Elec energy
    values with respect to the distribution in the training set.
    Requires a pandas DataFrame with a VdW and Elec column in it and
    returns the frame with two new columns addad to it:

    * mahal: the Mahalanobis distance with respect to the training set
    * CI:    the result of the AD test if a cutoff value is provided.
             If the Mahalanobis distance is smaller then the cutoff
             a 0 is listed (test passed) else 1.

    - Note:
    The `cov` argument needs to be a Sklearn EmpiricalCovariance instance that
    is pre-trained using the training data.

    :param ene_df:    pandas DataFrame with energy values
    :type ene_df:     :pandas:DataFrame
    :param cov:       the emperical covariance matrix used to calculate the
                      Mahalanobis distance
    :type cov:        :sklearn:covariance:EmpiricalCovariance
    :param center:    Center each VdW/Elec value pair by subtracting a fixed
                      [VdW, Elec] value pair from it.
    :type center:     :py:list
    :param ci_cutoff: The maximum Mahalanobis distance used as cutoff value for
                      the applicability domain test
    :type ci_cutoff:  :py:float
    :param columns:   pandas DataFrame column names for the VdW and Elec columns
    :type columns:    :py:list

    :return:          Mahalanobis distance and AD test results
    :rtype:           :pandas:DataFrame
    """

    # Check if VdW and Elec are present in the DataFrame
    assert set(columns).issubset(set(ene_df.columns)),\
        KeyError('Energy DataFrame has no columns: {0}'.format(', '.join(columns)))

    # Center data if needed
    if center:
        assert len(center) == 2, ValueError('Center should be list of length 2')
        ene_df[columns] = ene_df[columns] - center

    # Calculate Mahalanobis distance
    assert isinstance(cov, EmpiricalCovariance),\
        AssertionError('cov not of type EmpiricalCovariance: {0}'.format(type(cov)))
    ene_df['mahal'] = cov.mahalanobis(ene_df[columns])

    # Calculate applicability domain CI value if ci_cutoff defined
    if ci_cutoff:
        ene_df['CI'] = (ene_df['mahal'] >= ci_cutoff).astype(int)
        logging.info('DeltaG AD analysis with cutoff {0}'.format(ci_cutoff))

    return ene_df


def ad_dene_yrange(ene_df, ymin, ymax, column='dg_calc'):
    """
    eTOX ALLIES deltaG range applicability domain test

    Evaluates rather the calculated deltaG value is with a range defined
    by `ymin` and `ymax`. Adds a CI column to the DataFrame with the test
    results.

    :param ene_df:  pandas DataFrame with energy values
    :type ene_df:   :pandas:DataFrame
    :param ymin:    lower value for deltaG range
    :type ymin:     :py:float
    :param ymax:    upper value for deltaG range
    :type ymax:     :py:float
    :param column:  pandas DataFrame column name for deltaG
    :type column:   :py:str

    :return:        AD test results
    :rtype:         :pandas:DataFrame
    """

    # Check if calculated deltaG column in DataFrame
    assert column in ene_df.columns, KeyError('DataFrame contains no {0} column'.format(column))

    ene_df['CI'] = ((ene_df[column] > ymin) & (ene_df[column] < ymax)).astype(int)
    logging.info('DeltaG distribution AD analysis between {0} - {1}'.format(ymin, ymax))

    return ene_df