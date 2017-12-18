# -*- coding: utf-8 -*-

import numpy
import itertools

from twisted.logger import Logger
from scipy.spatial.distance import squareform
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram


def coords_from_mol2(mol2_files):
    """
    Extract XYZ coordinates from a mol2 file

    :param mol2_files: mol2 file paths to import
    :type mol2_files:  list
    :return:           coordinates as list of numpy arrays
    """

    sets = []
    for mol2 in mol2_files:

        with open(mol2, 'r') as structure_file:
            read = False
            coords = []
            for line in structure_file.readlines():
                line = line.strip()
                if line.endswith('ATOM'):
                    read = True
                elif line.endswith('BOND'):
                    break
                elif read:
                    line = line.split()
                    coords.append(map(float, line[2:5]))
            if coords:
                sets.append(coords)

    return numpy.array(sets)


def _rotate(c1, c2):
    """
    Rotate matrix c1 onto matrix c2 using Kabsch algorithm
    """
    rotated = _kabsch(c1, c2)

    # Rotate c1
    c1 = numpy.dot(c1, rotated)
    return c1


def _centroid(X):
    """
    Calculate the centroid from a vectorset X
    """
    C = sum(X) / len(X)
    return C


def _kabsch(P, Q):
    """
    The optimal rotation matrix U is calculated and then used to rotate matrix
    P unto matrix Q so the minimum root-mean-square deviation (RMSD) can be
    calculated.

    Using the Kabsch algorithm with two sets of paired point P and Q,
    centered around the center-of-mass. Each vector set is represented as
    an NxD matrix, where D is the the dimension of the space.

    The algorithm works in three steps:
        * A translation of P and Q
        * The computation of a covariance matrix C
        * Computation of the optimal rotation matrix U

    http://en.wikipedia.org/wiki/Kabsch_algorithm

    :param P: (N, number of points)x(D, dimension) matrix
    :param Q: (N, number of points)x(D, dimension) matrix
    :return: U the Rotation matrix
    :rtype: object
    """

    # Computation of the covariance matrix
    C = numpy.dot(numpy.transpose(P), Q)

     # Computation of the optimal rotation matrix
    # This can be done using singular value decomposition (SVD)
    # Getting the sign of the det(V)*(W) to decide
    # whether we need to correct our rotation matrix to ensure a
    # right-handed coordinate system.
    # And finally calculating the optimal rotation matrix U
    # see http://en.wikipedia.org/wiki/Kabsch_algorithm
    V, S, W = numpy.linalg.svd(C)
    d = (numpy.linalg.det(V) * numpy.linalg.det(W)) < 0.0

    if d:
        S[-1] = -S[-1]
        V[:, -1] = -V[:, -1]

    # Create Rotation matrix U
    U = numpy.dot(V, W)

    return U


def rmsd(c1, c2):

    delta = c1 - c2
    delta_sq = delta * delta
    return numpy.sqrt(delta_sq.sum() / len(c1))


def kabsch(c1, c2):
    """
    Rotate matrix c1 onto c2 and calculate the RMSD
    """

    c1 -= _centroid(c1)
    c2 -= _centroid(c2)

    c1 = _rotate(c1, c2)
    return rmsd(c1, c2)


class ClusterStructures(object):
    """
    Cluster analysis on sets of structures that are identical in atom count,
    atom type and atom order such as docking poses.

    The class works on plain sets of coordinates and thereby assumes that
    the above mentioned atom constraints are satisfied.
    A calculated pairwise distance matrix (**pdist**) is used as similarity measure
    in a hierarchical clustering analysis.

    Supported metrics of the **pdist** are:

        * **rmsd**:
          plane Root Mean Square Deviation between two coordinate
          sets without fitting.
        * **kabsch**:
          first fit the two coordinates set before calculating the
          RMSD value. Minimize the Root Mean Square Deviation
          between the two coordinate sets by calculating the
          optimal rotation matrix.

          This uses the Kabsch algorithm:

          * https://en.wikipedia.org/wiki/Kabsch_algorithm

    The **pdist** is calculated once at class construction and is reused to
    calculate different cluster flavors using the class `cluster` method.

    :param xyz:    structure xyz coordinate sets
    :type xyz:     list of numpy.ndarray's
    :param metric: one of the supported distance metrics
    :type metric:  str
    :param labels: structure identifiers such as docking pose ID's
                   corresponding to the entries in the coordinate set.
    :type labels:  list
    """

    logging = Logger()

    def __init__(self, xyz, metric='rmsd', labels=None):

        self.xyz = xyz
        self.metric = metric
        self.labels = labels or range(len(labels))

        # All xyz coordinate sets need to be of type numpy.ndarray
        print("XYZ: ", self.xyz)
        cond = all([isinstance(coords, numpy.ndarray) for coords in self.xyz])
        assert cond, 'Structure coordinates need to be of type numpy.ndarray'

        # Equality in number and order of atoms for all coordinate sets is assumed
        print("Coordinates: ", self.xyz)
        cond = len(set([coords.size for coords in self.xyz])) == 1
        assert cond, 'Structure coordinates have an unequal number of atoms'

        # Optional list of labels (e.a. structure id's) need to match coordinate set in length
        cond = len(self.labels) == len(self.xyz)
        assert cond, 'Number if labels is not matching number of coordinate sets'

        self._condensed_distance_matrix = self._build_pdist()
        self._clusters = []
        self._clusters_filtered = {}

    def __len__(self):
        """
        Return the number of clustered structures
        """

        len(self._clusters)

    def __str__(self):
        """
        Return a nicely formatted summary of the clustering
        """

        summary = []
        summary.append('Clustering {0} structures'.format(len(self.xyz)))
        summary.append('Metric for pairwise distance matrix: {0}'.format(self.metric))
        summary.append('Metric for hierarchical clustering: {0}'.format(self.method))
        summary.append('Cluster selection criterion: {0} with parameter {1}\n'.format(self.criterion, self.t))

        summary.append('Clusters: {0}, coverage: {1:.2f}%'.format(self.cluster_count, self.coverage * 100))

        return '\n'.join(summary)

    def _build_pdist(self):
        """
        Construct condensed pairwise distance matrix using the `metric`
        defined in the class constructor

        :return:       condensed distance matrix
        :rtype:        list
        """

        _metric_func = globals().get(self.metric)
        if not _metric_func:
            raise LookupError(
                '{0} class does not know about "{1}" pdist metric'.format(type(self).__name__, self.metric))

        dst = []
        for pair in itertools.combinations(self.xyz, 2):
            dst.append(_metric_func(*pair))

        return dst

    @property
    def clustered_structures(self):
        """
        For all structures that have been assigned to a cluster,
        return the cluster ID's

        :rtype: list
        """

        return [sid for sid in self._clusters_filtered if self._clusters_filtered[sid].get('cluster', 0) != 0]

    @property
    def cluster_medians(self):
        """
        Return ID's for structures that are representative for the
        cluster center determined as the structure for which the
        similarity distance metric is closest to the average of the
        given cluster.

        :return: dictionary of cluster ID/structure ID key/value pairs
        :rtype:  :py:class:`dict`
        """

        return {self._clusters_filtered[sid]['cluster']: sid for sid
                in self._clusters_filtered
                if self._clusters_filtered[sid].get('mean', False)}

    @property
    def cluster_count(self):

        return len(self.cluster_medians)

    @property
    def coverage(self):
        """
        Cluster coverage as the fraction of structures assigned to a cluster

        :rtype: float
        """

        return (len(self.clustered_structures) / float(len(self.xyz)))

    def plot(self, to_file='cluster_dendrogram.pdf'):
        """
        Plot the cluster dendrogram.
        """

        fig = plt.figure()

        ddata = dendrogram(self._linkage,
                           labels=self.labels,
                           color_threshold=self._linkage[-(max(self._clusters) - 1), 2])
        annotate_above = 1
        for i, d, c in zip(ddata['icoord'], ddata['dcoord'], ddata['color_list']):
            x = 0.5 * sum(i[1:3])
            y = d[1]
            if y > annotate_above:
                plt.plot(x, y, 'o', c=c)
                plt.annotate("%.3g" % y, (x, y), xytext=(0, -5),
                             textcoords='offset points',
                             va='top', ha='center')
        max_d = None
        if max_d:
            fig.axhline(y=max_d, c='k')

        if not to_file:
            return fig

        fig.savefig(to_file)

    def cluster(
            self, t=5, method='single', criterion='distance', min_cluster_count=1):
        """
        Cluster the structures using hierarchical clustering methods on
        the calculated pairwise distance matrix.

        The selected number of clusters

        :param method:            hierarchical clustering methods as defined in
                                  the scipy.cluster.hierarchy.linkage method.
                                  Options are: single, complete, average, weighted,
                                  centroid, median and ward.
        :type method:             str
        :param criterion:         method to use for flattening clusters from the
                                  hierarchical clustering as defined in the
                                  scipy.cluster.hierarchy.fcluster method.
                                  Options are: inconsistent, distance, maxclust
                                  monocrit and maxclust_monocrit. t is used as
                                  threshold for each of these methods
        :type criterion:          str
        :param min_cluster_count: minimal number of structures in a cluster
        :type min_cluster_count:  int

        :return:                  clustering results
        :rtype:                   :py:class:`dict`
        """

        self.method = method
        self.criterion = criterion
        self.t = t

        self._linkage = linkage(self._condensed_distance_matrix, method=method)
        self._clusters = fcluster(self._linkage, t, criterion=criterion)

        self._clusters_filtered = {}
        sqmatr = squareform(self._condensed_distance_matrix)
        for n in range(1, max(self._clusters) + 1):
            cl = numpy.where(self._clusters == n)
            if len(cl[0]) >= min_cluster_count:

                # Get one structure as representative of the cluster
                if len(cl[0]) == 1:
                    lc = [0]
                else:
                    a = sqmatr[cl[0]]
                    a = a[:, cl[0]]
                    m = numpy.mean(numpy.hstack(a[i][:i] for i in xrange(a.shape[0])))
                    x = (numpy.abs(a - m)).argmin()
                    lc = numpy.where(a == a.flat[x])[0]

                meanpose = self.labels[cl[0][lc[0]]]
                for idx in cl[0]:
                    self._clusters_filtered[self.labels[idx]] = {'cluster': n, 'mean': self.labels[idx] == meanpose}
            else:
                self.logging.debug('Cluster {0} contains less that {1} structures ({2}). Dropping'.format(n, min_cluster_count, len(cl[0])))
                for idx in cl[0]:
                    self._clusters_filtered[self.labels[idx]] = {'cluster': 0, 'mean': 0}

        self.logging.info('Cluster {0} structures. pdist method: {1}, cluster method: {2}, criterion: {3}, tolerance: {4}, minimum cluster size: {5}'.format(
            len(self.xyz), self.metric, self.method, self.criterion, self.t, min_cluster_count))
        self.logging.info('Resolved {0} clusters with a coverage of {1}%'.format(self.cluster_count, self.coverage * 100))
        return self._clusters_filtered
