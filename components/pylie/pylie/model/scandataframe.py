# -*- coding: utf-8 -*-

import logging
import numpy

from pandas import DataFrame, Series, pivot_table
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import *
from matplotlib import pyplot

from ..methods.methods import hlinkage_to_treematrix
from ..plotting import plot_matrix
from .liedataframe import LIEDataFrame, lie_deltag
from .lieseries import LIESeries
from .liebase import LIEDataFrameBase

logger = logging.getLogger('pylie')

DEFAULT_SCAN_COLUMN_NAMES = {'case': 'case',
                             'poses': 'poses',
                             'alpha': 'alpha',
                             'beta': 'beta',
                             'gamma': 'gamma',
                             'vdw': 'vdw',
                             'coul': 'coul',
                             'dg_calc': 'dg_calc',
                             'ref_affinity': 'ref_affinity', }


class LIEScanDataFrame(LIEDataFrameBase):
    """
    Perform an alpha/beta grid scan for provided cases.

    This function will systematically scan alpha/beta parameter space.
    The range of values for alpha and beta can be set to arbitrary start, stop and
    step size values. the gamma parameter is set to a fixed value.
    By default, an alpha/beta range between 0 and 1 with a step size of 0.01 is
    sampled.

    NOTE: the default step size is set to 0.01. Be carefull with setting smaller
    step sizes in particular for larger datasets where the number of scan
    combinations may easily explode resulting in long calculation times.

    The function expects Pandas DataFrame or Series objects as input. As such, the
    scan can be performed on a single case (a Series) or multiple cases
    (a DataFrame) in wich the latter may be multiple cases single pose or multiple
    cases multiple poses.

    The scan results are returned as a LIEScanDataFrame with the calculated dG
    values for each alpha/beta scan combination (columns) for each case (rows).
    Columns headers are tuples of alpha/beta values.
    """

    _class_name = 'scan'
    _column_names = DEFAULT_SCAN_COLUMN_NAMES

    def __init__(self, *args, **kwargs):
        """
        Class __init__ method

        Check input data:
        - Needs to be of type Pandas DataFrame or Series and contain at least
          Van der Waals (vdw), Coulomb (coul) and Pose (poses) columns.

        Arguments
        ---------
        :param dataframe: 'vdw' and 'coul' data to perform the scan on.
        :ptype dataframe: LIEDataFrame
        :param max_combinations: Maximum number of alpha/beta parameter combinations
          that are allowed to be sampled. A safety measure to prevent long
          computation times.
        :ptype max_combinations: int, default 100000000.
        """

        super(LIEScanDataFrame, self).__init__(*args, **kwargs)

    def _init_custom_finalize(self, **kwargs):

        self._declare_scan_parameters()

    @property
    def _constructor(self):

        return LIEScanDataFrame

    def _pivot_data(self, column):
        """
        Create matrix of VdW and Coul values for every pose of every case.
        Use a pivot table to collect VdW and Coul values as matrix from a DataFrame.
        Make new (1,1) array for VdW and Coul values from a Series (only one pose).

        @params string column: DataFrame column name to create pivot table for

        @return Pivot table as new Pandas DataFrame
        """

        if type(self.data) == LIEDataFrame:
            pivot = pivot_table(self.data, values=column, index=['case'], columns=['poses'])
        else:
            pivot = numpy.array([[self.data[column]]])

        return pivot

    def _declare_scan_parameters(self, alpha=None, beta=None, gamma=None):
        """
        Calculates the scan arguments required by the scan function.
        """

        if alpha is not None:
            self.alpha_scan_range = numpy.arange(*alpha)
            self.Sa = self.alpha_scan_range.size
            logger.info("Alpha parameter scan in range: {0} to {1}, step size {2}".format(*alpha))
        if beta is not None:
            self.beta_scan_range = numpy.arange(*beta)
            self.Sb = self.beta_scan_range.size
            logger.info("Beta parameter scan in range: {0} to {1}, step size {2}".format(*beta))

        if self.empty:
            cases = self.data.cases
        else:
            cases = self.cases

        if cases:
            self.N = len(cases)
            self.R = (self.Sa * self.Sb) * self.N

            if gamma is not None:
                self.gamma_scan_range = numpy.array([gamma] * self.R)
                logger.info("Gamma parameter: value fixed to {0}".format(gamma))

            # Check if total number of scan points does not exceed max_combinations
            if self.R > self.settings['max_combinations']:
                logger.error("Number of scan points ({0}) exceeds max_combinations ({1})\
            This is a safety threshold to prevent long computation times. Adjust with caution".format(self.R,
                self.settings['max_combinations']))
                return False

            # Report
            logger.info("Alpha/Beta parameter scan for {0} cases with a maximum of {1} poses".format(self.N,
                self.v_vdw.shape[1]))
            logger.info("Alpha/Beta parameter scan for cases: {0}".format(str(cases).strip('[]')))

        return True

    def _calc_similarity_matrix(self):

        # Extract column with calculated delta G values from the scandataframe and
        # reshape to form a matrix with cases for rows and columns for each scan
        # (alpha/beta) parameter combination.
        dgcalc = self['dg_calc'].values
        dgcalc = dgcalc.reshape((self.Sa * self.Sb, self.N))

        # Calculate pairwise distance matrix for each column using a given metric
        return pdist(dgcalc.T, metric=self.settings['pdist_metric'])

    def _filter_by_similarity(self, cutoff=0.75):
        # Calculate correlation variance for each ligand with respect to all
        # other ligands.

        simmatrix = 1 - squareform(self._calc_similarity_matrix())
        mean = numpy.mean(simmatrix, axis=0)
        std = numpy.std(simmatrix, axis=0)
        cases = self.cases
        outlier = [1 if c <= cutoff else 0 for c in mean]

        logger.info("Identified {0} outliers in a {1} based similarity matrix with a cutoff of {2}".format(sum(outlier),
            self.settings['pdist_metric'], cutoff))

        return DataFrame({'case': cases, 'mean': mean, 'std': std, 'filter_mask': outlier})

    @property
    def outliers(self):
        self.settings.pdist_metric = 'correlation'
        resultsframe = self._filter_by_similarity(cutoff=self.settings['outlier_cutoff'])
        self.settings.revert('pdist_metric')

        return resultsframe[resultsframe['filter_mask'] > 0]

    @property
    def inliers(self):
        self.settings.pdist_metric = 'correlation'
        resultsframe = self._filter_by_similarity(cutoff=self.settings['inlier_cutoff'])
        self.settings.revert('pdist_metric')

        return resultsframe[resultsframe['filter_mask'] == 0]

    def cluster(self, **kwargs):
        """
        Case wise clustering based on Alpha/Beta scan results

        :param cluster_method  method to use for clustering. Default is 'optimal' using the optimal alpha/beta
                               value for each case as cluster criteria. 'full' cluster on the full scan matrix
                               for each case or cluster on the optimal alpha/beta parameter values for each case.
                               'vector' cluster using on the vectors defined by the range of optimal alpha/beta
                               values for each case.
        :param pdist_metric:   metric to use for pairwise distance measurement. See SciPy documentation on
                               scipy.spatial.distance.pdist for more information on the supported metrics.
        :ptype pdist_metric:   string
        :param linkage_method: method to use for hierarchical/agglomerative clustering. See SciPy documentation
                               on scipy.cluster.hierarchy.linkage for more information on the supported methods.
        :ptype linkage_method: string
        :param linkage metric: metric to use for hierarchical/agglomerative clustering. See SciPy documentation
                               on scipy.cluster.hierarchy.linkage for more information on the supported methods.
        :ptype linkage_metric: string
        """

        self.settings.update(kwargs)

        if self.settings['cluster_method'] == 'full':
            simmatrix = self._calc_similarity_matrix(**kwargs)
            logger.info(
                'Cluster scan results using full scan matrix. pdist metric: {0}, linkage method: {1}, linkage metric: {2}'.format(
                    self.settings['pdist_metric'], self.settings['linkage_method'], self.settings['linkage_metric']))
        elif self.settings['cluster_method'] == 'vector':
            df = self.get_optimal_range()
            vectors = df[['ha', 'hb']].values - df[['la', 'lb']].values
            simmatrix = pdist(vectors, metric=self.settings['pdist_metric'])
            logger.info(
                'Cluster scan results using vectors. pdist metric: {0}, linkage method: {1}, linkage metric: {2}'.format(
                    self.settings['pdist_metric'], self.settings['linkage_method'], self.settings['linkage_metric']))
        else:
            optimal_params = self.get_optimal()
            simmatrix = pdist(optimal_params, metric=self.settings['pdist_metric'])
            logger.info(
                'Cluster scan results using optimal alpha/beta parameters. pdist metric: {0}, linkage method: {1}, linkage metric: {2}'.format(
                    self.settings['pdist_metric'], self.settings['linkage_method'], self.settings['linkage_metric']))

        tree = linkage(simmatrix, self.settings['linkage_method'], self.settings['linkage_metric'])
        dataframe = hlinkage_to_treematrix(tree)
        dataframe['case'] = self.cases

        if kwargs.get('return_all', False):
            return dataframe, simmatrix, tree

        return dataframe

    def get_optimal_range(self, column='error'):

        matrix = self.get_matrix(column=column)

        cases = []
        optimal = []
        lowa = []
        lowb = []
        higha = []
        highb = []
        for i, case in enumerate(matrix.index):
            opt_idx = (numpy.abs(matrix.iloc[i, :].values)).argmin()
            opt = matrix.iloc[i, opt_idx]
            one_dec = numpy.round(opt, 1)

            r = matrix.iloc[i, :]
            r = r[(r > one_dec - 0.1) & (r < one_dec + 0.1)].reset_index()

            low_ab = r.head(1).values[0]
            high_ab = r.tail(1).values[0]

            cases.append(case)
            optimal.append(opt)
            lowa.append(low_ab[0])
            lowb.append(low_ab[1])
            higha.append(high_ab[0])
            highb.append(high_ab[1])

        df = DataFrame({'case': cases, 'optimal': optimal, 'la': lowa, 'lb': lowb, 'ha': higha, 'hb': highb})
        return df

    def get_optimal(self, column='error'):
        """
        Get optimal alpha and beta value for each case

        For each case find the dG RMSE value closest to 0 and return RMSe, alpha
        and beta value als Pandas DataFrame

        :param column: column name for which to return values close to 0
        :type column:  :py:str
        :return:       Pandas DataFrame
        """

        matrix = self.get_matrix(column=column)
        optimal_idx = (numpy.abs(matrix.values)).argmin(1)
        dataframe = {column: [], 'alpha': [], 'beta': []}

        for case, idx in enumerate(optimal_idx):
            dataframe[column].append(matrix.iloc[case, idx])
            dataframe['alpha'].append(matrix.columns[idx][0])
            dataframe['beta'].append(matrix.columns[idx][1])

        # Gather results in new Pandas DataFrame.
        results = DataFrame(dataframe, index=set(self['case']))
        results.index.name = 'case'

        return results

    def get_density(self, **kwargs):
        """
        Reformat the DataFrame as a alpha/beta matrix with the number of cases
        having a calculated dG within a certain range as cell values

        :param ltol: Lower tolerance cutoff. May be used as mask in plot
                           creation to only focus on scan results with values higher
                           than or equal to cutoff. Default not defined.
        :ptype ltol: float
        :param utol: Upper tolerance cutoff. May be used as mask in plot
                           creation to only focus on scan results with values lower
                           than or equal to cutoff. Default not defined.
        :ptype utol: float
        :param absolute: Treat dG error values as absolute errors.
        :ptype absolute: bool
        :return:     pandas DataFrame
        """

        # Reshape in (N,Sa*Sb) matrix
        data = self['error'].values.reshape(self.Sa * self.Sb, self.N)
        if kwargs.get('absolute', False):
            data = numpy.absolute(dGdiff)

        # Set upper and lower tolerance limit if not set. Use cutoff of 5% between
        # minimum and maximum value in dataet
        ltol = kwargs.get('ltol', numpy.min(data) * 0.05)
        utol = kwargs.get('utol', numpy.max(data) * 0.05)

        # Make new matrix of size (alpha range x beta range) and add reshaped
        # identity matrixes for each case. Identity matrix is determined as 1 for
        # all cases with gamma residual in range ltol <= x <= utol, and 0 outside.
        identmatr = ((data >= ltol) & (data <= utol)).astype(int)
        ident_matrix_cases = identmatr * numpy.arange(1, self.N + 1).reshape(1, self.N)
        scanmatrix = numpy.zeros((self.Sa, self.Sb))
        for i in range(1, self.N + 1):
            scanmatrix = scanmatrix + numpy.sum((ident_matrix_cases == i).astype(int), axis=1).reshape(self.Sa, self.Sb)

        # Wrap scanmatrix in a Pandas DataFrame. Flip it up first to have both parameters start as 0 origin
        df = DataFrame(numpy.flipud(scanmatrix))
        df.columns = self.beta_scan_range
        df.index = self.alpha_scan_range

        return df

    def get_cases(self, alpha, beta, error=5):
        """
        Get cases in alpha/beta range lower than error.

        The method returns every case that matches the error cutoff in the
        matrix defined by the parameter range. This likely contains duplicates.
        Use set to get the unique case IDs or a counter or histogram function
        to get information on the frequency of occurrence for each case.

        :param alpha: Alpha parameter range (start,stop)
        :ptype alpha: :py:list
        :param beta:  Beta parameter range (start,stop)
        :ptype beta:  :py:list
        :param error: Absolute error cutoff
        :ptype error: :py:float

        :rtype:       :py:list
        """

        cases = self[(self['alpha'] > alpha[0]) & (self['alpha'] < alpha[1]) & (self['beta'] > beta[0]) &
                     (self['beta'] < beta[1]) & (abs(self['error']) < error)]
        return list(cases['case'].values)

    def propensity_distribution(self, min_density_frac=0.5):
        """
        Pose tagging:
          - 0: Contribution of this pose to the Boltzmann weighting is less then 5%. It's tagged as
               being insignificant unless 'prob_report_insignif' equals false, then report as 3.
          - 1: The Boltzmann weight of this pose is descending in alpha/beta space
          - 2: The Boltzmann weight of this pose is ascending in alpha/beta space
          - 3: The Boltzmann weight of this pose remains stable in alpha/beta space
        """

        probstats = DataFrame(columns=['case', 'pose', 'tag', 'min', 'max', 'mean', 'slope', 'total', 'overlap'])

        insignificant = self.settings.prob_insignif_cutoff
        optima = self.get_optimal()
        idx = 0
        for case, data in optima.sort_index().iterrows():

            optimum = abs(data['error'])
            if optimum == 0.0:
                search = 0.0
            else:
                search = (round(optimum, -int(numpy.floor(numpy.log10(optimum)))) + 0.1)

            selection = self.loc[(abs(self['error']) < search) & (self['case'] == case)]
            selection = selection.dropna(how='all', axis=1)

            columns = selection.get_columns('prob-*')
            stats = selection[selection.get_columns('prob-*')].describe()
            for prob in columns:
                p = stats[prob]
                slope = numpy.mean(numpy.gradient(selection[prob].values))

                # Insignificant pose
                if p['mean'] < insignificant and p['25%'] < insignificant and p['50%'] < insignificant and p[
                    '75%'] < insignificant:
                    tag = 3
                    if self.settings.prob_report_insignif:
                        tag = 0

                # Descending gradient
                elif (p['max'] - p['min']) > 0.1 and slope < self.settings.grad_desc_cutoff:
                    tag = 1

                # Ascending gradient
                elif (p['max'] - p['min']) > 0.1 and slope > self.settings.grad_ascn_cutoff:
                    tag = 2

                # Pose near constant
                else:
                    tag = 3

                pose_data = Series({'case': case,
                                    'pose': int(prob.split('-')[1]),
                                    'tag': tag,
                                    'min': p['min'],
                                    'max': p['max'],
                                    'mean': p['mean'],
                                    'slope': slope})
                probstats.loc[idx] = pose_data
                idx += 1

        # Get the density distribution for the scan and normalize
        density = self.get_density()
        maxval = max(density.values.flatten())
        density_norm = density / maxval

        # Select all grid points with a normalized fraction >= min_density_frac
        scanabrange = density_norm[density_norm >= min_density_frac]
        scanabrange = (scanabrange.fillna(0) != 0).astype(int)

        # Get number of grid points with value 1
        abgridcount = scanabrange.stack().value_counts()
        abdatapoints = float(abgridcount[1])

        for case in probstats['case'].unique():
            p = self[self['case'] == case]
            for i in p.get_columns('prob-*'):
                f = numpy.flipud(p[i].values.reshape(self.Sa, self.Sb))
                if not numpy.isnan(f.sum()):
                    pose = int(i.split('-')[-1])
                    f = DataFrame(f)
                    cutoff = f[f >= 0.1].fillna(0)
                    cutoff = (cutoff != 0).astype(int)

                    # Determine overlap propensity matrix and scanabrange
                    overlap = DataFrame(cutoff.values + scanabrange.values)
                    gridcount = overlap.stack().value_counts()

                    if 2 in gridcount.index.values:
                        totalcount = gridcount[1] + gridcount[2]
                        overlapcount = gridcount[2] / abdatapoints
                    else:
                        totalcount = gridcount[1]
                        overlapcount = 0

                    probstats.loc[(probstats['case'] == case) & (probstats['pose'] == pose), 'total'] = totalcount
                    probstats.loc[(probstats['case'] == case) & (probstats['pose'] == pose), 'overlap'] = overlapcount

        return probstats

    def get_matrix(self, column='dg_calc'):
        """
        Reformat the DataFrame with cases as rows and alpha/beta scan combinations
        as columns.

        :param column: LIEScanDataFrame column name to reformat the data for.
                       dg_calc by default.
        :ptype column: string
        """

        if column in self.columns:
            results = DataFrame(numpy.transpose(self[column].values.reshape(self.Sa * self.Sb, self.N)),
                                index=set(self['case']),
                                columns=[self.alpha_scan_range.repeat(self.Smin[0]),
                                         numpy.tile(self.beta_scan_range, self.Smin[1])])
            results.index.name = 'case'

            return results
        else:
            raise KeyError("no such column name: {0}".format(column))

    def plot(self, *args, **kwargs):
        """
        Support a number of class specific plot 'kinds'.
        If not requested refer to base class plot function
        """

        kind = kwargs.get('kind', None)
        if kind == 'simmatrix':
            kwargs.pop('kind')
            df, simmatrix, tree = self.cluster(return_all=True)
            return plot_matrix(squareform(simmatrix), yaxis=self['case'], xaxis=self['case'], ylabel='cases',
                               xlabel='cases', interpolation=None, *args, **kwargs)

        elif kind == 'dendrogram':
            kwargs.pop('kind')
            df, simmatrix, tree = self.cluster(return_all=True)

            fig = pyplot.figure()
            ax = fig.add_subplot(1, 1, 1)
            ax.grid(None)
            dendrogram(tree, ax=ax)
            return fig

        elif kind == 'vector':
            opt = self.get_optimal_range()
            fig = pyplot.figure()
            ax = fig.add_subplot(1, 1, 1)
            ax.quiver(opt['lb'], opt['la'], opt['hb'], opt['ha'], angles='xy', scale_units='xy', scale=1, color='r')
            ax.set_ylim([self.alpha_scan_range[0], self.alpha_scan_range[1]])
            ax.set_xlim([self.beta_scan_range[0], self.beta_scan_range[1]])
            pyplot.draw()
            return fig

        else:
            return super(LIEScanDataFrame, self).plot(*args, **kwargs)

    def scan(self, dataframe, **kwargs):
        """
        Runs the alpha/beta scan calculation

        :param dataframe: The dataframe with Van der Waals and Coulomb data used as
                          input for the scan calculation
        :ptype dataframe: LIEdataFrame or LIESeries
        :param alpha:     Alpha scan range parameters as list with start, stop and
                          step size values. Default [0,1,0.01].
        :ptype alpha:     list
        :param beta:      Beta scan range parameters as list with start, stop and
                          step size values. Default [0,1,0.01].
        :ptype beta:      list
        :param gamma:     Gamma value to use. Default = 0
        :ptype gamma:     float
        :param kBt:       Boltzmann constant at given temperature. Default = 2.49
        :ptype kBt:       float
        """

        # Update class settings from kwargs dict
        self.settings.update(kwargs, strict=True)

        if not type(dataframe) in (LIEDataFrame, LIESeries):
            logger.error("Input dataformat needs to be of Pandas DataFrame or Series type. Got {0}".format(type(dataframe)))
            return None

        required_columns = set([self._column_names[k] for k in ('vdw', 'coul', 'poses', 'ref_affinity')])
        if set(dataframe.columns.values).intersection(required_columns) != required_columns:
            logger.error("Input DataFrame missing required columns: {0}".format(
                ",".join(list(required_columns.difference(dataframe.columns.values)))))
            return None

        # Register dataframe and create pivot tables for vdw, coul and reference
        # affinity data, update settings
        self.settings.update(kwargs)
        self.data = dataframe
        self.v_vdw = self._pivot_data(self._column_names['vdw'])
        self.v_coul = self._pivot_data(self._column_names['coul'])
        self.ref = self._pivot_data(self._column_names['ref_affinity']).mean(axis=1).values

        # Calculate matrix and vector size parameters
        if not self._declare_scan_parameters(self.settings['alpha'], self.settings['beta'], self.settings['gamma']):
            return None

        # Create vector of alpha values.
        # First determine alpha/beta vector multiplication factor to deal with
        # non-square matrices (larger alpha then beta scan-range or vice-versa).
        self.Smin = sorted([self.Sa, self.Sb])
        if self.Sa == self.Smin[0]:
            self.Smin = sorted(self.Smin, reverse=True)

        # Multiply vector of VdW and Coul components Sa*Sb number of times
        vdw_mult = numpy.tile(self.v_vdw, (self.Sa * self.Sb, 1))
        coul_mult = numpy.tile(self.v_coul, (self.Sa * self.Sb, 1))
        ref_mult = numpy.tile(self.ref, self.Sa * self.Sb)

        # Calculate dG values. Returns DataFrame
        # Alpha: Every value in scan_range vector repeated N*Smin[0] times.
        # Beta:  Full scan_range vector repeated Smin[1] times, every value in
        #        vector repeated N times.
        # Gamma: All equal to initial guess repeated R times
        dg_calc = lie_deltag([vdw_mult, coul_mult],
                             params=[self.alpha_scan_range.repeat(self.N * self.Smin[0]),
                                     numpy.tile(self.beta_scan_range.repeat(self.N), self.Smin[1]),
                                     self.gamma_scan_range], kBt=self.settings['kBt'])

        self[self._column_names['case']] = numpy.tile(self.data.cases, self.Sa * self.Sb)

        # Copy only the values of the dg_calc DataFrame columns to self to avoid
        # misaligned indexes. We do assume equal length columns though but that
        # should be valid.
        for column in dg_calc.columns:
            self[column] = dg_calc[column].values
        self['ref_affinity'] = ref_mult
        self['vdw'] = vdw_mult
        self['coul'] = coul_mult

        # Calculate delta-dG values
        self['error'] = self['dg_calc'] - ref_mult
