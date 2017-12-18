# -*- coding: utf-8 -*-

import logging
import numpy

from .. import pylie_config
from ..plotting import plot_filtergaussian_distribution
from ..methods.methods import multivariate_gaussian

logger = logging.getLogger('pylie')


class FilterGaussian(object):

    def __init__(self, liedataframe, **kwargs):

        self.liedataframe = liedataframe.copy(deep=True)

        # Get copy of the global configuration for this class
        self.settings = pylie_config.get(instance=type(self).__name__)
        self.settings.update(kwargs)

        self._ellipse = None

    def filter(self):
        """
        Pose filtering using multivariate Gaussian Distribution analysis of
        the VdW and Coul components of the full data set.

        Outliers are registered by adding 1 to the filter_mask columns for
        outlier poses. Running the filter method multiple times using
        different settings will cumulative add the filter count for the
        poses.

        Returns
        -------
        LIESeries: Identity array with poses identified as outlier.
        """

        # Calculate outliers in the multivariate Gaussian distribution analysis.
        # Returns the outliers as vector and an Ellipse object for plotting
        outliers, self._ellipse = multivariate_gaussian(
            self.liedataframe[['coul', 'vdw']],
            confidence=self.settings.confidence,
            returnellipse=True,
            edgecolor='red',
            facecolor='none')

        # Register outliers.
        self.liedataframe['filter_mask'] = self.liedataframe['filter_mask'].values + numpy.array(outliers)

        # Check outliers for any cases leading to all but one pose to be marked as
        # outlier. Not wise to include this in the boltzmann weighted sheme.
        logger.info(
            "Outlier detection. Outliers: {0} of {1} points, method: Multivariate Gaussian distribution."
            "Confidence interval {2:.3f}".format(
                outliers.sum(), self.liedataframe[['coul', 'vdw']].size, self.settings.confidence))

        return self.liedataframe

    def plot(self, kind="distribution", *args, **kwargs):

        if kind == 'distribution':
            if self._ellipse:
                return plot_filtergaussian_distribution(self.liedataframe, ellipse=self._ellipse,
                                                        confidence=self.settings.confidence, *args, **kwargs)
            else:
                logger.warning(
                    "No multivariate Gaussian distribution analysis performed yet. Use the filter method first")
                return None
        else:
            return self.liedataframe.plot(kind=kind, *args, **kwargs)
