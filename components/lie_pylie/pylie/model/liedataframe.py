# -*- coding: utf-8 -*-

import logging
import math
import numpy
import copy

from pandas import pivot_table, DataFrame, Series

from ..methods.fileio import read_lie_etox_file
from ..methods.data import GREEK_ALPHABET
from ..model.liebase import LIEDataFrameBase
from ..model.lieseries import LIESeries

logger = logging.getLogger('pylie')


class LIEDataFrame(LIEDataFrameBase):
    """
    LIEDataFrame class

    Inherits from the LIEDataFrameBase class to provide a fully functional Pandas
    DataFrame instance with additional methods for LIE work.
    """

    _class_name = 'dataframe'

    def __getitem__(self, key):

        if isinstance(key, str):
            key = self._column_names.get(key, key)

        result = super(LIEDataFrame, self).__getitem__(key)
        if isinstance(key, str):
            result.__class__ = LIESeries
        elif isinstance(result, LIEDataFrameBase):
            result.__class__ = LIEDataFrame

        return result

    @property
    def _constructor(self):

        """
        Ensure that the new DataFrame is always of type LIEDataFrameBase
        """

        return LIEDataFrame

    def from_file(self, filepath, filetype='etox', **kwargs):

        """
        Construct LIEDataFrame from a file.

        Example:
          df = pylie.LIEDataFrame.from_file('liedata.tbl', filetype='etox')

        :param filepath: Path to file or buffer.
        :ptype filepath: mixed
        :param filetype: type of energy file, currently only 'etox'
        :ptype filetype: string
        :param kwargs  : additional keyword arguments are pased to the file importer
        """

        newframe = None
        if filetype == 'etox':
            newframe = read_lie_etox_file(filepath, **kwargs)

        if type(newframe) != type(None):
            for col in newframe.columns:
                self[col] = newframe[col]

            # Calculate VdW and Coul interaction energies for every pose
            self['vdw'] = self['vdw_bound'].sub(self['vdw_unbound'], axis=0)
            self['coul'] = self['coul_bound'].sub(self['coul_unbound'], axis=0)

    def liedeltag(self, params=None, **kwargs):
        """
        Convenience method for quick calculation of delta G using LIE.

        :param alpha:  LIE alpha scaling parameter
        :ptype alpha:  float
        :param beta:   LIE beta scaling parameter
        :ptype beta:   float
        :param gamma:  LIE gamma scaling parameter
        :ptype gamma:  float
        :param kwargs: Any keyword arguments passed to lie_deltag
        :return:       DeltaG DataFrame instance
        """

        if not params:
            params = [0.5, 0.5, 0]

        vdw = pivot_table(self, values='vdw', index=['case'], columns=['poses'])
        coul = pivot_table(self, values='coul', index=['case'], columns=['poses'])
        ref = self.groupby(['case', 'ref_affinity']).count().reset_index()['ref_affinity']

        dg_calc = lie_deltag([vdw, coul], params=params, kBt=self.settings.get('kBt', 2.49))
        dg_calc['ref_affinity'] = ref
        dg_calc['error'] = abs(dg_calc['ref_affinity'] - dg_calc['dg_calc'])

        return dg_calc

    def model(self, **kwargs):
        """
        Convenience method for quick setup of a LIE model building class and make
        an initial model

        :param kwargs: Any keyword arguments passed to LIEModelBuilder
        :return:       LIEModelBuilder class
        """

        # To prevent circular import problems
        from ..model.liemodelframe import LIEModelBuilder

        model = LIEModelBuilder(dataframe=self)
        return model.model(**kwargs)

    def pki_to_dg(self, R=8.3144621, temp=305):
        """
        Convert reference affinity data in pKi to delta G values.

        :param R: Gasconstant in J K-1 mol-1. Default = 8.3144621.
        :ptype R: float
        :param temp: Temperature in degrees Kelvin. Default = 305
        :ptype temp: float
        """

        if self._column_names['ref_affinity'] in self:
            converted = (-R * temp * self[self._column_names['ref_affinity']].apply(
                lambda x: math.log(math.pow(10, x)))) / 1000
            logger.info(
                "Converted reference affinity data from pKI to dG (datapoints: {0}, max: {1:.2f}, min: {2:.2f})".format(
                    converted.count(), converted.max(), converted.min()))
            self[self._column_names['ref_affinity']] = converted
        else:
            raise KeyError("No {0} column in dataFrame".format(self._column_names['ref_affinity']))

    def scan(self, *args, **kwargs):
        """
        Convenience method for quick setup of a Alpha/Beta parameter scan with the
        data from the current LIEDataFrame instance.

        :param args:   Any arguments passed to LIEScanDataFrame
        :param kwargs: Any keyword arguments passed to LIEScanDataFrame
        :return:       LIEScanDataFrame class
        """

        # To prevent circular import problems
        from ..model.scandataframe import LIEScanDataFrame

        abscan = LIEScanDataFrame()
        abscan.scan(self, *args, **kwargs)

        return abscan


def lie_deltag(dataset, params=[0.5, 0.5, 0], kBt=2.49, **kwargs):
    """
    Calculate free energy of binding (delta G) using the LIE equation

    This function uses a vectorized version of the LIE equation with support
    for multiple poses. The LIE equation is of the form:

      dGcalc = (S1 * D1) + (S2 * D2) +.... (Sn * Dn) + Si

    Where S is a scaling parameter, D is a data set and i is the intercept value.
    The elements for each scaling parameter, data set multiplication are drawn from
    the dataset and params list provided as input for the method.

    The scaling parameter are classically: Alpha, Beta and Gamma. Gamma serves as
    intercept which is optional.
    The data set is classically composed of the Van der Waals and Coulomb energy
    values as single value, Numpy array or Pandas DataFrame type.

    The method requires at least a D1, D2 and S1, S2. The equation can be extended
    with an arbitrary number of additional data sets, each with their own scaling
    parameter.

    Poses and cases:
    From an array point of view, separate cases are represented as rows and poses
    as columns. Columns for pose energies need to be of equals length for each
    case.
    Input for which it is ambiguous rather it is a row- or column vector will be
    cast as row vector (thus treated as cases rather then poses).

    LIE scaling parameters:
    The scaling parameters may be set to fixed values or as arrays of unique value
    for each case. The intercept value is set as one additional scaling parameter.

    Probabilities:
    Each energy term having multiple poses will be subjected to Boltzmann
    weighting by default. This behaviour can be customized by proving a list
    of booleans as 'calc_prob' argument that specifies for each energy term rather
    or not to include it in Boltzmann weighting.

    :param dataset: list of datasets to use in the LIE equation. Classicly these
                    are at least Van der Waals and Coulomb energy terms.
    :type dataset:  :py:list
    :param params:  list of scaling parameters in the LIE equation for each of the
                    terms in the dataset plus optional intercept term. By default
                    these are set to 0.5, 0.5 and 0.0 for the alpha, beta and
                    gamma scaling parameter respectivly.
    :type params:   :py:list
    :param kBt:     Boltzmann constant at given temperature. Default = 2.49
    :type kBt:      :py:float
    :param calc_prob: list of booleans specifying which of the energy terms to
                    include in Boltzmann weighting. By default True for all terms.
    :type calc_prob: :py:list
    :param param_labels: Data labels for the scaling parameters used in the
                    results DataFrame. By default set to the Greek alphabet.
    :type param_labels: :py:list
    :param data_labels: Data labels for the input datasets used in the
                    results DataFrame. By default set to 'vdw', 'coul' and 'dx'.
    :type param_labels: :py:list

    :return:        Pandas DataFrame with an array of deltaG values, the weighted
                    VdW and Coul energy values, alpha, beta and gamma values and
                    propensities for each case.
    :rtype:         :pandas:dataframe
    """

    # Function requires at least a dataset with two value sets.
    assert type(dataset) == list and len(dataset) > 1, "lie_deltag requires a list of at least two value sets."

    # Check data types. Accept Pandas DataFrame like, Numpy array or single value
    # cast all to Numpy array
    cast_dataset = []
    index_values = None
    index_name = 'case'
    for value_set in dataset:
        if type(value_set) in (DataFrame, Series) or getattr(value_set, '_class_name', None) in ('series', 'dataframe'):
            cast_dataset.append(value_set.values)
            index_values = value_set.index.values
            index_name = value_set.index.name
        elif type(value_set) == numpy.ndarray:
            if len(value_set.shape) == 1:
                value_set = value_set[numpy.newaxis, :]
            cast_dataset.append(value_set)
        elif type(value_set) in (int, float):
            cast_dataset.append(numpy.array([value_set]))
        else:
            raise TypeError("Unable to use data of type '{0}'".format(type(value_set)))

    # Check if data arrays are of equal shape
    dataset_shapes = [n.shape for n in cast_dataset]
    shape = max(dataset_shapes)
    for i, d in enumerate(cast_dataset):
        dshape = d.shape
        if dshape != shape:
            if dshape[1] != 1 and dshape[1] != shape[1]:
                raise AssertionError("Unable to cast arrays of unqual shape: {0} and {1}".format(dshape, shape))
            elif dshape[1] == 1 and dshape[1] != shape[1]:
                cast_dataset[i] = numpy.tile(d, shape[1])

    # Check if the dataset is of same length as params set. If not warn user.
    N_data = len(cast_dataset)
    N_params = len(params)
    N_intercept = 0
    if N_data > N_params:
        logger.warn(
            "There are {0} value sets in the dataset but only {1} scaling parameters. Missing parameters will be set to 1".format(
                N_data, N_params))
        params.extend([1] * (N_data - N_params))
    if N_data < N_params:
        N_intercept = N_params - N_data
        for n in range(N_intercept):
            cast_dataset.append(numpy.ones(shape))

    # Cast all scaling parameters to numpy array, ajust shape to dataset if needed
    cast_params = []
    for param_set in params:
        if type(param_set) == Series or getattr(value_set, '_class_name', None) == 'series':
            cast_params.append(param_set.values.reshape(-1, 1))
        elif type(param_set) == numpy.ndarray:
            cast_params.append(param_set.reshape(-1, 1))
        elif type(param_set) in (int, float, numpy.int64, numpy.float64):
            cast_params.append(numpy.array([[param_set]] * shape[0]))
        else:
            raise TypeError("Unable to use scaling parameter of type '{0}'".format(type(param_set)))

    # Check if param arrays and data arrays are of equal length
    paramset_length = [(n.shape[0], shape[0]) for n in cast_params]
    assert len(
        set(paramset_length)) == 1, "Scaling parameters and datasets need to be of the same length. Got: {0}".format(
        str(paramset_length).strip('[]'))

    # Create Boltzmann boolean list of Boltzmann reweighting of energy terms
    calc_prob = kwargs.get('calc_prob', None)
    if calc_prob:
        assert len(calc_prob) == len(
            cast_dataset), "custom boolean list for calculating energy probabilities not of same length as input dataset"
    else:
        calc_prob = [True] * len(cast_dataset)

    # Get column names for the results DataSet
    param_labels = kwargs.get('param_labels', GREEK_ALPHABET)
    data_labels = copy.copy(kwargs.get('data_labels', ['vdw', 'coul']))
    missing_labels = len(cast_dataset) - len(data_labels)
    if missing_labels > 0:
        data_labels.extend(['d{0}'.format(i + 1) for i in range(missing_labels)])

    # Report to user
    logger.debug(
        "Running LIE equation on: {0} cases, {1} energy terms, {2} scaling parameters, {3} intercept term(s) and up to {4} poses. kBt value of {5:.2f}".format(
            shape[0], len(dataset), len(cast_params), N_intercept, shape[1], kBt))

    # Calculate energies with initial values for scaling parameters
    energy = numpy.zeros(shape)
    for i, p in enumerate(cast_params):
        if calc_prob[i]:
            energy += (cast_dataset[i] * p)

    # Calculate exponent energies.
    exponent = numpy.exp(-energy / kBt)

    # Calculate probabilities.
    expsum = numpy.sum(numpy.nan_to_num(exponent), axis=1)
    expsum.resize(shape[0], 1)
    probabilities = exponent / expsum

    # Calculate weighted total energies
    w_energies = []
    for i, p in enumerate(cast_params):
        if calc_prob[i]:
            w_energies.append(numpy.sum(numpy.nan_to_num(cast_dataset[i] * probabilities), axis=1))
        else:
            w_energies.append(numpy.sum(numpy.nan_to_num(cast_dataset[i]), axis=1))
    w_energies = numpy.column_stack(w_energies)

    # Calculate delta G
    dg_calc = numpy.sum(w_energies * numpy.column_stack(cast_params), axis=1)

    # Return results in Pandas DataFrame. Add probabilities for each pose
    dfdict = {'dg_calc': dg_calc}
    dfdict.update(dict(
        [('w_{0}'.format(data_labels[i]), w_energies[:, i]) for i, data in enumerate(cast_dataset) if calc_prob[i]]))
    dfdict.update(dict([(param_labels[i], param.flatten()) for i, param in enumerate(cast_params)]))
    dfdict.update(dict([('prob-%i' % i, p) for i, p in enumerate(probabilities.T, start=1)]))

    if type(index_values) == numpy.ndarray:
        dfdict[index_name] = index_values
        index_values = numpy.arange(1, shape[0] + 1)
    results = LIEDataFrame(dfdict)

    return results
