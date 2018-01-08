# -*- coding: utf-8 -*-

"""
package: pylie
file   : methods

Library of basic LIE related methods
"""

import logging
import numpy
import itertools
import matplotlib.pyplot as plt

from scipy import stats
from matplotlib.patches import Ellipse
from pandas import DataFrame

logger = logging.getLogger('pylie')


def get_boltzmann_poses(df, tol=0.2, plot=False):
    p = df[df.get_columns('prob-*')].copy()
    p.index = df.case
    p.fillna(0, inplace=True)

    if plot:
        p.plot(kind='bar', stacked=True)
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        plt.savefig('boltzmann-weights.pdf')

    lowweight = []
    for idx, i in p.iterrows():
        vals = list(i.values)
        maxp = max(vals)
        for pose in [vals.index(y) + 1 for y in vals if maxp - tol < y <= maxp]:
            lowweight.append((int(idx), pose))

    return lowweight


def multivariate_gaussian(dataframe, confidence=0.975, returnellipse=False, **kwargs):
    """
    Perform multivariate Gaussian distribution outlier detection.

    Asses the fit of the multivariate dataset against a Gaussian distribution
    and calculate outliers as outside the confidence interval within the fitted
    Gaussian distribution.

    Optionally return an matplotlib Ellipse object representing the fitted
    confidance interval

    :param dataframe:     pandas DataFrame instance with multivariate data
    :type dataframe:      LIEDataFrame
    :param confidence:    the confidence interval to fit on, 0.975 by default
    :type confidence:     :py:float
    :param returnellipse: if to return matplotlib Ellipse object
    :type returnellipse:  :py:bool
    :param kwargs:        any additional keyword arguments will be passed to
                          Ellipse

    :return:              array of outliers (0 or 1), optional Ellipse object
    :rtype:               :numpy:array
    """

    # Check if there are Nan's in the dataframe. Remove if found, issue warning
    dataframe = dataframe.fillna(0)

    numpy_array = dataframe.values
    numpy_shape = numpy.shape(numpy_array)

    if numpy_shape[1] < 2:
        logger.error(
            "No multivariate Gaussian distribution outlier detection on dataset with less than two dimensions. ({0},{1})".format(
                *numpy_shape))
        return None, None

    # Estimate mu and sigma2 in the dataset
    mu = numpy_array.mean(axis=0)
    sigma2 = numpy.sum(numpy.square(numpy_array - mu), 0) / numpy_shape[0]

    # compute the confidence interval ellipse by calculating the quantile
    # (the inverse of the Cumulative Distribution Function) at every point
    # x of the chi-square distribution with n degrees of freedom.
    cov = numpy.cov(numpy_array, rowvar=False)
    A = numpy.linalg.inv(cov)
    b = stats.chi2.ppf(confidence, numpy_shape[1])

    # Find the outliers in data set.
    # An observation is an outlier if the condition d 2 < sigma is not
    # satisfied with sigma being a threshold drawn from a Chi-square
    # distribution.
    errors = numpy_array - mu
    outliers = numpy.diag(numpy.dot(numpy.dot(errors, A), numpy.transpose(errors))) > b

    if returnellipse and numpy_shape[1] == 2:

        vals, vecs = numpy.linalg.eigh(cov)
        order = vals.argsort()[::-1]
        vals, vecs = vals[order], vecs[:, order]
        theta = numpy.degrees(numpy.arctan2(*vecs[:, 0][::-1]))

        # Width and height are "full" widths, not radius
        width, height = 2 * numpy.sqrt(b) * numpy.sqrt(vals)
        ellipse = Ellipse(xy=mu, width=width, height=height, angle=theta, **kwargs)

        return outliers.astype(int), ellipse

    elif returnellipse and numpy_shape[1] > 1:
        logger.warning("Cannot create Ellipse for data with more than 2 dimensions")

    return outliers.astype(int), None


def hlinkage_to_treematrix(linkage_matrix):
    """
    Converts a hierarchical cluster linkage to a matrix representing the cluster
    tree

    The hierarchical clustering performed by the 'linkage' function returns an
    array representing the cluster tree as paires of nodes, the way they are
    connected with one another and the distance between them as calculated by the
    linkage method used.

    This functions converts the node based tree representation to a matrix form
    where each row represents a cluster element (case) and each column a node in
    the hierarchical tree going from the tree leafs (first column) to the trunk
    (last column)
    The matrix is an identity matrix where 1 signifies that case being present at
    the given node in the tree.

    @return DataFrame: Identity matrix
    """

    N = linkage_matrix.shape[0] + 1
    clusters = numpy.zeros((N, N - 1))

    # Assign single node branches
    cluster_list = numpy.arange(N, N + N - 1)
    linkage_matrix = numpy.column_stack((numpy.array(cluster_list).reshape(-1, 1), linkage_matrix))

    remove = []
    for idx, element in enumerate(cluster_list):
        nodes = [linkage_matrix[idx, 1].astype(int), linkage_matrix[idx, 2].astype(int)]

        # both nodes are leaf nodes
        if nodes[0] < N and nodes[1] < N:
            clusters[[nodes[0], nodes[1]], element - N] = 1
            remove.append(idx)

        # One of the nodes is a leaf node
        elif nodes[0] < N:
            clusters[nodes[0], element - N] = 1
        elif nodes[1] < N:
            clusters[nodes[1], element - N] = 1

    # Remove clusters made up of singletons from cluster list
    cluster_list = numpy.delete(cluster_list, remove)

    # Move up the tree, merging clusters
    while len(cluster_list) > 0:
        remove = []

        for i, element in enumerate(cluster_list):
            idx = numpy.where(linkage_matrix[:, 0] == element)[0][0]

            if idx:
                nodes = [linkage_matrix[idx, 1].astype(int), linkage_matrix[idx, 2].astype(int)]

                # Start merging nodes
                if nodes[0] < N and nodes[1] <= element:
                    clusters[:, element - N] = clusters[:, element - N] + clusters[:, nodes[1] - N]
                    remove.append(i)
                    break
                elif nodes[1] < N and nodes[0] <= element:
                    clusters[:, element - N] = clusters[:, element - N] + clusters[:, nodes[0] - N]
                    remove.append(i)
                    break
                elif nodes[0] <= element and nodes[1] <= element:
                    clusters[:, element - N] = clusters[:, nodes[1] - N] + clusters[:, nodes[0] - N]
                    remove.append(i)
                    break

        if len(remove):
            cluster_list = numpy.delete(cluster_list, remove)

    results = DataFrame(clusters)

    return results


def cv_set_partitioner(cases, cvtype='LOO', p=2, maxpartitions=200):
    """
    Creates test and train sets for cross-validation

    Given a list of observations, the function will create an identity matrix with
    different partitions of the input. A partition contains observations marked as
    training set (1) and validation set (0). Each column of the matrix is one
    partition. The number of columns is defined by the number of observations and
    the choosen partition method (cvtype). Supported methods are:

    LOO:  Leave-On-Out cross-validation. Exhaustive cross-validation in which all
          permutations of one observation as the validation set and the remaining
          observations as the training set are generated.
          Permutation combinations equals C\ :sup:`n` \ :sub: `1` \ = n where n
          equals the number of observations.
    LPO:  Leave-p-Out cross-validation. Exhausitive cross-validation in which p
          observations as the validation set and the remaining observations as the
          training set. This is repeated on all ways to cut the original sample on
          a validation set of p' observations and a training set.
          Permutation combinations equals C\ :sup:`n` \ :sub: `p` \ times where n
          equals the number of observations and p the partition count. With larger
          values of n this becomes impossible to calculateb efficiently. To
          prevent combinatorial explosions a maxpartitions count is enforces.
    RAND: Select random but unique subsets from the dataset with partition p and
          maxpartitions numer of times.
    KFOLD:

    :param cases:  List of observation ID's
    :ptype cases:  List or array of int's
    :param cvtype: Cross-validation method. Either LOO, LPO or KFOLD
    :ptype cvtype: string
    :param p:      Partition count or fraction for LPO cross-validation.
                   Set to 1 for LOO.
    :ptype p:      int or float
    :param maxpartitions: Maximum number of permutations returned to prevent
                   combinatorial explosions. Defaults to 200
    :ptype maxpartitions: int

    :return:       DataFrame with the partition identity matrix
    """

    nr = len(cases)
    if type(p) == float:
        assert 0 < p < 1, "Cross-validation partition fraction needs to be between 0 and 1"
        p = int(nr * p)
    elif type(p) == int:
        assert 0 < p < nr, "Cross-validation partition count needs to be between 0 and {0}. Got {1}".format(nr, p)
    else:
        p = 1

    # Leave one-out cross-validation (LOO)
    if cvtype in ('LOO', 'LPO'):
        if cvtype == 'LOO':
            p = 1
        permutations = [n for n in itertools.permutations(range(0, len(cases)), p)]
        perm_matrix = numpy.ones((nr, len(permutations)))
        for i, t in enumerate(permutations):
            perm_matrix[t, i] = 0
            if i == maxpartitions:
                logger.warn("maxpartitions ({0}) reached. Return current set only".format(maxpartitions))
                break

    if cvtype == 'KFOLD':

        assert 2 <= p < nr, "K-folds fold partition needs to be between 2 and {0}. Got {1}".format(nr, p)

        fold_sizes = (nr // p) * numpy.ones(p, dtype=numpy.int)
        fold_sizes[:nr % p] += 1
        perm_matrix = numpy.ones((nr, len(fold_sizes)))
        current = 0
        for i, fold_size in enumerate(fold_sizes):
            start, stop = current, current + fold_size
            perm_matrix[start:stop, i] = 0
            current = stop

    if cvtype == 'RAND':

        partitions = []
        case_id = range(nr)
        for n in range(maxpartitions):
            part = numpy.random.permutation(case_id)
            part = part.tolist()[0:p]
            if part not in partitions:
                partitions.append(part)

        perm_matrix = numpy.zeros((nr, len(partitions)))
        for i, partition in enumerate(partitions):
            perm_matrix[partition, i] = 1

    dataframe = DataFrame(perm_matrix)
    dataframe['case'] = cases

    return dataframe
