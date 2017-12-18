# -*- coding: utf-8 -*-

import logging
import re

from pandas import isnull, DataFrame

from ..methods.fileio import read_gromacs_energy_file
from ..model.liebase import LIEDataFrameBase
from ..model.liedataframe import LIEDataFrame
from ..model.lieseries import LIESeries

logger = logging.getLogger('pylie')

DEFAULT_MD_COLUMN_NAMES = {'case': 'case',
                           'frame': 'frame',
                           'time': 'time',
                           'ref_affinity': 'ref_affinity'}


class LIEMDFrame(LIEDataFrameBase):
    """
    LIEMDFrame class

    DataFrame that represents the molecular dynamics data that servers as the
    source data for LIE calculations. Primarily these consist of the delta Van
    der Waals and Coulomb energy values between ligand and its surrounding for
    all time steps of a simulation. The surrounding usually is either the solvent
    or a protein.
    """

    _class_name = 'mdframe'
    _column_names = DEFAULT_MD_COLUMN_NAMES

    def __getitem__(self, key):

        if isinstance(key, str):
            key = self._column_names.get(key, key)

        result = super(LIEMDFrame, self).__getitem__(key)
        if isinstance(key, str):
            result.__class__ = LIESeries
        elif isinstance(result, LIEDataFrameBase):
            result.__class__ = LIEMDFrame

        return result

    @property
    def poses(self):
        """
        Extract pose numbers from headers

        :return: poses
        :rtype:  :py:list
        """

        poses = [int(re.sub('\D+', '', p)) for p in self.get_columns('vdw_bound*')]
        return sorted(poses)

    @property
    def _constructor(self):
        """
        Ensure that the new DataFrame is always of type LIEMDFrame
        """

        return LIEMDFrame

    def calc_deltaE(self):
        """
        Calculate deta-delta Van der Waals and Coulomb energies
        """

        if 'vdw_unbound' not in self.columns and 'coul_unbound' not in self.columns:
            logger.error('No unbound energy values for vdw and coul in dataframe')
            return

        poses = self.poses
        for pose in poses:
            self['vdw_{0}'.format(pose)] = self['vdw_bound_{0}'.format(pose)].sub(self['vdw_unbound'], axis=0)
            self['coul_{0}'.format(pose)] = self['coul_bound_{0}'.format(pose)].sub(self['coul_unbound'], axis=0)

        logger.debug("Case {0} calculate delta-delta energy for {0} poses".format(self.cases[0], len(poses)))

    def inliers(self, method=None):
        """
        Return MD frames assigned as 'inliers' by a filter method or manual
        assignment.
        Inliers can be assigned in three different ways:

        * single: return inliers for each column separately. This may result
                  in a coulomb/VdW energy pair having one of both energy
                  values set to Nan because it was assigned as outlier.
        * pair:   Ensure that a coulomb/VdW pair is assigned inlier only if
                  both energy values are inlier.
        * global: Assign inlier if all poses for a given frame count have their
                  coulomb/VdW energy pairs assigned as inlier.

        :param method:  method for assigning inliers
        :type method:   :py:str

        :return:        LIEMDFrame
        """

        df_copy = self.copy()
        filter_cols = self.get_columns('filter_*')
        method = method or self.settings.inlierFilterMethod

        if not len(filter_cols):
            return df_copy

        # Method 'single', only set source column of corresponding filter column to
        # None for filtered items.
        if method == 'single':
            for col in filter_cols:
                source = [s for s in self.columns if col.strip('filter_') in s]
                source.remove(col)
                for data_col in source:
                    df_copy.loc[df_copy[col] > 0, data_col] = None
                df_copy.loc[df_copy[col] > 0, col] = None

        # Method 'pair', for a vdw/coul pair, set the source data to None if the
        # filter data for both items in the pair > 0
        if method == 'pair':
            poses = self.poses
            for pose in poses:
                pair = [n for n in filter_cols if str(pose) in n]
                if len(pair) == 2:
                    source = []
                    for p in pair:
                        source.extend([s for s in self.columns if p.strip('filter_') in s])
                        source.remove(p)
                    for data_col in source:
                        df_copy.loc[(df_copy[pair[0]] > 0) | (df_copy[pair[1]] > 0), data_col] = None
                    df_copy.loc[(df_copy[pair[0]] > 0) | (df_copy[pair[1]] > 0), pair] = None

        # Method 'global', select set for which all filter columns equal 0
        if method == 'global':
            df_copy = df_copy[df_copy[filter_cols].sum(axis=1) == 0]

        return df_copy

    def get_average(self, keepnull=False):
        """
        Get mean values for Van der Waals and Coulomb energies in de dataframe

        If a filter column is available for a vdw/coul pair, only the inliers are
        used for the calculation
        """

        # Check if the delta-delta Evdw and Ecoul have been calculated else do so
        # still.
        pose_indexes = self.poses
        pose_headers = ['vdw_{0}'.format(p) for p in pose_indexes]
        pose_headers.extend(['coul_{0}'.format(p) for p in pose_indexes])
        if set(pose_headers).intersection(set(self.columns)) != set(pose_headers):
            self.calc_deltaE()

        # Calculate the averages. It's up to the user to get the filtered set using
        # the inlier method
        averages = self.mean()

        # Check for Nan in unbound columns.
        if not averages['coul_unbound'] or not averages['vdw_unbound']:
            logger.error('Case {0}, no average unbound Coulomb and Van der Waals energies'.format(self.cases[0]))
            return None

        # Filter poses for Nan values in either vdw or coul energies
        poses = self.poses
        if not keepnull:
            filtered_poses = []
            for pose in poses:
                if isnull(averages['coul_bound_{0}'.format(pose)]) or isnull(averages['vdw_bound_{0}'.format(pose)]):
                    logger.warn(
                        'Case {0}, discard pose {1}: no average Coulomb or Van der Waals energies'.format(self.cases[0],
                                                                                                          pose))
                    continue
                filtered_poses.append(pose)
            poses = filtered_poses

        # Collect Data in new frame
        data = {'coul_unbound': averages['coul_unbound'],
                'vdw_unbound': averages['vdw_unbound'],
                'coul_bound': [averages['coul_bound_{0}'.format(b)] for b in poses if averages['coul_bound_{0}'.format(b)]],
                'vdw_bound': [averages['vdw_bound_{0}'.format(b)] for b in poses if averages['vdw_bound_{0}'.format(b)]],
                'vdw': [averages['vdw_{0}'.format(b)] for b in poses if averages['vdw_{0}'.format(b)]],
                'coul': [averages['coul_{0}'.format(b)] for b in poses if averages['coul_{0}'.format(b)]],
                'poses': poses,
                'case': averages.get('case', 0),
                'filter_mask': 0,
                'train_mask': 0,
                'ref_affinity': averages.get('ref_affinity', 0),
                }

        dataframe = LIEDataFrame(data)
        return dataframe

    def get_poses(self, poses):
        """
        Convenience method for quick selection of poses from a LIEMDFrame

        :param poses: list of pose ID's
        :type poses:  :py:list
        :return:      New LIEMDFrame representing selected cases
        :rtype:       LIEMDFrame
        """

        columns = self._column_names.keys()
        for pose in poses:
            columns.extend([h for h in self.columns if h.endswith('_{0}'.format(pose))])

        return self[columns]

    def get_stable(self, pose):
        """
        For the energy values of a pose trajectory return the region assigned
        as 'inlier' as tuple of number of frames, start frame and end frame.

        :param pose: pose for which to return stable regions
        :return:     dictionary of energy column name and tuple
        :type:       :py:dict
        """

        filter_cols = self.get_columns('filter_*_*_{0}'.format(pose))
        if not filter_cols:
            logger.warn('No filter column found for pose {0}'.format(pose))

        data = {}
        for fc in filter_cols:
            stripped = fc.strip('_{0}'.format(pose))
            sel = self.loc[self[fc] == 0, 'frame'].values
            data[stripped.strip('filter_')] = (len(sel), int(min(sel)), int(max(sel)))

        return data

    def set_stable(self, column, start, end):
        """
        (re)set a region of a energy trajectory as stable by defining the
        start and end frame of the region for a given column.

        :param column:  column to set stable region for
        :type column:   :py:str
        :param start:   start frame
        :type start:    :py:int
        :param end:     end frame
        :type end:      :py:int
        """

        column = 'filter_{0}'.format(column.strip('filter_'))
        if not column in self.columns:
            logger.error('No column with name {0}'.format(column))
            return column

        # Check if start and end frame defined
        if start in self['frame'] and end in self['frame']:

            # Reset the filter column
            self[column] = 1

            # Set new region
            start = self.loc[self['frame'] == start].index[0]
            end = self.loc[self['frame'] == end].index[0]
            self.loc[start:end, column] = 0

        else:
            logger.error('Region with start: {0} and end: {1} not contained in trajectory ({2},{3})'.format(
                start, end, int(min(self['frame'])), int(max(self['frame']))
            ))

    def from_file(self, file_or_buffer, headers, filetype='gromacs'):
        """
        Read external molecular dynamics energy files into the LIEMDFrame

        Currently supports only GROMACS MD energy files.
        MD energy files are imported as Pandas LIEMDFrame DataFrame columns.
        Class methods and external functions that use LIE based Van der Waals
        and electrostatic energy values require standardized naming of the
        data column headers. That translation is done using the `headers`
        translation dictionary.

        :param file_or_buffer: path to file or buffer.
        :param headers:        translation of trajectory file specific column
                               headers to LIEMDFrame compatible headers
        :type headers:         :py:dict
        :param filetype:       type of energy file, currently only 'gromacs'
        :type filetype:        :py:str
        :param headers:        columns selection and header translation dictionary
        :type headers:         :py:dict
        """

        # Check if translation dictionary contains proper header names
        if not any([value.startswith(('vdw_', 'coul_')) for value in headers.values()]):
            logger.error('Column header translation dictionary should contain "vdw_*" or "coul_*" names')
            return

        newframe = None
        if filetype == 'gromacs':
            newframe = read_gromacs_energy_file(file_or_buffer, columns=headers.keys(), lowercase=False)
        else:
            logger.error('File format not supported: {0}'.format(filetype))

        # Parse imported DataFrame and translate column headers
        if isinstance(newframe, DataFrame):
            for col in newframe.columns:
                self[headers.get(col,col)] = newframe[col]

        # Set a default case number
        if self['case'].isnull().all():
            self['case'] = 1

        # Check if all columns with energy values have the same number of MD frames
        # if not, issue a warning.
        if not self.empty:
            not_all_nan = self.isnull().all()
            column_counts = [self[n].count() for n in not_all_nan.index if not not_all_nan[n]]
            if len(set(column_counts)) != 1:
                logger.warn(
                    "Energy values from trajectories with unequal frame count detected. This could be intentional. File {0}".format(
                        file_or_buffer.name))
