# -*- coding: utf-8 -*-

import logging
import numpy

from matplotlib import pyplot
from numpy.fft import fft, ifft
from scipy.interpolate import UnivariateSpline

from .. import pylie_config

logger = logging.getLogger('pylie')


class FilterSplines(object):
    """
    FilterSplines class

    Set of functions to examine stability of molecular dynamics trajectories with
    respect to various energy terms by a series of noise reduction and spline
    fitting steps.

    The energy values in the trajectory are noise filtered using FFT transform.
    All frequencies higher than 'fftfreq' are removed.
    The filtered dataset is subjected to single or double (default) spline fitting
    followed by a gradient calculation to identify positive or negative changes in
    the gradient.

    If the detected change is larger then a pre-defined cutoff 'gradco' the change
    is marked as significant which could indicate a structure transition.
    """

    def __init__(self, liemdframe, **kwargs):
        if getattr(liemdframe, '_class_name', None) != 'mdframe':
            raise TypeError("FilterSplines requires an LIEMDFrames instance, got {0}".format(type(liemdframe)))

        # Get copy of the global configuration for this class
        self.settings = pylie_config.get(instance=type(self).__name__)
        self.settings.update(kwargs)

        # Make a deep copy of the frame
        self.liemdframe = liemdframe.copy(deep=True)

        # Store the stable regions
        self.stable = {}

    def _fft(self, data):
        """
        Run numpy FFT on the dataset. Replace all frequencies higher than fftfreq
        by 0
        """

        fftdata = fft(data)
        for i in range(len(fftdata)):
            if i >= self.settings.fftfreq:
                fftdata[i] = 0

        return fftdata

    def _fitspline(self, data):
        """
        fit splines to data
        as an option, print knots and coefficients
        """

        x = numpy.linspace(1, len(data), len(data))
        nx = UnivariateSpline(x, data, k=1, s=self.settings.splinesmooth)

        # logger.debug("Spline knots: {0}".format(",".join(["{0:.0f}".format(n) for n in nx.get_knots()])))
        # logger.debug("Spline coefficients: {0}".format(",".join(["{0:.0f}".format(n) for n in nx.get_coeffs()])))

        return nx(x)

    def _cleangrad(self, data):
        """
        replace all values below cutoff by zeroes

        NOTE: gradient values are multiplied by a gradco_mult factor to
        visually enhance the gradient when plotting.
        """

        for i in range(len(data)):
            if abs(data[i]) < self.settings.gradco:
                data[i] = 0
            else:
                data[i] = abs(data[i]) * self.settings.gradco_mult
        return data

    def _rmart(self, data):
        """
        remove data points at beginning and end of list to remove artefacts
        """

        n = int(len(data) * self.settings.gradcl)
        for i in range(len(data)):
            if i < n or i > (len(data) - n):
                data[i] = 0
        return data

    def _findstraight(self, column):
        """
        Determines the range of stable minima in the data set

        :param column: Dataset
        :ptype column: numpy array
        :return: List of minima in which a minimum is defined as (length, start
                 data point, end data point).
        :rtype:  [(int,int,int),...,(int,int,int)]
        """

        fftdata = self._fft(self.liemdframe[column].values)

        if self.settings.doublespline:
            data = self._fitspline(self._fitspline(ifft(fftdata)[:].real))
        else:
            data = ifft(fftdata)[:].real

        # Store transform
        self.liemdframe['fft_{0}'.format(column)] = data

        # Gradient on data set, remove artifacts and store
        data = self._cleangrad(numpy.gradient(data))
        data = self._rmart(data)
        self.liemdframe['grad_{0}'.format(column)] = data

        # Some logic to find straight bits and store them
        straight = True
        b = 0
        lst = []
        for i in range(len(data)):
            if data[i] != 0 and straight is True:
                straight = False
                lst.append((i - b - 1, b, i - 1))
            elif data[i] == 0 and straight is False:
                straight, b = True, i
            elif i == len(data) - 1 and straight is True:
                lst.append((i - b, b, i))

        return sorted(lst, key=lambda l: l[0], reverse=True)

    def filter(self, columns=None):
        """
        Run the FFT filtering and spline fitting workflow. By default on all columns
        for which the column name starts with vdw and coul or the column headers
        defined in the column argument list.

        If multiple stable regions are found, the first region of sufficient length
        starting from the beginning of the trajectory is selected (filter value 0).
        Other stable regions are assigned filter value 1 and non-stable regions
        filter value 2.

        :param columns: specific columns to perform filtering on
        :type columns:  :py:list
        """

        if not columns:
            columns = [n for n in self.liemdframe.columns if n.startswith(('vdw', 'coul'))]

        for column in columns:

            assert column in self.liemdframe.columns, "Column with header {0} not in dataframe".format(column)

            # Get all the straight energy tracts from the datasets
            straight_stretches = self._findstraight(column)

            # Extract all stretches that are equal to or larger then minlength.
            above_length_cutoff = [stretch for stretch in straight_stretches if stretch[0] >= self.settings.minlength]
            self.stable[column] = above_length_cutoff

            # If there are no stretches of sufficient length, issue warning
            if not len(above_length_cutoff):
                logger.warn(
                    "Case {0}, dataset {1}. No stable energy tracts found with a minimum length of {2} datapoints".format(
                        self.liemdframe.cases[0], column, self.settings.minlength))
            else:
                logger.info(
                    "Case {0}, dataset {1}: found {2} stable energy tracts of which {3} with a minimum {4} datapoints".format(
                        self.liemdframe.cases[0], column, len(straight_stretches), len(above_length_cutoff),
                        self.settings.minlength))

            self.liemdframe['filter_{0}'.format(column)] = 1
            for stretch in above_length_cutoff:
                logger.debug("Case {0}, dataset {1}: stable energy tract from datapoint {2} till {3} ({4})".format(
                    self.liemdframe.cases[0], column, stretch[1], stretch[2], stretch[0]))
                self.liemdframe.loc[stretch[1]:stretch[2], 'filter_{0}'.format(column)] = 0

            # If no stretches of sufficient length, continue
            if not len(above_length_cutoff):
                continue

            # Select best stretch. First add 1 to filter column. Then reset to 0 for
            # selected stretch
            self.liemdframe['filter_{0}'.format(column)] = self.liemdframe['filter_{0}'.format(column)] + 1

            # Select first longest stretch at beginning of trajectory
            for stretch in sorted(above_length_cutoff, key=lambda l: l[1]):
                if self.settings.extend:
                    self.liemdframe.loc[stretch[1]:stretch[2], 'filter_{0}'.format(column)] = 0
                else:
                    self.liemdframe.loc[stretch[1]:stretch[1]+self.settings.minlength, 'filter_{0}'.format(column)] = 0
                break

        return self.liemdframe

    def plot(self, tofile=False, filetype='png'):
        """
        Plot the results of the FFT filtering and spline fitting for all bound
        Coulomb and Van der Waals pairs in the DataFrame.

        :param tofile:   save the plot as file with `filetype` in the current
                         directory. File names are of the formt
                         <case>-<pose>.<filetype>
        :type tofile:    :py:bool
        :param filetype: Matplotlib supported image file types
        :type filetype:  :py:str

        :return:         Matplotlib axis objects representing the plots
        :rtype:          :py:list
        """

        columns = [n for n in self.liemdframe.columns if n.startswith('coul_bound')]
        plots = []

        for column in columns:

            # Plot the energy trajectory
            plotset = [column]
            pose = column.replace('coul_bound', '')
            vdw = 'vdw_bound{0}'.format(pose)
            if vdw in self.liemdframe.columns:
                plotset.append(vdw)

            ax = self.liemdframe[plotset].plot(legend=False)

            # Plot the FFT fit
            fftset = ['fft_{0}'.format(n) for n in plotset if 'fft_{0}'.format(n) in self.liemdframe.columns]
            if len(fftset):
                ax = self.liemdframe[fftset].plot(ax=ax, legend=False)

            # Plot the gradient
            gradset = ['grad_{0}'.format(n) for n in plotset if 'grad_{0}'.format(n) in self.liemdframe.columns]
            if len(gradset):
                ax = self.liemdframe[gradset].plot(ax=ax, label=None)

            # Give a bit more room at the top by upscaling Y-axis
            yaxis = ax.get_ylim()
            if yaxis[1] <= 5:
                ax.set_ylim(yaxis[0], yaxis[1] + 50)

            if tofile:
                pyplot.savefig('{0}-{1}.{2}'.format(self.liemdframe.cases[0], pose.strip('_'), filetype.strip('.')))
                pyplot.close()
            plots.append(ax)

        return plots
