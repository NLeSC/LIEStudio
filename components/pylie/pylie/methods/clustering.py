# -*- coding: utf-8 -*-

import logging
import pandas
import os
import time
import getpass
import StringIO

from .. import LIEModelBuilder, pylie_config
from ..methods.methods import cv_set_partitioner
from ..model.liemodelframe import RLMregression, OLSregression

logger = logging.getLogger('pylie')

GREEK_ALPHABET = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 'theta', 'iota', 'kappa',
                  'lambda', 'mu', 'nu', 'xi', 'omicron', 'pi', 'rho', 'sigma', 'tau', 'upsilon', 'phi',
                  'chi', 'psi', 'omega']


class StochasticOptimizer(object):
    def __init__(self, dataframe, **kwargs):

        # Register source dataset. Reset test/train cases
        self.dataframe = dataframe
        self.dataframe['train_mask'] = 0

        # Get class settings
        self.settings = pylie_config.get(instance=type(self).__name__)
        self.settings.update(kwargs)

        self._cluster_matrix = pandas.DataFrame({'cases': self.dataframe.cases})

    def _filter_move(self, dataframe):

        if self.settings['exclude_nonconverged']:
            dataframe = dataframe[dataframe['converge'] == 1]

        # Check if model parameters are within acceptable range
        ltol = self.settings['param_ltol']
        utol = self.settings['param_utol']
        param_labels = [col for col in dataframe.columns if col in GREEK_ALPHABET]
        for i, param in enumerate(param_labels):
            dataframe = dataframe[(dataframe[param] > ltol[i]) & (dataframe[param] < utol[i])]

        return dataframe

    def run(self):

        modeller = LIEModelBuilder(dataframe=self.dataframe)
        basemodel = modeller.model(rmodel=RLMregression(),
                                   minclustersize=self.settings['minclustersize'])

        # Register the basemodel
        self._cluster_matrix[0] = basemodel['weights']
        cluster_set = basemodel.cases
        outliers = []
        for itr in range(10):

            # Set matrix indexes
            start_index = self._cluster_matrix.shape[1]

            # Stochastic iterations
            cv = cv_set_partitioner(cluster_set, cvtype='RAND', p=0.9, maxpartitions=50)

            # Random reintroduce outliers from previous iteration
            if outliers:
                pass

            modeller.batchmodel(cv,
                                rmodel=RLMregression(),
                                minclustersize=self.settings['minclustersize'])

            bestmodels = self._filter_move(modeller.inliers)
            for i, n in bestmodels.iterrows():
                model = bestmodels.getmodel(i)
                self._cluster_matrix[i] = model['weights']

            # Calculate weight means. Create new clusters
            weight_means = self._cluster_matrix.iloc[:, start_index:self._cluster_matrix.shape[1]].mean(axis=1)
            weight_means = pandas.DataFrame({'case': model['case'], 'mean': weight_means})

            cluster_set = weight_means.loc[weight_means['mean'] >= 0.8, 'case'].values
            outliers = weight_means.loc[weight_means['mean'] < 0.8, 'case'].values


class ClusterOptimizer(object):
    def __init__(self, dataframe, **kwargs):

        # Register source dataset
        self.dataframe = dataframe

        # Get class settings
        self.settings = pylie_config.get(instance=type(self).__name__)
        self.settings.update(kwargs)

        # Prepaire the report
        self._report = StringIO.StringIO()
        self._print_header()

        # Create clustering dataframe
        self._clust_frame = None
        self._model_count = 1

    def _print_header(self):

        self._report.write('=' * 100 + '\n')
        self._report.write(
            "LIE cluster based modelling workflow\n- Date: {0}\n- folder: {1}\n- User: {2}\n".format(time.ctime(),
                                                                                                     os.getcwd(),
                                                                                                     getpass.getuser()))
        self._report.write('=' * 100 + '\n')

    def _filter_clusters(self, dataframe):

        if self.settings['exclude_nonconverged']:
            dataframe = dataframe[dataframe['converge'] == 1]

        # Check if model parameters are within acceptable range
        ltol = self.settings['param_ltol']
        utol = self.settings['param_utol']
        param_labels = [col for col in dataframe.columns if col in GREEK_ALPHABET]
        for i, param in enumerate(param_labels):
            dataframe = dataframe[(dataframe[param] > ltol[i]) & (dataframe[param] < utol[i])]

        return dataframe.sort(['rsquared', 'rmsd', 'norm'], ascending=[0, 1, 1])

    def optimize(self, clusters):

        # First pass through clusterspace, discards cluster below minclustersize
        modeller = LIEModelBuilder(dataframe=self.dataframe)
        modeller.batchmodel(clusters,
                            rmodel=RLMregression(),
                            minclustersize=self.settings['minclustersize'])

        # For each pass do crossvalidation
        bestmodels = modeller.inliers
        param_labels = [col for col in bestmodels.columns if col in GREEK_ALPHABET]
        for idx, model_instance in bestmodels.iterrows():

            model = bestmodels.getmodel(idx)

            # Make a new cluster dataframe if not yet defined
            if type(self._clust_frame) == type(None):
                columns = modeller.columns.values.tolist()
                columns.append('base')
                self._clust_frame = pandas.DataFrame(columns=columns)

            self._clust_frame.loc[self._model_count] = model_instance
            self._clust_frame.loc[self._model_count, 'base'] = model_instance['L1']
            self._model_count += 1

            # If model contains minclustersize cases, no crossvalidation
            if model_instance['N'] == self.settings['minclustersize']:
                continue

            # If model contains less than 15 cases. Do LOO crossvalidation
            elif model_instance['N'] < 15:
                cv = model.crossvalidate()

            # Else run KFOLD crossvalidation
            else:
                cv = model.crossvalidate()
                # cv = model.crossvalidate(cvtype='RAND', p=0.8, maxpartitions=40)

            bestcvmodels = cv.inliers
            for idz, cvmodel_instance in bestcvmodels.iterrows():
                self._clust_frame.loc[self._model_count] = cvmodel_instance
                self._clust_frame.loc[self._model_count, 'base'] = model_instance['L1']
                self._model_count += 1

        # Filter results
        filtered_clusters = self._filter_clusters(self._clust_frame)
        filtered_clusters.sort('base', inplace=True)

        # How many outliers (non-clustered cases) do we have
        modelled_cases = set(
            [case for i, n in filtered_clusters[filtered_clusters['rmsd'] <= 5.0].iterrows() for case in n['set']])
        nonmodelled_cases = set(self.dataframe.cases).difference(modelled_cases)
        if nonmodelled_cases:
            print("Following cases where not modelled within tolerance range of {0:.2f} kJ/mol:".format(5))
            print("{0}".format(' '.join(list(nonmodelled_cases))))

        # Print all results
        weighted_dataframes = []
        describe_columns = ['rsquared', 'rmsd'] + param_labels
        for base in filtered_clusters['base'].unique():

            # General statistics of the cluster
            baseset = filtered_clusters[filtered_clusters['base'] == base]
            print("\nCluster: {0:.0f} having {1:.0f} cases\n".format(base, baseset['N'].max()))
            print(baseset[describe_columns].describe())

            # Create new OLSmodels
            optimal = baseset.sort(['rsquared', 'N'], ascending=[0, 0]).head(n=1)
            self.dataframe.trainset = optimal['set'].values[0]

            modeller = LIEModelBuilder(dataframe=self.dataframe)
            m = modeller.model(rmodel=OLSregression(), minclustersize=self.settings['minclustersize'] - 1)
            print m.summary()

            # Determine RLM based outliers
            baseset_cases = set([case for n in baseset['set'] for case in n])
            baseset_cases = sorted(list(set(baseset_cases)))

            weights_dataframe = pandas.DataFrame(index=baseset_cases)
            for i, n in baseset.iterrows():
                weights = []
                c = n['set']
                w = n['fit'].weights
                for case in baseset_cases:
                    if case in c:
                        weights.append(w[c.index(case)])
                    else:
                        weights.append(None)
                weights_dataframe[n['L1']] = weights

            weighted_dataframe_mean = weights_dataframe.mean(axis=1)
            weighted_dataframes.append(weighted_dataframe_mean)

            print('\nCases with an average RLM weight below {0:.1f} after cross-validation:'.format(0.8))
            print('{0}'.format(' '.join(weighted_dataframe_mean[weighted_dataframe_mean < 0.8].index.values)))

        newclusters = pandas.concat(weighted_dataframes, axis=1)

        clusters = (newclusters >= 0.8).astype(int)
        clusters.reindex()
        clusters['case'] = newclusters.index

        # Create new models
        modeller = LIEModelBuilder(dataframe=self.dataframe)
        modeller.batchmodel(clusters, rmodel=OLSregression(), minclustersize=self.settings['minclustersize'] - 1)
        modeller['N'] = modeller['set'].apply(len)

        bestmodels = modeller.inliers
        param_labels = [col for col in bestmodels.columns if col in GREEK_ALPHABET]
        for idx, model_instance in bestmodels.iterrows():
            model = bestmodels.getmodel(idx)
            print model.summary()

            fig = model.plot(kind='model')
            fig.savefig('optim_model_{0}.pdf'.format(model_instance['L1']))
