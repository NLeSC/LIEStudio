# -*- coding: utf-8 -*-

import logging
import re

from pandas import DataFrame, Series

from .. import plotting
from .. import pylie_config

logger = logging.getLogger('pylie')

DEFAULT_LIE_COLUMN_NAMES = {'case': 'case',
                            'poses': 'poses',
                            'filter_mask': 'filter_mask',
                            'train_mask': 'train_mask',
                            'ref_affinity': 'ref_affinity',
                            'vdw_unbound': 'vdw_unbound',
                            'coul_unbound': 'coul_unbound',
                            'vdw_bound': 'vdw_bound',
                            'coul_bound': 'coul_bound'}


class _Common(object):
    """
    Methods common to all Pandas DataFrame and Series extensions
    """

    @property
    def size(self):
        """
        Provide backwards compatibility with older versions of Pandas that do not
        have the size attribute
        """

        shape = self.shape
        if len(shape) == 1:
            return shape[0]
        else:
            return shape[0] * shape[1]

    def __finalize__(self, other, method=None, **kwargs):
        """
        Propegate the _metadata dictionary attribute from the other class instance
        to the new one. These concern all the attributes that the custom DataFrame
        or Series class may have declared.

        Calls _init_custom_finalize to allow customomization of the class just
        after the __init__ method is called. Can be overloaded by custom classes.
        """

        if getattr(other, '_metadata', None):
            object.__setattr__(self, '_metadata', getattr(other, '_metadata', None))

        self._init_custom_finalize(**kwargs)
        return self

    def _init_custom_finalize(self, **kwargs):
        """
        This is the last method called in the creation of a new DataFrame or Series
        object.
        This is a placeholder method that can be overloaded by custom classes to
        perform pre-processing on the data in the class instance prior to returning
        the newly created instance.
        """

        pass

    def _init_plot_functions(self):
        """
        Initiate general and class specific plot functions at class initiation.
        Only called at first time class initiation to allow the user edit the
        plotting function dictionary (plot_functions attribute) with custom
        plotting functions.
        """

        pfunc = ['plot_general_']
        if hasattr(self, '_class_name'):
            pfunc.append('plot_{0}_'.format(self._class_name))

        for func in dir(plotting):
            for n in pfunc:
                if func.startswith(n):
                    func_name = func.replace(n, '')
                    if not func_name in self.plot_functions:
                        self.plot_functions[func_name] = getattr(plotting, func)

    def get_columns(self, columns, regex=False, flags=0):
        """
        Get columns with wildcard support.

        :param columns: column(s) to search for
        :type columns:  :py:str
        :param regex:   regular expression match
        :type regex:    :py:bool
        :param flags:   optional flags for the regular expression engine
        :return:        list of matching column names or empty list
        :rtype:         :py:list
        """

        if not isinstance(columns, list):
            columns = [columns]

        result = []
        for column in columns:
            if regex:
                pattern = re.compile(column, flags=flags)
                result.extend([col for col in self.columns if pattern.match(col)])
            elif '*' in column:
                pattern = re.compile('^{0}'.format(column.replace('*', '.*')), flags=flags)
                result.extend([col for col in self.columns if pattern.search(col)])
            elif column in self.columns:
                result.append(column)
            else:
                pass

        return result


class LIESeriesBase(_Common, Series):
    _class_name = 'series'
    _column_names = DEFAULT_LIE_COLUMN_NAMES

    def __init__(self, *args, **kwargs):

        for meta in ('_metadata', 'plot_functions'):
            if meta not in self.__dict__:
                self.__dict__[meta] = {}

        for colname in [var for var in kwargs if var in self._column_names]:
            self._column_names[colname] = kwargs[colname]
            kwargs.pop(colname)

        super(LIESeriesBase, self).__init__(*args, **kwargs)

        # Register plotting functions for custom series.
        self._init_plot_functions()

    def __setattr__(self, key, value):

        if not hasattr(self, key) and not key == 'plot_functions':
            self._metadata[key] = value

        super(LIESeriesBase, self).__setattr__(key, value)

    @property
    def _can_hold_na(self):
        return False

    @property
    def _constructor(self):
        """
        Ensure that the new DataFrame is always of type LIESeriesBase
        Should be overloaded by the class that inherits from LIESeriesBase.
        """

        return LIESeriesBase

    def _wrapped_pandas_method(self, mtd, *args, **kwargs):
        """
        Wrap a generic pandas method to ensure it returns a LIESeries
        """

        val = getattr(super(LIESeriesBase, self), mtd)(*args, **kwargs)
        if type(val) == Series:
            val.__class__ = LIESeriesBase
        return val

    def __getattr__(self, key):
        if key in self._metadata:
            return self._metadata[key]
        return super(LIESeriesBase, self).__getattr__(key)

    def __getitem__(self, key):
        return self._wrapped_pandas_method('__getitem__', key)

    def sort_index(self, *args, **kwargs):
        return self._wrapped_pandas_method('sort_index', *args, **kwargs)

    def take(self, *args, **kwargs):
        return self._wrapped_pandas_method('take', *args, **kwargs)

    def select(self, *args, **kwargs):
        return self._wrapped_pandas_method('select', *args, **kwargs)

    def plot(self, *args, **kwargs):
        """
        Extends the default Pandas DataFrame plot method with new plot types
        stored in the class plot_functions dictionary initiated by the
        _init_plot_functions at first class initiation.

        The functions registered in the plot_functions dictionary of the class
        may be changed/extended if needed. They should be able to accepted at
        minimum the class DataFrame as first argument and any number of additional
        arguments and keyword arguments using *args and **kwargs.
        The function should return a matplotlib plot axis.

        :param args:   any additional argument passed to the plot function
        :param kwargs: any additional keyword argument passed to the plot function
        :return:       matplotlib plot axis
        """

        kind = kwargs.get('kind', None)
        if kind and kind in self.plot_functions:
            return self.plot_functions[kind](self, *args, **kwargs)
        else:
            return super(LIESeriesBase, self).plot(*args, **kwargs)


class LIEDataFrameBase(_Common, DataFrame):
    _class_name = 'dataframe'
    _column_names = DEFAULT_LIE_COLUMN_NAMES

    def __init__(self, *args, **kwargs):
        """
        Overload class __init__

        Calls the parent DataFrame __init__ method.
        Registers any custom column header names the user may have provided.
        Initiate default columns in case not yet available and ensures that the
        default values for the train and filter columns are set to 0 instead of NaN.
        """

        for meta in ('_metadata', 'plot_functions'):
            if meta not in self.__dict__:
                self.__dict__[meta] = {}

        for colname in [var for var in kwargs if var in self._column_names]:
            self._column_names[colname] = kwargs[colname]
            kwargs.pop(colname)

        super(LIEDataFrameBase, self).__init__(*args, **kwargs)

        # Init default data columns only at first init
        if self.empty:
            for col in self._column_names.values():
                self[col] = 0
            if 'parent' not in self._metadata:
                self._metadata['parent'] = self

        # Ensure the train and filter masks are filled with 0's instead of NaN
        for col in ('train_mask', 'filter_mask'):
            if self._column_names.get(col, col) in self.columns:
                self[self._column_names.get(col, col)].fillna(0, inplace=True)

        # Register plotting functions for custom dataframes.
        self._init_plot_functions()

        # Get copy of the global configuration for this class once so the user
        # can modify the configuration dict later
        # TODO: Even new classes get populated with base class instance so all the
        #       metadata also gets inherited from base (like settings)
        self.settings = pylie_config.get(instance=type(self).__name__)

    def __getattr__(self, key):
        """
        Overload class __getattr__
        """

        if key in self._metadata:
            return self._metadata[key]
        return super(LIEDataFrameBase, self).__getattr__(key)

    def __setattr__(self, key, value):
        """
        Overload class __setattr__
        """

        # This causes: UserWarning: Pandas doesn't allow columns to be created via a new attribute name
        # if not hasattr(self, key) and not key == 'plot_functions':

        if not hasattr(self, key):
            self._metadata[key] = value
        super(LIEDataFrameBase, self).__setattr__(key, value)

    def _sanitize_cases(self, cases):
        """
        Sanitize provided list of case ID's or case-pose combinations

        For every case ID or case-pose combination check if it is in the
        DataFrame and store the indices. Remove duplicates and report missing
        cases.

        :param cases: list of case ID's or case-pose combinations to sanitize
        :type cases:  :py:list
        :return:      list of DataFrame indices
        :rtype:       :py:list
        """

        # If cases is a Pandas Series
        if getattr(cases, '_class_name', None) == 'series':
            cases = list(cases.values)

        selected_indices = []
        cases_not_found = []
        poses_not_found = []
        df_cases = self['case'].values.astype(int)
        for item in cases:

            # Item is a case
            if isinstance(item, int):
                if item in df_cases:
                    selected_indices.extend(self.loc[self['case'] == item].index.values)
                else:
                    cases_not_found.append(item)

            # Item is a case-pose combination
            if isinstance(item, tuple) and len(item) == 2:
                sel = self.loc[(self['case'] == item[0]) & (self['poses'] == item[1])]
                if sel.empty:
                    poses_not_found.append(item)
                else:
                    selected_indices.extend(sel.index.values)

        if cases_not_found:
            logger.error('Cases not in dataframe: {0}'.format(str(cases_not_found).strip('[]')))
        if poses_not_found:
            pstring = ['{0}-{1}'.format(*p) for p in poses_not_found]
            logger.error('Case-pose combination not in dataframe: {0}'.format(', '.join(pstring)))

        return set(selected_indices)

    @property
    def _constructor(self):
        """
        Ensure that the new DataFrame is always of type LIEDataFrameBase.
        Should be overloaded by the class that inherits from LIEDataFrameBase.
        """

        return LIEDataFrameBase

    @property
    def cases(self):
        """
        Return a unique list of case ID's in the current LIEDataFrame.

        :return: list of case ID's in the LIEDataFrame
        :rtype:  :py:list
        """

        if self._column_names['case'] in self.columns:
            cases = list(set(self[self._column_names['case']].values.astype(int)))
            return sorted(cases)

    @property
    def casepose(self):
        """
        Return a unique list of case ID - pose combinations in the current
        LIEDataFrame.

        :return: list of cae ID - pose tuples
        :rtype:  :py:list
        """

        if self._column_names['case'] in self.columns and self._column_names['poses'] in self.columns:
            return zip(self['case'].values.astype(int), self['poses'].values)

    @property
    def trainset(self):
        """
        Return new LIEDataFrame with all cases labeled as train cases.
        This equals all cases with an integer value higher than 0 in the
        train_mask column.

        :return: new LIEDataFrame with training set cases
        :rtype:  LIEDataFrame
        """

        if 'train_mask' in self.columns:
            return self[self['train_mask'] > 0]

    @property
    def testset(self):
        """
        Return new LIEDataFrame with all cases labeled as test cases.
        This equals all cases with an integer value of 0 in the train_mask
        column.

        Method is exposed as property with associated setter menthod

        :return: new LIEDataFrame with test set cases
        :rtype:  LIEDataFrame
        """

        if 'train_mask' in self.columns:
            return self[self['train_mask'] == 0]

    @trainset.setter
    def trainset(self, cases):
        """
        Train set property setter method.

        :param cases: list of cases to label as training set
        :type cases:  :py:list
        """

        if 'train_mask' in self.columns:
            cp_indices = self._sanitize_cases(cases)
            self.loc[cp_indices, 'train_mask'] = 1

    @testset.setter
    def testset(self, cases):
        """
        Test set property setter method.

        :param cases: list of cases to label as test set
        :type cases:  :py:list
        """

        if self._column_names['train_mask'] in self.columns:
            cp_indices = self._sanitize_cases(cases)
            self.loc[cp_indices, 'train_mask'] = 0

    @property
    def outliers(self):
        """
        Return new LIEDataFrame with all cases labeled as outlier.
        This equals all cases with an integer value higher than 0 in the
        filter_mask column.

        Method is exposed as property with associated setter method

        :return: new LIEDataFrame with outlier cases
        :rtype:  LIEDataFrame
        """

        if 'filter_mask' in self.columns:
            return self[self['filter_mask'] > 0]

    @property
    def inliers(self):
        """
        Return new LIEDataFrame with all cases labeled as inliers.
        This equals all cases with an integer value of 0 in the  filter_mask
        column.

        Method is exposed as property with associated setter method

        :return: new LIEDataFrame with outlier cases
        :rtype:  LIEDataFrame
        """

        if 'filter_mask' in self.columns:
            return self[self['filter_mask'] == 0]

    @outliers.setter
    def outliers(self, cases):
        """
        Outliers property setter method.

        :param cases: list of cases to label as outlier
        :ptype cases: list
        """

        if self._column_names['filter_mask'] in self.columns:
            cp_indices = self._sanitize_cases(cases)
            self.loc[cp_indices, 'filter_mask'] = 1

    @inliers.setter
    def inliers(self, cases):
        """
        Inliers property setter method.

        :param cases: list of cases to label as inliers
        :ptype cases: list
        """

        if self._column_names['filter_mask'] in self.columns:
            cp_indices = self._sanitize_cases(cases)
            self.loc[cp_indices, 'filter_mask'] = 0

    def reset_trainset(self, train=False):
        """
        Reset the train mask to 0 (everything test set) or 1
        (everything train set).

        :param train: reset everything to train set
        :type train:  :py:bool
        """

        if self._column_names['train_mask'] in self.columns:
            self['train_mask'] = int(train)

    def reset_outliers(self, inlier=False):
        """
        Reset the outlier mask to 0 (everything inlier) or 1
        (everything outlier).

        :param inlier: reset everything to be inlier
        :type inlier:  :py:bool
        """

        if self._column_names['filter_mask'] in self.columns:
            self['filter_mask'] = int(inlier)

    def get_cases(self, cases):
        """
        Convenience method for quick selection of cases in the LIEDataFrame.
        Returns and empty DataFrame if no match

        :param cases: list of case ID's to select
        :type cases:  :py:list
        :return:      New LIEDataFrame representing selected cases
        :rtype:       LIEDataFrame
        """

        cp_indices = self._sanitize_cases(cases)
        return self.loc[cp_indices, :]

    def get_poses(self, case_pose_list):
        """
        Convenience method for quick selection of case-pose combinations in
        the LIEDataFrame.
        Returns and empty DataFrame if no match

        :param case_pose_list: list of case ID, pose ID tuples
        :type case_pose_list:  :py:list
        :return:               New LIEDataFrame representing selected cases
        :rtype:                LIEDataFrame
        """

        cp_indices = self._sanitize_cases(case_pose_list)
        return self.loc[cp_indices, :]

    def plot(self, *args, **kwargs):
        """
        Extends the default Pandas DataFrame plot method with new plot types
        stored in the class plot_functions dictionary initiated by the
        _init_plot_functions at first class initiation.

        The functions registered in the plot_functions dictionary of the class
        may be changed/extended if needed. They should be able to accepted at
        minimum the class DataFrame as first argument and any number of additional
        arguments and keyword arguments using *args and **kwargs.
        The function should return a matplotlib plot axis.

        :param args:   any additional argument passed to the plot function
        :param kwargs: any additional keyword argument passed to the plot function
        :return:       matplotlib plot axis
        """

        kind = kwargs.get('kind', None)
        if kind and kind in self.plot_functions:
            return self.plot_functions[kind](self, *args, **kwargs)
        else:
            return super(LIEDataFrameBase, self).plot(*args, **kwargs)
