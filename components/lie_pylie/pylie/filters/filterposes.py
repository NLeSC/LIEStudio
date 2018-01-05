# -*- coding: utf-8 -*-

import logging

from .. import pylie_config

logger = logging.getLogger('pylie')


class FilterPoses(object):

    def __init__(self, liedataframe, **kwargs):

        self.liedataframe = liedataframe.copy(deep=True)

        # Get copy of the global configuration for this class
        self.settings = pylie_config.get(instance=type(self).__name__)
        self.settings.update(kwargs)

    def filter(self):

        scan = self.liedataframe.scan()
        prob_dist = scan.propensity_distribution()

        for case in self.liedataframe.cases:

            # Select the case
            sel = prob_dist[prob_dist['case'] == case]

            # Set filter_flag of all insignificant poses to 1
            ins = sel.loc[(sel['tag'] == 0), 'pose']
            self.liedataframe.loc[
                (self.liedataframe['case'] == case) & (self.liedataframe['poses'].isin(ins.values)), 'filter_mask'] = 1

            # If there are poses having ascending and descending weight gradients in the same set, seperate
            if 1 in sel['tag'].values and 2 in sel['tag'].values:
                # Set filter_flag of poses with tag 2 to 0 in original dataframe
                ins = sel.loc[(sel['tag'] == 2), 'pose']
                self.liedataframe.loc[
                    (self.liedataframe['case'] == case) &
                    (self.liedataframe['poses'].isin(ins.values)), 'filter_mask'] = 1

                # Copy the poses with tag 2 and 3 from original dataframe and add again as new case
                ins = sel.loc[sel['tag'].isin([2, 3]), 'pose']
                newcase = self.liedataframe[
                    (self.liedataframe['case'] == case) & (self.liedataframe['poses'].isin(ins.values))].copy()
                newcase['filter_mask'] = 0
                newcase['case'] = newcase['case'] + 1000

                self.liedataframe = self.liedataframe.append(newcase, ignore_index=True)
