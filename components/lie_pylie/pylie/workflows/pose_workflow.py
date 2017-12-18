# -*- coding: utf-8 -*-

import logging
import time
import os
import getpass

from .. import pylie_config
from .. import LIEScanDataFrame

logger = logging.getLogger('pylie')


class PoseWorkflow(object):
    """
    Premade workflow for seperating ligand poses based on their propensity
    distribution in the parameter scan.
    If poses have a high propensity in different regions of parameter space
    that are nevertheless close together, they are seperated creating a
    fictive new ligand

    Settings:
    Class aggregates settings from LIEScanDataFrame.

    :param data: Input LIE DataFrame.
    :ptype data: LIEDataFrame
    """

    def __init__(self, data, **kwargs):

        # Store original dataframe(s) and list of processed dataframe(s)
        self.data = data

        # Get copy of the global configuration for this class
        self.settings = pylie_config.get(instance=[type(self).__name__, 'LIEScanDataFrame'])
        self.settings.update(kwargs)

        # Run alpha/beta parameter scan and return propensity distributions
        self.prob_dist = self._init_clusters()

        # Seperate cases based on propensities
        self._init_propensity_filtering()

    def _init_clusters(self):
        """
        Create initial clusters based on an alpha/beta scan.
        Scan and clustering setting may be altered using the LIEScanDataFrame settings.
        """

        # Prepare scan
        abscan = LIEScanDataFrame()
        abscan.settings.update(self.settings())
        abscan.scan(self.data)

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

        return abscan.propensity_distribution()

    def _init_propensity_filtering(self):
        """
        Make new dataframe marking all unsignificant poses as outliers if any
        and all cases that have both ascending and descending poses, create new
        case for descending pose. If new pose is created and there are poses with
        stable probabilities, replicate these for the new case.
        """

        desc_cases = [int(n) for n in self.prob_dist.loc[self.prob_dist['tag'] == 1, 'case'].unique()]
        ascn_cases = [int(n) for n in self.prob_dist.loc[self.prob_dist['tag'] == 2, 'case'].unique()]
        diff_cases = list(set(desc_cases).symmetric_difference(set(ascn_cases)))

        for idx, x in self.prob_dist.iterrows():
            tag = int(x.tag)
            case = int(x.case)
            p = int(x.pose)
            if tag == 0:
                pose = self.data[(self.data['case'] == case) & (self.data['poses'] == p)].index
                self.data.ix[pose, 'filter_mask'] = 1
            elif tag == 1 and case in ascn_cases:
                pose = self.data[(self.data['case'] == case) & (self.data['poses'] == p)].index
                self.data.ix[pose[0], 'case'] = self.data.loc[pose[0], 'case'] + 1000
            elif tag == 3 and case in ascn_cases:
                pose = self.data[(self.data['case'] == case) & (self.data['poses'] == p)]
                newpose = pose.copy()
                newpose['case'] = newpose['case'] + 1000
                self.data = self.data.append(newpose, ignore_index=True)

        # Report: cases with probabilities that are either ascending or descending
        print('=' * 100 + '\n')
        print("LIE dataset pose probability filter workflow\n- Date: {0}\n- folder: {1}\n- User: {2}\n".format(
            time.ctime(), os.getcwd(), getpass.getuser()))
        print('{0}\n'.format('-' * 100))

        print("Cases with descending probabilities are marked '1', cases with ascending probabilities marked as '2',\n\
        insignificant cases below a cutoff of {0:.3f} marked '0' if prob_report_insignif equals True.\n\
        Stable probabilities marked as '3'.\n".format(self.settings['prob_insignif_cutoff']))

        print("Descending cases:\n {0}".format(str(desc_cases).strip('[]')))
        print("Ascending cases :\n {0}".format(str(ascn_cases).strip('[]')))
        print("Difference      :\n {0}\n".format(str(diff_cases).strip('[]')))

        print self.prob_dist.to_string()

        print('\n{0}\n'.format('-' * 100))
        print('Workflow configuration:')
        for key, value in self.settings.items():
            print('- {0}: {1}'.format(key, repr(value)))
        print('=' * 100 + '\n')
