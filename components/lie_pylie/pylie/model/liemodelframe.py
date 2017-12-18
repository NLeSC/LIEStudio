# -*- coding: utf-8 -*-

import logging
import numpy

from numpy.random import choice
from collections import defaultdict
from pandas import DataFrame, Series, pivot_table, isnull
from statsmodels import api as sm
from sklearn import mixture

from ..methods.methods import cv_set_partitioner
from ..methods.stats import *
from .liebase import LIEDataFrameBase
from .liedataframe import LIEDataFrame, lie_deltag

logger = logging.getLogger('pylie')

GREEK_ALPHABET = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 'theta', 'iota', 'kappa',
                  'lambda', 'mu', 'nu', 'xi', 'omicron', 'pi', 'rho', 'sigma', 'tau', 'upsilon', 'phi',
                  'chi', 'psi', 'omega']

DEFAULT_MODEL_COLUMN_NAMES = {'L0': 'L0',
                              'L1': 'L1',
                              'iteration': 'iteration',
                              'set': 'set',
                              'N': 'N',
                              'fit': 'fit',
                              'rmsd': 'rmsd',
                              'rsquared': 'rsquared',
                              'regressor': 'regressor',
                              'filter_mask': 'filter_mask',
                              'converge': 'converge'}


class OLSregression(object):
    rmodeltype = 'OLS'

    def __init__(self, **kwargs):
        self.rmodelparams = kwargs
        self.model = None

    def set(self, endog, exog=None):
        self.model = sm.OLS(endog, exog=exog, **self.rmodelparams)

    def fit(self):
        return self.model.fit()


class GLSregression(object):
    rmodeltype = 'GLS'

    def __init__(self, **kwargs):
        self.rmodelparams = kwargs
        self.model = None

    def set(self, endog, exog=None):
        self.model = sm.GLS(endog, exog=exog, **self.rmodelparams)

    def fit(self):
        return self.model.fit()


class WLSregression(object):
    rmodeltype = 'WLS'

    def __init__(self, **kwargs):
        self.rmodelparams = kwargs
        self.model = None

    def set(self, endog, exog=None):
        self.model = sm.WLS(endog, exog=exog, **self.rmodelparams)

    def fit(self):
        return self.model.fit()


class GLSARregression(object):
    rmodeltype = 'GLSAR'

    def __init__(self, **kwargs):
        self.rmodelparams = kwargs
        self.model = None

    def set(self, endog, exog=None):
        self.model = sm.GLSAR(endog, exog=exog, **self.rmodelparams)

    def fit(self):
        return self.model.fit()


class QRregression(object):
    rmodeltype = 'QR'

    def __init__(self, **kwargs):
        self.rmodelparams = kwargs
        self.model = None

    def set(self, endog, exog=None):
        self.model = sm.QR(endog, exog=exog, **self.rmodelparams)

    def fit(self):
        return self.model.fit()


class RLMregression(object):
    rmodeltype = 'RLM'

    def __init__(self, norm='AndrewWave', **kwargs):
        self.rmodelparams = kwargs
        self.model = None
        self.norm = norm
        if type(norm) == str:
            self.norm = getattr(sm.robust.norms, norm, None)
            assert self.norm is not None, "No valid M-estimator of type {0} available".format(norm)

    def set(self, endog, exog=None):
        self.model = sm.RLM(endog, exog=exog, M=self.norm(), **self.rmodelparams)

    def fit(self):
        return self.model.fit()


REGRESS_METHODS = {
    'OLS': OLSregression,
    'GLS': GLSregression,
    'WLS': WLSregression,
    'GLSAR': GLSARregression,
    'QR': QRregression,
    'RLM': RLMregression
}


class LIEModelFrame(LIEDataFrameBase):
    _class_name = 'model'

    def __init__(self, *args, **kwargs):

        super(LIEModelFrame, self).__init__(*args, **kwargs)

    def __getattr__(self, key):

        if 'model' in self._metadata and hasattr(self._metadata['model'], key):
            return getattr(self._metadata['model'], key)

        return super(LIEModelFrame, self).__getattr__(key)

    def __getitem__(self, key):

        result = super(LIEModelFrame, self).__getitem__(key)

        return result

    @property
    def _constructor(self):

        return LIEModelFrame

    def crossvalidate(self, cvtype='LOO', p=1, maxpartitions=200):

        # Current trainset
        trainset = self.trainset.cases

        # Create a copy of the original dataset
        dfcopy = self.source.copy()
        dfcopy.trainset = trainset

        # Get default parameter set
        def_params = [0.5] * len(self.model.params)
        if len(def_params) > 2:
            def_params[-1] = 0

        # Create Cross-validation partition table
        cvmatrix = cv_set_partitioner(trainset, cvtype=cvtype, p=p, maxpartitions=maxpartitions)

        # Run a new batch modelling using the cross-validation matrix as input
        cmodel = LIEModelBuilder(dataframe=dfcopy)
        cmodel.batchmodel(cvmatrix, rmodel=REGRESS_METHODS[self.rmodel](), usefilter=False, def_params=def_params)

        # Collect cross-validated deltaG values
        response = self.trainset['ref_affinity'].values
        test_observed = []
        for i, index in enumerate(cmodel.inliers.index):
            testset = cvmatrix[cvmatrix[i] == 0]['case']
            m = cmodel.getmodel(index)
            test_observed.extend(m.get_cases(testset.values)['dg_calc'].values)

        if len(test_observed) == len(response):
            stats = {'n': len(trainset), 'p': p, 'cvtype': cvtype, 'sdep': sdep(response, test_observed),
                     'q2': qsquared(response, test_observed)}
            cmodel._metadata.update(stats)

        return cmodel

    def fitstats_to_table(self):
        # Set the residual weights. Default to 1 for non-weighted regression methods
        # Check for a 'weights' attribute in the regression results. If found, set
        # weights for the training set to regression results weights
        self['weights'] = 1
        if 'model' in self._metadata:
            weights = getattr(self.model, 'weights', None)
            if type(weights) != type(None):
                self['weights'] = numpy.nan
                self.loc[self['train_mask'] == 1, 'weights'] = weights

        # Set residuals. Defaults to know - calculated (equals error)
        # Set scaled residuals if available in regression results.
        self['residuals'] = self['ref_affinity'] - self['dg_calc']
        if 'model' in self._metadata:
            sresiduals = getattr(self.model, 'sresid', None)
            if type(sresiduals) != type(None):
                self['sresiduals'] = 0
                self.loc[self['train_mask'] == 1, 'sresiduals'] = sresiduals

    def summary(self, crossvalidate=False):
        """
        Goodness of fit for the model:
        Asses by max(R-squared) or max(F) or min(RSD)

        Goodness of prediction measure:
        Asses by min(SDEP) max(Q-squared)

        When the aim is to select the best model in a population of models or select
        the best variables within a set of variables or compare different models,
        or get models containing only relevant variables, the parameter R cannot be
        used (neither r or R2, obviously).

        n=15 Q2 =93.62 SDEP=0.792
        R2 = 97.65 SDEC = 0.821

        n = 15 Q2 (20%) = 91.13 LMO
        n = 5 Q2 = 88.03 SDEP EXT EXT
        Q2 (30%) = 90.32 Q2 = 90.56 LMO BOOT = 0.872
        """

        print("=" * 78)
        print("Model statistics for run: {0}, iteration {1}\n".format(self.run, self.iteration))
        print(self.model.summary())
        print("=" * 78)

        warnings = 1
        full_response = self['ref_affinity'].values
        full_observed = self['dg_calc'].values
        train_response = self.trainset['ref_affinity'].values
        train_observed = self.trainset['dg_calc'].values

        print("Goodness of fit measures:")
        print('      {0:>12s}{1:>12s}{2:>12s}{3:>12s}{3:>12s}'.format('N', 'R2/Q2', 'RMSE', 'RSD', 'F'))
        print("-" * 78)
        print('full  {0:>12}{1:>12s}{2:>12.3f}{3:>12.3f}{3:>12.3f}'.format(len(full_response), '-',
            sdec(full_response, full_observed), rsd(full_response, full_observed, len(self.params)),
            ftest(full_response, full_observed, len(self.params))))
        print('train {0:>12}{1:>12.3f}{2:>12.3f}{3:>12.3f}{3:>12.3f}'.format(len(train_response),
            rsquared(train_response, train_observed), sdec(train_response, train_observed),
            rsd(train_response, train_observed, len(self.params)), ftest(train_response, train_observed,
            len(self.params))))

        if len(full_response) - len(train_response) > 0:
            test_response = self.testset['ref_affinity'].values
            test_observed = self.testset['dg_calc'].values

            print('test  {0:>12}{1:>12.3f}{2:>12.3f}{3:>12.3f}{3:>12.3f}'.format(len(test_response),
                rsquared(test_response, test_observed), sdec(test_response, test_observed),
                rsd(test_response, test_observed, len(self.params)), ftest(test_response, test_observed,
                len(self.params))))

        if self.rmodel in ('OLS', 'GLS'):
            print(
            "Centered TSS: {0:.3f}  Uncentered TSS: {1:.3f}".format(self.model.centered_tss, self.model.uncentered_tss))
            print("ESS: {0:.3f}  RSS: {1:.3f}".format(self.model.ess, rss(train_response, train_observed)))

        print('\nWarnings:\n')
        if self.rmodel in ('OLS', 'GLS') and not self.model.intercept:
            print('[{0}] The model contains no constant, the Statsmodel R-squared is likely to high'.format(warnings))
            warnings += 1
        rsq = rsquared(train_response, train_observed)
        if round(getattr(self.model, 'rsquared', rsq), 3) != round(rsq, 3):
            print(
            '[{0}] R-Squared mismatch likely caused by non-converged regression parameters\n    in the iterative LIE optimization.'.format(
                warnings))
            warnings += 1
        if not self.converge:
            print(
            '[{0}] No convergence in regression parameters in iterative LIE modelling.\n    Oscillation detected.'.format(
                warnings))
            warnings += 1

        print("=" * 78)

        if crossvalidate:
            cv = self.crossvalidate()
            print("\nCrossvalidation statistics:")
            print("No. Observations: {n}    validation method: {cvtype}    partition size: {p}".format(**cv._metadata))
            print("SDEP/Q2: {sdep:.3f} {q2:.3f}".format(**cv._metadata))
            print("=" * 78)

        if self.rmodel == 'RLM':
            rlmoutliers = self.trainset[self.trainset['weights'] <= self.settings.rlm_outlier_cutoff]
            if not rlmoutliers.empty:
                print("\n{0} of {1} training cases attributed with a weight lower then {2:.2f} for RLM:".format(
                    rlmoutliers.shape[0], len(train_response), self.settings.rlm_outlier_cutoff))

        print(self.trainset[['case', 'dg_calc', 'ref_affinity', 'residuals', 'weights']].to_string())


class LIEModelBuilder(LIEDataFrameBase):
    _class_name = 'modelbuilder'
    _column_names = DEFAULT_MODEL_COLUMN_NAMES

    def __init__(self, *args, **kwargs):

        if 'dataframe' in kwargs:
            dataframe = kwargs.get('dataframe', None)
            if not type(dataframe) == LIEDataFrame:
                raise AssertionError(
                    "Input dataformat needs to be of LIEDataFrame type. Got {0}".format(type(dataframe)))
            else:
                self._metadata['dataframe'] = dataframe
                kwargs.pop('dataframe')

        super(LIEModelBuilder, self).__init__(*args, **kwargs)

    @property
    def _constructor(self):

        return LIEModelBuilder

    def _filter_result(self, model):

        """
        Process filter criteria for data columns. Return True/False after evaluation of combined
        filter results. Determines if filter_mask will be set to 0
        """

        passed = True
        idx = model.index.values[0]

        # Check if model parameters are within acceptable range
        params = model.at[idx, 'fit'].params
        filter_settings = self.settings.filter
        for i, param in enumerate(self.settings.param_labels):
            if params[i] < filter_settings['param_ltol'][i] or params[i] > filter_settings['param_utol'][i]:
                passed = False
                break

        if not passed:
            return passed

        for key, value in filter_settings.items():
            if key in self.columns:

                if type(value) in (int, float):
                    if model.at[idx, key] != value:
                        passed = False
                        break

                if type(value) == list:
                    if not (value[0] < model.at[idx, key] < value[1]):
                        passed = False
                        break

        return passed

    @staticmethod
    def _pivot_data(dataframe, column):
        """
        Create matrix of VdW and Coul values for every pose of every case.
        Use a pivot table to collect VdW and Coul values as matrix from a DataFrame.
        Make new (1,1) array for VdW and Coul values from a Series (only one pose).

        :param column: DataFrame column name to create pivot table for
        :ptype column: string
        :return: Pivot table as new Pandas DataFrame
        """

        if isinstance(dataframe, LIEDataFrame):
            pivot = pivot_table(dataframe, values=column, index=['case'], columns=['poses'])
        else:
            pivot = numpy.array([[dataframe[column]]])

        return pivot

    def _iterative_lie_optimizer(self, dataset, ref, rmodel=None, cases=None, L0=None):
        """
        Iteratively optimize the alpha, beta and/or gamma parameters for the LIE
        regression model.

        Iteration stops when the model parameters converge at the convergence cutoff
        value (conv_cutoff) or when the maximum iteration treshold has been reached
        (maxiter). Convergence is always assessed over the last three iterations to
        prevent a false convergence in an oscilating system.
        """

        # Determine model params
        intercept = True
        if len(self.settings.def_params) <= len(dataset):
            intercept = False
        weighted_data_labels = ['w_{0}'.format(l) for l in self.settings.model_cols]

        # Add parameter columns to dataframe if needed
        for param in self.settings.param_labels:
            if not param in self.columns: self[param] = None

        # Init a new run
        run = self.loc[self['L0'] == L0, 'L1'].max()
        if isnull(run):
            run = 0
        run += 1

        # Add iteration 0 to the DataFrame, this is the start situation
        index = self.index.max()
        if str(index) == 'nan':
            index = -1
        rowdict = {'L0': L0,
                   'L1': run,
                   'iteration': 0,
                   'set': cases,
                   'N': len(cases),
                   'converge': 0,
                   'filter_mask': 1}
        rowdict.update(dict([(self.settings.param_labels[i], param) for i, param in enumerate(self.settings.def_params)]))
        self.loc[index + 1] = Series(rowdict)

        # Start iteration
        for i in range(1, self.settings.maxiter + 1):

            # Load state at previous iteration step.
            prev_theta = self.loc[index + i][self.settings.param_labels].values

            # Get weighted energies using active theta.
            Wenergies = lie_deltag(dataset, params=prev_theta, data_labels=self.settings.model_cols, kBt=self.settings.kBt)

            # Calculate the regression model
            if intercept:
                variables = numpy.column_stack((Wenergies[weighted_data_labels].values, numpy.ones((len(cases), 1))))
            else:
                variables = Wenergies[weighted_data_labels].values

            rmodel.set(ref, variables)
            results = rmodel.fit()
            results.intercept = intercept
            irmsd = sdec(ref, results.predict())
            ir2 = 1 - (sum(numpy.square(results.resid)) / tss(ref))

            # Add new iteration to the DataFrame
            rowdict = {'L0': L0,
                       'L1': run,
                       'iteration': i,
                       'fit': results,
                       'rmsd': irmsd,
                       'rsquared': ir2,
                       'regressor': rmodel.rmodeltype,
                       'set': cases,
                       'N': len(cases),
                       'converge': 1,
                       'filter_mask': 1}
            rowdict.update(dict([(self.settings.param_labels[n], param) for n, param in enumerate(results.params)]))
            self.loc[index + i + 1] = Series(rowdict)
            logger.debug("Iteration {0}: param {1}, SDEC {2:.3f}, R2 {3:.3f}".format(i, ' '.join(
                ['{0:.3f}'.format(p) for p in results.params]), irmsd, ir2))

            # Check for convergence in regression parameters usign a rolling window
            # average over the last X iterations.
            # On convergence, pick case with lowest RSD
            # Do check for oscillation and report.
            window = (self.loc[self['L1'] == run, self.settings.param_labels]).sum(axis=1).rolling(
                window=self.settings.window_size).mean()
            if (window.loc[index + i + 1] - window.loc[index + i]) ** 2 < self.settings.conv_cutoff:

                convsel = self.iloc[index + i - self.settings.window_size + 2:index + i + 2]
                best = convsel[convsel['rmsd'] == convsel['rmsd'].min()].tail(1)
                best_index = best.index.values[0]

                # Run through filter
                if self.settings.usefilter:
                    if self._filter_result(best):
                        self.loc[best.index.values, 'filter_mask'] = 0
                        logger.info("Run {0}: iterations {1}, param {2}, SDEC {3:.3f}, R2 {4:.3f}".format(run,
                            best.at[best_index, 'iteration'], ' '.join(['{0:.3f}'.format(p) for p in
                            best.at[best_index, 'fit'].params]), best.at[best_index, 'rmsd'],
                            best.at[best_index, 'rsquared']))
                else:
                    self.loc[best.index.values, 'filter_mask'] = 0

                # Check for oscillation over the last 4 iterations
                tail = self[self['L1'] == run].tail(4)
                alpha_gradient = numpy.mean(numpy.gradient(tail['alpha']))
                beta_gradient = numpy.mean(numpy.gradient(tail['beta']))
                if abs(alpha_gradient) > 0.001 or abs(beta_gradient) > 0.001:
                    self.loc[best_index, 'converge'] = 0
                    self.loc[best_index, 'filter_mask'] = 1
                    logger.warn(
                        "Run {0}: oscillation detected over last 4 iterations. alpha gradient {1}, beta gradient {2}".format(
                            run, alpha_gradient, beta_gradient))

                # Return index of best model
                return best_index

        # Maximum number of iterations reached. Report, do not set filter_mask to 0
        if i == self.settings.maxiter:
            self.loc[index + i + 1, 'converge'] = 0
            logger.warn('not converged within {0} iterations'.format(self.settings.maxiter))

    def _parse_to_list(self, indexes):
        """
        Cast indexes to list and validate if all elements of the resulting list are
        a subset of dataframe indexes
        """

        if indexes and not isinstance(indexes, list):
            indexes = [int(indexes)]
        else:
            indexes = self.index.values

        assert set(indexes).issubset(self.index.values), "No model with index {0} in LIEModelBuilder instance".format(
            set(indexes).difference(self.index.values))

        return indexes

    def get_cases(self, index=None):
        """
        Return cases for one or more models by index as a list

        Index accepts multiple input types:
        None:    if no index defined, a list of unique cases for all models in the
                 current dataframe is returned.
        Integer: cases in the single model are returned
        List:    Unique cases for the subset of models defined by their indexes

        :param index: Index(es) to return cases for
        :ptype index: Integer or list of integers. None returns all

        :return:      List or None
        """

        superset = []
        for idx in self._parse_to_list(index):
            superset.extend(self.loc[idx, 'set'])

        return sorted(set(superset))

    def get_base(self, index):
        """Get the base model for a model derivative"""

        index = self._parse_to_list(index)
        base_index = self.loc[index[0], 'L0']
        return self[(self['L0'] == base_index) & (self[['L0', 'L1', 'filter_mask']].sum(axis=1) == 2)]

    def isbase(self, index):
        index = self._parse_to_list(index)
        return self.loc[index[0], ['L0', 'L1']].sum() == 2

    def issubset(self, first, second):
        """Is every case in the first also in the second (subset)"""

        first = self.get_cases(first)
        second = self.get_cases(second)

        return set(first).issubset(set(second))

    def issuperset(self, first, second):
        """Is every case in the second also in the first (superset)"""

        first = self.get_cases(first)
        second = self.get_cases(second)

        return set(first).issuperset(set(second))

    def union(self, collection):
        """Return list of the cases in the input collection combined"""

        return self.get_cases(collection)

    def intersection(self, first, second):
        """Return list with cases common to both first and second"""

        first = self.get_cases(first)
        second = self.get_cases(second)

        return sorted(set(first).intersection(set(second)))

    def difference(self, first, second, symmetric=False):
        """Return list with cases in first but not in second or with cases in
           either the first or the second but not in both if symmetric equals True
        """

        first = self.get_cases(first)
        second = self.get_cases(second)

        if symmetric:
            return sorted(set(first).symmetric_difference(set(second)))
        return sorted(set(first).difference(set(second)))

        # (Re)sampling functions

    def emr(self):
        # Global model first
        sourceset = self.dataframe.cases
        full_model = self.model(rmodel=RLMregression(), cases=sourceset)
        opt_model = self.model(rmodel=OLSregression(), cases=full_model[full_model['weights'] >= 0.9].cases)

        # Run GMM
        lowest_bic = numpy.infty
        bic = []
        n_components_range = range(1, 7)
        cv_types = ['spherical', 'tied', 'diag', 'full']
        x = opt_model[['ref_affinity', 'dg_calc']].values
        for cv_type in cv_types:
            for n_components in n_components_range:
                # Fit a mixture of Gaussians with EM
                gmm = mixture.GMM(n_components=n_components, covariance_type=cv_type)
                gmm.fit(x)
                bic.append(gmm.bic(x))
                if bic[-1] < lowest_bic:
                    lowest_bic = bic[-1]
                    best_gmm = gmm

        gmm_clusters = best_gmm.predict(x)

        # Report GMM results
        print bic
        print set(gmm_clusters)

        # Regress on new clusters
        opt_model['gmm'] = gmm_clusters
        for cluster in set(gmm_clusters):
            v = self.model(rmodel=RLMregression(), cases=opt_model[opt_model['gmm'] == cluster].cases)
            self.model(rmodel=OLSregression(), cases=v[v['weights'] >= 0.9].cases)
            self.mcresample(v.mid, full_model.mid)

    def mcresample(self, index, superset=None, posestore=True, **kwargs):
        """
        MonteCarlo like resampling of a cluster aimed on enlarging the cluster
        within the limits defined by the filter criteria.
        """

        # Update class settings from kwargs dict
        self.settings.update(kwargs)

        # Get cases for source- and superset. If superset equals None, all cases in the dataset are used
        superset = self.get_cases(superset)
        sourceset = self.get_cases(index)

        # DataFrame to keep track of case weights during optimization
        columns = ['mid', 'rmsd', 'rsquared', 'alpha', 'beta'] + sorted(superset)
        tracker = DataFrame(columns=columns)

        # Dataframe to keep track of poses with highest weight during optimization
        if posestore:
            poserecord = DataFrame(columns=['cases'])
            poserecord['cases'] = self.dataframe.cases

        def poserecord_update(model):

            selected_poses = []
            for ida, a in model[model.get_columns('prob-*')].iterrows():
                m = a.idxmax()
                selected_poses.append(int(m[-1]))

            poserecord[model.mid] = 0
            for p in zip(selected_poses, model.cases):
                poserecord.loc[(poserecord['cases'] == p[1]), model.mid] = p[0]

        def tracker_update(model):

            rowdict = {'mid': model.mid, 'rmsd': model.rmsd, 'rsquared': model.rsquared, 'alpha': model.model.params[0],
                       'beta': model.model.params[1]}
            cases = list(model['case'].values)
            weights = list(model['weights'].values)
            rowdict.update(dict(zip(cases, weights)))

            if not len(tracker.index):
                idx = 1
            else:
                idx = max(tracker.index) + 1

            tracker.loc[idx] = Series(rowdict)

        # First get the RLM weights of the source set
        label = self.loc[index, 'L0']
        if self.loc[index, 'regressor'] != 'RLM':
            rlm_model = self.model(rmodel=RLMregression(), label=label, cases=sourceset)
        else:
            rlm_model = self.getmodel(index)
        tracker_update(rlm_model)

        # Set the rmsd and rsquare filter rules to match base model stats increased by mc_filter_tol
        # to give room to improve up to original filter cutoff's
        orig_rmsd_filter = self.settings.filter['rmsd']
        orig_rsquared_filter = self.settings.filter['rsquared']

        new_rmsd_cutoff = self.loc[index, 'rmsd'] * (2 - self.settings.mc_filter_tol)
        if new_rmsd_cutoff >= orig_rmsd_filter[1]:
            new_rmsd_cutoff = orig_rmsd_filter[1]

        new_rsquared_cutoff = self.loc[index, 'rsquared'] * self.settings.mc_filter_tol
        if new_rsquared_cutoff <= orig_rsquared_filter[0]:
            new_rsquared_cutoff = orig_rsquared_filter[0]

        self.settings.filter['rmsd'] = [orig_rmsd_filter[0], new_rmsd_cutoff]
        self.settings.filter['rsquared'] = [new_rsquared_cutoff, orig_rsquared_filter[1]]
        logger.warn("Initial filter rules: rmsd = {0:.3f}-{1:.3f}, r-squared = {2:.3f}-{3:.3f}".format(
            orig_rmsd_filter[0], new_rmsd_cutoff, new_rsquared_cutoff, orig_rsquared_filter[1]))

        # Determine number of RLM outliers in the baseset
        # - Add them to the superset so they may be added again later
        downweight = [n for n in rlm_model.trainset[rlm_model.trainset['weights'] <= self.settings.rlm_outlier_cutoff].cases
                      if n not in superset]
        superset.extend(downweight)
        logger.warn("RLM outlier in source set (<= {0:.2f}): {1}".format(self.settings.rlm_outlier_cutoff, downweight))

        # iterate through superset as long as there are elements in it or max_iter_steps reached
        baseset = rlm_model[rlm_model['weights'] > self.settings.rlm_outlier_cutoff].cases
        iteration = 0
        removed = []
        latest_model = rlm_model.mid
        no_model_count = 0
        while len(superset) and iteration < self.settings.max_iter_steps:

            iteration += 1

            # - Ajust propensity for drawing new sample based on outlier count
            if len(removed):
                propensities = [1 - (removed.count(case) / float(len(removed))) for case in superset]
                prop_sum = sum(propensities)
                propensities = [p / prop_sum for p in propensities]
            else:
                propensities = [1.0 / len(superset)] * len(superset)

            # - Draw random sample
            sample_size = int(len(baseset) * self.settings.mc_rand_sample_draw)
            sample = list(choice(superset, size=sample_size, p=propensities, replace=False))
            logger.debug("Draw sample of {0} cases: {1}".format(sample_size, str(sample).strip('[]')))

            # - RLM model using the new baseset
            model = self.model(rmodel=RLMregression(), label=label, cases=baseset + sample)

            # - Check if we get a model back
            if type(model) != type(None):
                ref = model.trainset['ref_affinity'].values
                rmsd = sdec(ref, model.model.predict())
                r2 = 1 - (sum(numpy.square(model.model.resid)) / tss(ref))

                # - Get down weighted cases
                dw = model.trainset[model.trainset['weights'] <= self.settings.rlm_outlier_cutoff].cases
                adj_sample = [n for n in sample if not n in dw]

                # - If all are downweighted, continue
                if not len(adj_sample):
                    removed.extend(sample)
                    continue

                # - If there are down-weighted cases in the sample, rerun RLM without them.
                if len(adj_sample) != len(sample):

                    model = self.model(rmodel=RLMregression(), label=label, cases=baseset + adj_sample)
                    if type(model) == type(None):
                        continue

                    dw = model.trainset[model.trainset['weights'] <= self.settings.rlm_outlier_cutoff].cases
                    ref = model.trainset['ref_affinity'].values
                    rmsd = sdec(ref, model.model.predict())
                    r2 = 1 - (sum(numpy.square(model.model.resid)) / tss(ref))

                # - Check if filter rules are passed
                if model.filterpass == 0:

                    tracker_update(model)

                    # - Track significant poses
                    if posestore:
                        poserecord_update(model)

                    # - Register model and reset no_model_count
                    latest_model = model.mid
                    no_model_count = 0

                    # - Add down weighted cases to removed
                    removed.extend(dw)

                    # - Model passed, register new baseset and correct removed
                    baseset = list(set(baseset + adj_sample))
                    superset = [c for c in superset if not c in baseset]
                    removed = [r for r in removed if not r in baseset]

                    # - Adjust filter criteria
                    new_rmsd_cutoff = rmsd * (2 - self.settings.mc_filter_tol)
                    if new_rmsd_cutoff >= orig_rmsd_filter[1]:
                        new_rmsd_cutoff = orig_rmsd_filter[1]
                    elif new_rmsd_cutoff <= self.settings.filter['rmsd'][1]:
                        new_rmsd_cutoff = self.settings.filter['rmsd'][1]

                    new_rsquared_cutoff = r2 * self.settings.mc_filter_tol
                    if new_rsquared_cutoff <= orig_rsquared_filter[0]:
                        new_rsquared_cutoff = orig_rsquared_filter[0]
                    elif new_rsquared_cutoff >= self.settings.filter['rsquared'][0]:
                        new_rsquared_cutoff = self.settings.filter['rsquared'][0]

                    self.settings.filter['rmsd'] = [orig_rmsd_filter[0], new_rmsd_cutoff]
                    self.settings.filter['rsquared'] = [new_rsquared_cutoff, orig_rsquared_filter[1]]
                    logger.warn("New filter criteria for rmsd ({0:.3f}-{1:.3f}) and r-squared ({2:.3f}-{3:.3f})".format(
                        orig_rmsd_filter[0], new_rmsd_cutoff, new_rsquared_cutoff, orig_rsquared_filter[1]))

                    logger.warn(
                        "MonteCarlo optimize: iteration {0}, rmsd: {1:.3f}, r-squared: {2:.3f}. Baseset: {3}, superset: {4} sample size: {5}".format(
                            iteration, rmsd, r2, len(baseset), len(superset), sample_size))

                else:
                    removed.extend(adj_sample)
                    no_model_count += 1
                    if no_model_count >= 20:
                        logger.warn("Unable to improve model after {0} unsuccessful sample additions. Stopping".format(
                            no_model_count))
                        break

        # Reset filter to original values
        self.settings.filter['rmsd'] = orig_rmsd_filter
        self.settings.filter['rsquared'] = orig_rsquared_filter

        logger.warn(
            "MC optimization finished: baseset {0}, superset {1}, rmsd {2:.3f} r-squared {3:.3f}".format(len(baseset),
            len(superset), self.loc[latest_model, 'rmsd'], self.loc[latest_model, 'rsquared']))

        logger.info("Safe tracker dataframe to file")
        tracker.to_csv('tracker_model_{0}.csv'.format(index))

        if posestore:
            poserecord.to_csv('poses_model_{0}.csv'.format(index))

        return baseset

    def rlm_optimize(self, index, **kwargs):
        """
        Iteratively optimize a cluster based on the number of down weighted cases
        in the robust linear regression.
        """

        # Update class settings from kwargs dict
        self.settings.update(kwargs)

        label = self.loc[index, 'L0']
        iteration = 0
        sourceset = self.get_cases(index)
        while iteration < 100:

            model = self.model(rmodel=RLMregression(), label=label, cases=sourceset)

            # - Check if we get a model back
            if type(model) != type(None):

                ref = model.trainset['ref_affinity'].values
                rmsd = sdec(ref, model.model.predict())
                r2 = 1 - (sum(numpy.square(model.model.resid)) / tss(ref))

                # - Get down weighted cases
                dw = model[model['weights'] <= self.settings.rlm_outlier_cutoff].cases

                print("RLM optimize: iteration {0}, rmsd: {1:.3f}, rquared: {2:.3f}. cluster size: {3}, dw: {4}".format(
                    iteration, rmsd, r2, len(sourceset), len(dw)))

                if len(dw):
                    for case in dw:
                        sourceset.remove(case)
                else:
                    return model

            iteration += 1

    def resample(self, index, cvtype='LOO'):
        """
        Resample a model using a cross-validation method.

        :param index:   DataFrame index of model to resample
        :ptype index:   int
        :param cvtype:  Cross-validation method to use. Default 'LOO' (Leave-One-Out)
                        For other option see the cv_set_partitioner method.
        :ptype cvtype:  string
        :return:        None, resampled moddels added to class dataframe
        """

        assert index in self.index.values, "No model with index {0} in LIEModelBuilder instance".format(index)

        model = self.iloc[index]
        self.settings['label'] = model['L0']

        # Create Cross-validation partition table
        cvmatrix = cv_set_partitioner(model['set'], cvtype=cvtype)
        self.batchmodel(cvmatrix)

    def weight_resample(self, index):
        """
        Resample a OLS generated model using the RLM regressor and correcting for all
        cases with a regression weight lower than 0.80

        :param index:   DataFrame index of model to resample
        :ptype index:   int
        :return:        None, resampled moddels added to class dataframe
        """

        assert index in self.index.values, "No model with index {0} in LIEModelBuilder instance".format(index)

        self.settings['label'] = self.loc[index, 'L0']
        if self.loc[index, 'regressor'] != 'RLM':
            self.dataframe.trainset = self.loc[index, 'set']
            model = self.model(rmodel=RLMregression())
        else:
            model = self.getmodel(index)

        if type(model) != type(None):
            cases = model[model['weights'] > 0.80].cases
            self.dataframe.trainset = cases
            return self.model(rmodel=RLMregression())

    def getlabel(self, label='L0'):
        label_value = self[label].max()
        if isnull(label_value):
            label_value = 1

        return label_value + 1

    def get_unique_clusters(self):
        clusters = self.clusters()
        return list(clusters[clusters.sum(axis=1) == 0].index.values)

    def clusters(self):
        master_lst = dict([(i, n['set']) for i, n in self.iterrows()])

        cluster_list = defaultdict(list)
        for idd in master_lst:
            for ids in master_lst:
                if not idd == ids:
                    if set(master_lst[ids]).issubset(set(master_lst[idd])):
                        cluster_list[idd].append(ids)

        keys = self.index
        cluster_matrix = DataFrame(columns=keys, index=keys)
        for i, n in cluster_list.items():
            cluster_matrix.loc[n, i] = 1
        cluster_matrix.fillna(0, inplace=True)

        return cluster_matrix

    def getmodel(self, index, **kwargs):
        assert index in self.index.values, "No model with index {0} in LIEModelBuilder instance".format(index)

        # Update class settings from kwargs dict
        self.settings.update(kwargs)

        model = self.loc[index]
        modelfit = model['fit']

        # Recalculate deltaG values for all cases using the model parameters of the
        # current regression model. Create a new LIEModelFrame of the dataset.
        exog = [self._pivot_data(self.dataframe, column) for column in self.settings.model_cols]
        dg_calc = lie_deltag(exog, params=modelfit.params, kBt=self.settings.kBt)
        modelframe = LIEModelFrame(dg_calc)

        # Add reference affinity, filter mask data and set the training mask
        modelframe['ref_affinity'] = self._pivot_data(self.dataframe, 'ref_affinity').mean(axis=1).values
        modelframe['filter_mask'] = self._pivot_data(self.dataframe, 'filter_mask').mean(axis=1).values
        modelframe['train_mask'] = 0
        modelframe.trainset = model['set']

        # Add the regression results object as argument in the new LIEModelFrame
        # instance. Call the LIEModelFrame instance to have it pre-process the
        # DataFrame before returning it.
        modelframe.model = modelfit
        modelframe.rmodel = model['regressor']  # Regressor type use
        modelframe.source = self.dataframe  # Pointer to source data
        modelframe.converge = model['converge']
        modelframe.run = model['L0']
        modelframe.mid = index  # Index of the model in the current ModelBuilder
        modelframe.filterpass = model['filter_mask']  # Passed modelbuilder filter?
        modelframe.iteration = model['iteration']
        modelframe.rmsd = model['rmsd']
        modelframe.rsquared = model['rsquared']
        modelframe.fitstats_to_table()

        return modelframe

    def batchmodel(self, clusterset, rmodel=OLSregression(), **kwargs):
        # Update class settings from kwargs dict
        self.settings.update(kwargs)

        for cluster in [col for col in clusterset.columns if not col == 'case']:

            cases = clusterset.loc[clusterset[cluster] == 1, 'case']
            cases = cases.values.tolist()

            if len(cases) < self.settings.minclustersize:
                logger.debug("Cluster {0} has {1} members. Less than minimum clustersize of {2}".format(cluster,
                    len(cases), self.settings.minclustersize))
                continue

            self.dataframe.trainset = cases

            model = self.model(rmodel=rmodel, cases=cases, label=self.settings.get('label', cluster))

    def model(self, rmodel=OLSregression(), label=None, cases=[], **kwargs):
        """
        Build a model from the data in the LIEDataFrame contained in the class
        instance using a regression algorithm.

        :param rmodel: Class representing the regression algorithm to use.
                       OLS_regression class by default.
        :return:       Class representing the build model.
        :rtype:        LIEModelFrame
        """

        # Update class settings from kwargs dict
        if not label:
            label = self.getlabel()
        self.settings.update(kwargs)

        # Determine parameter labels
        self.settings['param_labels'] = [GREEK_ALPHABET[i] for i, p in enumerate(self.settings.def_params)]

        # Check if we have reference affinity data to model against
        assert self.dataframe['ref_affinity'].sum() != 0, "Unable to model, no reference affinity data available"

        # Extract training set from the dataframe if any, else use full set.
        if cases:
            self.dataframe.trainset = cases

        trainset = self.dataframe.trainset
        if trainset.empty:
            trainset = self.dataframe

        cases = trainset.cases
        logger.info("Use {0} training cases for regression modelling".format(len(cases)))

        # Create pivot tables for model data columns and reference affinity data
        exog = [self._pivot_data(trainset, column) for column in self.settings.model_cols]
        ref = self._pivot_data(trainset, self._column_names.get('ref_affinity', 'ref_affinity')).mean(axis=1).values

        # Perform iterative modelling
        model_index = self._iterative_lie_optimizer(exog, ref, rmodel=rmodel, cases=cases, L0=label)

        if model_index:
            return self.getmodel(model_index)
