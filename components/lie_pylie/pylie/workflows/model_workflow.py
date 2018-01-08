# -*- coding: utf-8 -*-

import logging
import numpy
import pandas

from .. import pylie_config
from .. import LIEModelBuilder, LIEScanDataFrame
from ..model.liemodelframe import RLM_regression

logger = logging.getLogger('pylie')


class ModelWorkflow(object):
    """
    Premade workflow for automated clustering and LIE model generations.

    Settings:
    Class aggregates settings from ModelWorkflow and LIEScanDataFrame.

    :param data: Input LIE DataFrame.
    :ptype data: LIEDataFrame
    """

    def __init__(self, data, clusters=None, **kwargs):

        # Store original dataframe(s) and list of processed dataframe(s)
        self.data = data

        # Get copy of the global configuration for this class
        self.settings = pylie_config.get(instance=[type(self).__name__, 'LIEScanDataFrame'])
        self.settings.update(kwargs)

        # Obtain initial clusters based on Alpha/Beta scan if no other
        # clusters as input.
        if type(clusters) == type(None):
            clusters = self._init_clusters()

        # Run modelling routine
        self._init_models(clusters)

        # self.result = self._cluster_final_models(self.modeller.inliers)

    def _init_clusters(self):
        """
        Create initial clusters based on an alpha/beta scan.
        Scan and clustering setting may be altered using the LIEScanDataFrame settings.
        """

        # Prepare scan
        abscan = LIEScanDataFrame()
        abscan.settings.update(self.settings())
        abscan.scan(self.data.inliers)
        clusters = abscan.cluster()

        # Make figures
        if self.settings['plotClusterResults']:
            fig = abscan.plot(kind='optimal')
            fig.savefig('alphabetascan_optimal.{0}'.format(self.settings['plotFileType']))
            fig = abscan.plot(kind='simmatrix')
            fig.savefig('alphabetascan_simmatrix.{0}'.format(self.settings['plotFileType']))
            fig = abscan.plot(kind='dendrogram')
            fig.savefig('alphabetascan_dendrogram.{0}'.format(self.settings['plotFileType']))
            fig = abscan.plot(kind='density', utol=5, ltol=-5)
            fig.savefig('alphabetascan_density.{0}'.format(self.settings['plotFileType']))

        return clusters

    def _init_models(self, clusters):
        """
        Determine the number of models the data most likely has with the aim of covering
        as much as possible of the cases and describing the relationship between the
        models.
        """

        # Collect outliers previously detected
        outliers = self.data.outliers.cases
        logger.info("Initial cases marked as outliers: {0}".format(str(outliers).strip('[]')))

        # Prepare modelframe
        self.modeller = LIEModelBuilder(dataframe=self.data.inliers)
        self.modeller.settings.update(self.settings())
        rmsd_filter_range = self.modeller.settings['filter']['rmsd']
        r2_filter_range = self.modeller.settings['filter']['rsquared']

        # Run modelling on full dataset as reference
        basemodel = self.modeller.model(cases=self.data.cases, rmodel=RLM_regression())
        logger.info("Initial model of the full dataset:")

        # Run batch modelling routine on initial clusters
        logger.info("Generate models for {0} clusters obtained from alpha/beta scan".format(len(clusters)))
        self.modeller.batchmodel(clusters, rmodel=RLM_regression())

        # Report on initial clusters
        report_columns = ['N', 'rmsd', 'rsquared', 'regressor']
        report_columns.extend(self.modeller.settings.param_labels)
        inliers = self.modeller.inliers
        cl = inliers.clusters()
        unique_cl = list(cl[cl.sum(axis=1) == 0].index.values)

        if not len(unique_cl):
            logger.error("No unique models obtained from initial clusters derived from alpha/beta scan. Stopping")
            return

        unique_clusters = self.modeller.loc[unique_cl, :]
        logger.info("Generated {0} models of which {1} unique in case composition".format(len(inliers), len(unique_cl)))
        logger.info("filter RMSD range of {0} and r2 range of {1}".format(str(rmsd_filter_range).strip('[]'),
                                                                          str(r2_filter_range).strip('[]')))

        print("Balance: {0} total cases, {1} in initial unique models based on alpha/beta scan:".format(
            len(self.data.cases), unique_clusters['N'].sum()))
        print(unique_clusters[report_columns].sort('rsquared', ascending=False).to_string())

        # Enrich all initial models
        for idx in inliers.index:
            self.modeller.mcresample(idx, basemodel.mid)

        print("Enriched models")
        print self.modeller.inliers[report_columns].sort('rsquared').to_string()

    @staticmethod
    def _cluster_final_models(models):
        """
        Calculate the custom similarity metric between models
        """

        # Remove duplicate regression models
        duplicate_set = []
        indexes = []
        for idx, row in models.iterrows():
            if not row['set'] in duplicate_set:
                duplicate_set.append(row['set'])
                indexes.append(idx)
        filtered = models.loc[indexes]

        print("removed {0} identical regression models from a dataset with {1} models".format(
            len(models) - len(indexes), len(models)))

        # Get occurrence weights for each case
        # - Frequency of occurrence of case in all of the models divided by model count
        total_models = len(filtered)
        case_weight = [b for i in filtered['set'] for b in i]
        case_weight = dict([(x, float(case_weight.count(x)) / total_models) for x in case_weight])

        # Get alpha / beta value for the largest model
        abmax = filtered.sort('N', ascending=[0]).head(1)
        abmax = abmax[['alpha', 'beta']]

        # Get path
        matrix = {}
        count = 1
        index = []
        for idx1, row1 in filtered.sort('rmsd').iterrows():

            a = set(row1['set'])
            gdiff1 = abs(abmax - row1[['alpha', 'beta']])
            scores = []
            for idx2, row2 in filtered.sort('rmsd').iterrows():

                # Calculate symmetric difference between two sets and divide by total set.
                # Represent each case according to there frequency of occurance and sum the lists.
                # NOTE: Frequency of occurrence assumes that the base set was constructed using
                # a homogeneous sampling.
                b = set(row2['set'])
                diff = [1 - case_weight[n] for n in a.symmetric_difference(b)]
                if diff:
                    diff = sum(diff) / sum([1 - case_weight[n] for n in a.union(b)])
                else:
                    diff = 0

                # Calculate difference in alpha/beta parameters.
                gdiff2 = abs(abmax - row2[['alpha', 'beta']])
                if (gdiff1 + gdiff2).sum(axis=1).values > 0:
                    abdiff = (abs(row1[['alpha', 'beta']] - row2[['alpha', 'beta']]) / (gdiff1 + gdiff2)).sum(axis=1)
                    abdiff = abdiff.values
                else:
                    abdiff = numpy.array([0.0, 0.0])

                # Sum normalized differences
                score = abdiff + diff
                scores.append((score / 3)[0])

            matrix[count] = scores
            index.append(idx1)
            count += 1

        df = pandas.DataFrame(matrix)
        df.columns = index
        df.index = index

        return df
