# -*- coding: utf-8 -*-

import logging
import pandas
import os
import time
import getpass
import StringIO

from .. import pylie_config
from ..model.scandataframe import LIEScanDataFrame
from ..filters.filtersplines import FilterSplines
from ..filters.filtergaussian import FilterGaussian

logger = logging.getLogger('pylie')


class FilterWorkflow(object):
    """
    Premade workflow for filtering LIE datasets using various filtering methods.

    :param data: Input DataFrames.
    :ptype data: LIEMDFrame or LIEDataFrame, single item or list
    """

    def __init__(self, data, **kwargs):

        # Store original dataframe(s) and list of processed dataframe(s)
        self._orig_data = data
        self._processed = []

        # Get copy of the global configuration for this class
        self.settings = pylie_config.get(instance=[type(self).__name__, 'FilterGaussian'])
        self.settings.update(kwargs)

        # Cast all input objects to a list
        if not isinstance(self._orig_data, list):
            self._orig_data = [self._orig_data]

        # Prepare the report
        self._report = StringIO.StringIO()
        self._report_config = StringIO.StringIO()
        self._print_header()

        # For each object: choose filter based on mdframe or dataframe types
        self._mdframe_import_count = 0
        self._dataframe_import_count = 0
        for lieobject in self._orig_data:
            object_type = getattr(lieobject, '_class_name', None)
            if object_type == 'mdframe':
                averaged = self._filterMDFrame(lieobject)
                self._processed.append(averaged)
                self._mdframe_import_count += 1
            elif object_type == 'dataframe':
                self._processed.append(lieobject)
                self._dataframe_import_count += 1

        if len(self._processed) > 1:
            self._combined = pandas.concat(self._processed, ignore_index=True)
        else:
            self._combined = self._processed[0]

        # Sort the dataframe on case and poses
        self._combined.sort_values(by=['case', 'poses'])

        self.result = self._filterLIEDataFrame(self._combined)

    @property
    def report(self):
        self._report.write('\n{0}\n'.format('-' * 100))
        self._report.write('Workflow configuration:\n')
        self._report.write(self._report_config.getvalue())
        return self._report.getvalue()

    def _format_settings(self, settings, module=''):
        self._report_config.write('\n{0}\n'.format(module))
        for key, value in settings.items():
            self._report_config.write('- {0}: {1}\n'.format(key, repr(value)))

    def _print_header(self):
        self._report.write('=' * 100 + '\n')
        self._report.write("LIE dataset filter workflow\n- Date: {0}\n- folder: {1}\n- User: {2}\n".format(time.ctime(),
                                                                                                           os.getcwd(),
                                                                                                           getpass.getuser()))
        self._report.write('=' * 100 + '\n')

    def _filterLIEDataFrame(self, lieobject):
        """
        Run filter methods on LIEDataFrame objects
        """

        filter_summary = pandas.DataFrame(lieobject[['case', 'poses']])
        filters_used = []
        usermessages = []

        # Perform multivariate Gaussian distribution filtering for the Van der
        # Waals and Coulomb energy pairs
        if self.settings['doFilterGaussian']:
            gaussian = FilterGaussian(lieobject, confidence=self.settings.confidence)
            lieobject = gaussian.filter()

            # Register outliers in summary DataFrame
            filter_summary['filter_gaussian'] = lieobject['filter_mask']

            # Make plot if requested
            if self.settings['plotFilterGaussian']:
                fig = gaussian.plot(kind='distribution')
                fig.savefig('gaussian_distribution_filter.pdf')

            # For reporting
            filters_used.append('filter_gaussian')
            usermessages.append('Filter_gaussian note: The multivariate Gaussian filter operates on a per-pose basis')
            self._format_settings(gaussian.settings, module='Multivariate Gaussian VdW and Coulomb filter')

        # Perform alpha/beta scan based filtering
        if self.settings['doFilterAlphaBetaScan']:
            abscan = LIEScanDataFrame()
            abscan.scan(lieobject)
            outliers = abscan.outliers

            # Check how many cases are filtered out. Set warning if more than 50%
            frac_outliers = len(outliers) / float(len(abscan.cases))
            if frac_outliers > 0.5:
                usermessages.append(
                    'Filter_scan note:     Using a correlation variance cutoff of {0:.2f}, {1}%% of the cases are marked as outlier'.format(
                        abscan.settings['outlier_cutoff'], frac_outliers * 100))

            # Register outliers in summary DataFrame
            filter_summary['filter_scan'] = 0
            filter_summary.loc[filter_summary['case'].isin(outliers['case'].values), 'filter_scan'] = 1

            if self.settings['plotFilterAlphaBetaScan']:
                fig = abscan.plot(kind='optimal')
                fig.savefig('alphabetascan_optimal_filter.{0}'.format(self.settings['plotFileType']))
                fig = abscan.plot(kind='error')
                fig.savefig('alphabetascan_error_filter.{0}'.format(self.settings['plotFileType']))
                fig = abscan.plot(kind='density', utol=5, ltol=-5)
                fig.savefig('alphabetascan_density_filter.{0}'.format(self.settings['plotFileType']))

            # For reporting
            filters_used.append('filter_scan')
            usermessages.append('Filter_scan note:     The alpha-beta scan filter operates on a per-case basis')
            self._format_settings(abscan.settings, module='Alpha Beta Scan filter')

        # Calculate overall filter statistics and report to used
        if filters_used:
            filter_summary['filter_total'] = filter_summary[filters_used].sum(axis=1)
            filter_outlier = filter_summary[filter_summary['filter_total'] > 0]

            if not filter_outlier.empty:

                # Check if there are cases for wich all or all but one poses are marked outlier
                for case in filter_outlier['case'].unique():
                    orig_pose_count = lieobject.loc[lieobject['case'] == case, 'poses'].count()
                    filter_pose_count = filter_outlier.loc[filter_outlier['case'] == case, 'poses'].count()

                    if orig_pose_count == filter_pose_count:
                        self._report.write(
                            "Case {0}: All of the {1} poses are marked as outlier by one or more filter methods.\n".format(
                                case, orig_pose_count))
                    elif orig_pose_count - filter_pose_count == 1:
                        self._report.write(
                            "Case {0}: Only 1 of {1} poses left after filtering. It may not be wise to use this case in a Boltzmann weighted LIE calculation\n".format(
                                case, orig_pose_count))

                self._report.write(filter_outlier.to_string())
                self._report.write('\n\n{0}'.format("\n".join(usermessages)))
            else:
                self._report.write('Good news: no outliers detected\n')

        return lieobject

    def _filterMDFrame(self, lieobject):
        """
        Run filter methods on LIEMDFrame
        """

        # Perform detection of possible transition states in the MD frames and
        # select stable regions
        if self.settings['doFilterSplines']:

            # Spline filter all data columns
            splines = FilterSplines(lieobject)
            filtered_lieobject = splines.filter()

            # Check for presence a stable unbound simulation.
            # We expect this to be the case, otherwise it makes no sense to do LIE.
            if len({'vdw_unbound', 'coul_unbound'}.difference(set(filtered_lieobject.columns))):
                logger.error(
                    "FilterSplines: No unbound Van der Waals or Coulomb energies in LIEMDFrame instance. Excluding case {0}".format(
                        lieobject.cases))
                return

            grad_unbound = filtered_lieobject.loc[
                               filtered_lieobject['filter_vdw_unbound'] == 0, 'filter_vdw_unbound'].count() + \
                           filtered_lieobject.loc[
                               filtered_lieobject['filter_coul_unbound'] == 0, 'filter_coul_unbound'].count()
            unbound_tolerance = filtered_lieobject['frame'].count() * 2 * self.settings['stable_unbound_md_tolerance']
            if grad_unbound <= unbound_tolerance:
                logger.warn(
                    "FilterSplines: more than tolerated unstable regions found for the unbound ligand case. Please check MD. ({0} unstable of total {1} frames. Tolerance {2})".format(
                        grad_unbound, filtered_lieobject['frame'].count(), self.settings['stable_unbound_md_tolerance']))

            if self.settings['plotFilterSplines']:
                splines.plot(filetype="png")

            # Assign filter set to lieobject again
            lieobject = filtered_lieobject.inliers(method=self.settings['FilterSplinesInlierMethod'])

            columns = lieobject.get_columns('vdw_*bound*')
            columns.extend(lieobject.get_columns('coul_*bound*'))
            for column in columns:
                sel = lieobject[column][~lieobject[column].isnull()]
                if len(sel):
                    logger.info("Selected frames for case: {0}, energy term: {1}. Frame: {2} - {3} ({4} datapoints)".format(
                        lieobject.cases[0], column,
                        int(lieobject.loc[sel.index[0], 'frame']), int(lieobject.loc[sel.index[-1], 'frame']), len(sel)))
                else:
                    logger.warn("No stable energy trajectory found for case {0}, energy term {1}".format(
                        lieobject.cases[0], column))

            # Report the used spline fitting parameters once in the report
            if self._mdframe_import_count == 0:
                self._format_settings(splines.settings, module='MD trajectory spline fitting')

        average = lieobject.get_average()
        average.case = lieobject.cases[0]

        return average
