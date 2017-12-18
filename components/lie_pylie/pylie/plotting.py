# -*- coding: utf-8 -*-

import logging
import numpy
import matplotlib.ticker as mticker

from matplotlib import pyplot
from pylab import polyfit, poly1d

logger = logging.getLogger('pylie')


def plot_matrix(matrix, yaxis=None, xaxis=None, **kwargs):
    """
    Prepare a matrix plot
    """

    # Make new matplotlib figure.
    fig = pyplot.figure()
    ax = fig.add_subplot(1, 1, 1)
    fig.subplots_adjust(top=0.85)
    cax = ax.matshow(matrix, interpolation=kwargs.get('interpolation', 'bilinear'))
    cb = fig.colorbar(cax)
    cb.set_label(kwargs.get('cblabel', ''))

    # Set figure and axis titles
    fig.suptitle(kwargs.get('title', ''))
    ax.set_title(kwargs.get('subtitle', ''), fontsize=8)
    ax.set_ylabel(kwargs.get('ylabel', ''), fontsize=10)
    ax.set_xlabel(kwargs.get('xlabel', ''), fontsize=10)

    # Set the ticks and tick labels. Reverse y axis to align x/y origin
    yaxis_locs = range(0, len(yaxis), len(yaxis) / 10)
    ax.yaxis.set_ticks_position('left')
    ax.yaxis.set_major_locator(mticker.FixedLocator(yaxis_locs))
    ax.yaxis.set_major_formatter(mticker.FixedFormatter(['%1.2f' % yaxis[x] for x in yaxis_locs]))
    ax.invert_yaxis()
    xaxis_locs = range(0, len(xaxis), len(xaxis) / 10)
    ax.xaxis.set_ticks_position('bottom')
    ax.xaxis.set_major_locator(mticker.FixedLocator(xaxis_locs))
    ax.xaxis.set_major_formatter(mticker.FixedFormatter(['%1.2f' % xaxis[x] for x in xaxis_locs]))
    ax.grid(None)

    return fig


def _get_label_offset(dataframe, offset=0.01):
    """
    Calculate label offset value for placing labels next to points in a scatter
    plot. The offset value needs to be added to the datapoint coordinates to place
    the label next to.

    :param dataframe: DataFrame with the two columns to calculate offset for
    :ptype dataframe: DataFrame like object
    :param offset: offset percentage. x and y axis are equal
    :ptype offset: float
    :return: tuple of offset value for x and y axis
    :rtype: tuple
    """

    x_offset = (dataframe.iloc[:, 0].max() - dataframe.iloc[:, 0].min()) * offset
    y_offset = (dataframe.iloc[:, 1].max() - dataframe.iloc[:, 1].min()) * offset

    return x_offset, y_offset


def plot_filtergaussian_distribution(dataframe, ellipse=None, confidence=0.975, *args, **kwargs):
    """
    Plot the results of the multivariate Gaussian distribution analysis as a
    scatter plot. An ellipse is drawn around the data cloud representing the
    confidance interval in which all points within the ellipse are regarded as
    normally distributed.
    Data points outside of the normal distribution are shown in red and labeled
    with there case and pose number.
    Cases defined as part of a training set are shown in green.

    :param kwargs: Any additional keyword arguments are passed to the matplotlib
                   plotting function
    :return: Matplotlib axis object representing the figure
    """

    fig = pyplot.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax = dataframe.plot(kind='scatter', x='coul', y='vdw',
                        title='Multivariate Gaussian distribution outlier detection of delta VdW and Coul energies',
                        ax=ax, **kwargs)

    # If outliers, plot them.
    if dataframe.outliers['filter_mask'].sum() > 0:
        outlier_dataframe = dataframe.outliers
        outlier_dataframe.plot(kind='scatter', x='coul', y='vdw',
                               color='red', label='Outlier %1.1f%%' % (confidence * 100),
                               ax=ax, **kwargs)

        # Print outlier labels
        if kwargs.get('show_labels', True):
            xoff, yoff = _get_label_offset(dataframe[['coul', 'vdw']])
            for i, point in outlier_dataframe.iterrows():
                ax.text(point['coul'] + xoff, point['vdw'] + yoff,
                        "{0:.0f}-{1:.0f}".format(point['case'], point['poses']), fontsize=8)

    # Plot training compounds if any
    trainset = dataframe.trainset
    if not trainset.empty:
        trainset.plot(kind='scatter', x='coul', y='vdw', color='green', label='Training compounds', ax=ax, **kwargs)

    ax.legend(frameon=False, loc='best', fontsize=8)
    ax.set_xlabel(r'$\Delta$$E_{ele}$ (kJ/mol)', fontsize=10)
    ax.set_ylabel(r'$\Delta$$E_{VdW}$ (kJ/mol)', fontsize=10)

    # Plot the ellipse
    if ellipse:
        ax.add_artist(ellipse)

    return fig


def plot_scan_error(dataframe, **kwargs):
    """
    Prepare an error plot.

    Plot scan results as a matrixplot (or heatmap) by calculating the difference
    between reference and calculated values for dG and plot these directly.
    ltol and/or utol may be used as mask to focus plot output on selected ranges
    of delta-dG.
    If the scan is performed for multiple cases, the RMS error in delta-dG will
    be plotted.

    The plot is returned as matplotlib plot object. The appearence of the plot can
    as such be modified afterwards but general plot settings may also be changed
    directly by provinding the keyword argument as input to this function.

    :param dataframe: LIEScanDataFrame instance
    :param ltol: Lower tolerance cutoff. May be used as mask in plot creation to
                 only focus on scan results with values higher than or equal to
                 cutoff. Default not defined.
    :ptype ltol: float
    :param utol: Upper tolerance cutoff. May be used as mask in plot creation to
                 only focus on scan results with values lower than or equal to
                 cutoff. Default not defined.
    :ptype utol: float
    :param kwargs: Any additional keyword arguments will be passed on to
                 matplotlib to change plot appearance.

    :return: matplotlib plot object
    """

    # Determine number of cases
    nr = len(set(dataframe[dataframe._column_names['case']].values))

    # Reshape in (N,Sa*Sb) matrix
    if kwargs.get('absolute', True):
        data = abs(dataframe['error']).values.reshape(dataframe.Sa * dataframe.Sb, nr)
    else:
        data = dataframe['error'].values.reshape(dataframe.Sa * dataframe.Sb, nr)

    # Set upper and lower tolerance limit if not set
    ltol = kwargs.get('ltol', numpy.min(data))
    utol = kwargs.get('utol', numpy.max(data))

    # Calculate Root Mean Squared Error
    scanmatrix = numpy.zeros((dataframe.Sa, dataframe.Sb))
    for i in range(0, nr):
        scanmatrix = scanmatrix + numpy.power(data[:, i].reshape(dataframe.Sa, dataframe.Sb), 2)
    scanmatrix = numpy.sqrt(scanmatrix / nr)
    scanmatrix[scanmatrix <= ltol] = ltol
    scanmatrix[scanmatrix >= utol] = utol

    # Define plotting variables
    plotvars = {
        'title': r'LIE $\alpha$ and $\beta$ parameter scan for {0} cases'.format(nr),
        'subtitle': 'Lower tolerance: {0:.2f}, upper tolerance: {1:.2f}'.format(ltol, utol),
        'cblabel': 'RMS error (kJ/mol)',
        'ylabel': r'$\alpha$',
        'xlabel': r'$\beta$'
    }
    plotvars.update(kwargs)

    logger.info("Create dG RMSe matrix plot for Alpha/Beta parameter scan results")
    logger.info(
        "Create matrix plot using lower tolerance (ltol) of {0:.3f} and upper rolerance (utol) of {1:.3f}".format(ltol,
                                                                                                                  utol))

    # Prepare the plot
    return plot_matrix(scanmatrix,
                       xaxis=dataframe.beta_scan_range,
                       yaxis=dataframe.alpha_scan_range,
                       **plotvars)


def plot_scan_density(dataframe, **kwargs):
    """
    Prepare an density plot.

    Plot scan results as a matrixplot (or heatmap) by calculating the difference
    between reference and calculated values for dG and represent them as boolean
    matrix with a value of 1 for each scan point where the difference is with the
    range ltol <= x <= utol. Given that ltol and utol are defined.

    This representation is particulary usefull when performing the scan for
    multiple cases and quickly getting an overview of the regions in parameter
    space where most cases are within ltol/utol range.

    The plot is returned as matplotlib plot object. The appearence of the plot can
    as such be modified afterwards but general plot settings may also be changed
    directly by provinding the keyword argument as input to this function.

    @param float ltol: Lower tolerance cutoff. May be used as mask in plot
                       creation to only focus on scan results with values higher
                       than or equal to cutoff. Default not defined.
    @param float utol: Upper tolerance cutoff. May be used as mask in plot
                       creation to only focus on scan results with values lower
                       than or equal to cutoff. Default not defined.
    @param float ptol: Do not display density values lower than percentage cutoff.
                       None, by default.
    @param bool absolute: Use the absolute difference between calculated and
                       observed dG.
    @param kwargs:     Any additional keyword arguments will be passed on to
                       matplotlib to change plot appearance.

    @return matplotlib plot object
    """

    # Determine number of cases
    nr = len(set(dataframe[dataframe._column_names['case']].values))

    # Reshape in (N,Sa*Sb) matrix
    data = dataframe['error'].values.reshape(dataframe.Sa * dataframe.Sb, nr)
    if kwargs.get('absolute', False):
        data = numpy.absolute(dGdiff)

    # Set upper and lower tolerance limit if not set. Use cutoff of 5% between
    # minimum and maximum value in dataet
    ltol = kwargs.get('ltol', numpy.min(data) * 0.05)
    utol = kwargs.get('utol', numpy.max(data) * 0.05)

    # Make new matrix of size (alpha range x beta range) and add reshaped
    # identity matrixes for each case. Identity matrix is determined as 1 for
    # all cases with gamma residual in range ltol <= x <= utol, and 0 outside.
    identmatr = ((data >= ltol) & (data <= utol)).astype(int)
    ident_matrix_cases = identmatr * numpy.arange(1, nr + 1).reshape(1, nr)
    scanmatrix = numpy.zeros((dataframe.Sa, dataframe.Sb))
    for i in range(1, nr + 1):
        scanmatrix = scanmatrix + numpy.sum((ident_matrix_cases == i).astype(int), axis=1).reshape(dataframe.Sa,
                                                                                                   dataframe.Sb)

    # Transform counts into percentages
    scanmatrix = (scanmatrix / nr) * 100

    # Only display matrix elements with percentage above cutoff
    ptol = kwargs.get('ptol', None)
    if ptol:
        scanmatrix[scanmatrix < ptol] = 0

    # Define plotting variables
    plotvars = {
        'title': r'LIE $\alpha$ and $\beta$ parameter scan for {0} cases'.format(nr),
        'subtitle': 'Density as number of ligands with dG RMSe within range: {0:.2f} to {1:.2f} kJ/mol'.format(ltol,
                                                                                                               utol),
        'cblabel': 'Percentage within tolerance range',
        'ylabel': r'$\alpha$',
        'xlabel': r'$\beta$'
    }
    plotvars.update(kwargs)

    logging.info("Create density matrix plot for Alpha/Beta parameter scan results")
    logging.info(
        "Create matrix plot using lower tolerance (ltol) of {0:.3f} and upper rolerance (utol) of {1:.3f}".format(ltol,
                                                                                                                  utol))

    # Prepare the plot
    return plot_matrix(scanmatrix,
                       xaxis=dataframe.beta_scan_range,
                       yaxis=dataframe.alpha_scan_range,
                       **plotvars)


def plot_scan_optimal(dataframe, **kwargs):
    column = kwargs.get('parameter', 'error')

    # Determine number of cases
    nr = len(set(dataframe[dataframe._column_names['case']].values))

    data = dataframe.get_optimal(column=column)
    data[column] = abs(data[column])
    fig = pyplot.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax = data.plot(kind='scatter', x='beta', y='alpha', c=column, ax=ax)

    fig.suptitle(r'Optimal $\alpha$ and $\beta$ parameter values for {0} cases'.format(nr))
    ax.set_xlabel(r'$\beta$', fontsize=20)
    ax.set_ylabel(r'$\alpha$', fontsize=20)

    if kwargs.get('plot_labels', False):
        for i, point in data.iterrows():
            ax.text(point['beta'], point['alpha'], "{0:.0f}".format(i), size='xx-small')

    return fig


def plot_model_weights(dataframe, **kwargs):
    """
    Create the LIE model scatter plot with marker points colored according to the
    weight in the robust regression
    """

    fig = pyplot.figure()
    ax = fig.add_subplot(1, 1, 1)

    # Plot all the datapoints
    ax = dataframe.plot(kind='scatter', x='ref_affinity', y='dg_calc', c='weights', color='Blue', ax=ax)
    ax.set_aspect('equal')

    # Force X and Y axis to have the same data range
    axis_min = 10 * round((min([dataframe['ref_affinity'].min(), dataframe['dg_calc'].min()]) - 5) / 10)
    axis_max = 10 * round((max([dataframe['ref_affinity'].max(), dataframe['dg_calc'].max()]) + 5) / 10)
    ax.set_xlim(axis_min, axis_max)
    ax.set_ylim(axis_min, axis_max)

    # Add diagonal
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    ax.plot(xlim, ylim, 'k-', linewidth=0.5)
    ax.plot((xlim[0], xlim[1] - 5), (ylim[0] + 5, ylim[1]), 'k--')
    ax.plot((xlim[0] + 5, xlim[1]), (ylim[0], ylim[1] - 5), 'k--')

    # Plot the training set if any
    trainset = dataframe.trainset
    if not trainset.empty:
        ax = trainset.plot(kind='scatter', x='ref_affinity', y='dg_calc', c='weights', marker='s', ax=ax)

    # Plot the regression line
    ref = dataframe['ref_affinity'].values
    fitx = polyfit(ref, dataframe['dg_calc'].values, 1)
    fit_fnx = poly1d(fitx)
    ax.plot(ref, fit_fnx(ref), 'r-', label="fit", linewidth=0.5)

    # Plot datalabels if needed
    if kwargs.get('plot_labels', False):
        cutoff = kwargs.get('cutoff', 0.85)
        for i, point in dataframe.iterrows():
            if point['weights'] < cutoff:
                ax.text(point['ref_affinity'], point['dg_calc'], "{0:.0f}".format(point['case']), fontsize=8)

    ax.set_xlabel(r'$\Delta$$G_{Ref}$ (kJ/mol)', fontsize=10)
    ax.set_ylabel(r'$\Delta$$G_{Calc}$ (kJ/mol)', fontsize=10)
    ax.legend(loc="best", frameon=False)

    return fig


def plot_model_model(dataframe, **kwargs):
    """
    Create the LIE model scatter plot
    """

    settings = {'tollerance': 5, 'color': 'red'}
    settings.update(kwargs)

    ax = settings.get('ax', None)
    combine_plots = False
    if ax:
        combine_plots = True

    # Plot the training set
    trainset = dataframe.trainset
    label = 'train'
    if combine_plots:
        label = None
    ax = trainset.plot(kind='scatter', x='ref_affinity', y='dg_calc', color=settings['color'], label=label, s=25, ax=ax)
    ax.set_aspect('equal')

    # Plot datalabels if needed
    if settings.get('plot_labels', False):
        for i, point in trainset.iterrows():
            ax.text(point['ref_affinity'], point['dg_calc'], "{0:.0f}".format(point['case']), fontsize=8)

    # Force X and Y axis to have the same data range
    axis_min = 10 * round(min([trainset['ref_affinity'].min(), trainset['dg_calc'].min()]) / 10)
    axis_max = 10 * round(max([trainset['ref_affinity'].max(), trainset['dg_calc'].max()]) / 10)

    # Give it a bit more space
    ax.set_xlim(axis_min - 10, axis_max + 10)
    ax.set_ylim(axis_min - 10, axis_max + 10)

    # Plot the regression line
    if settings.get('plot_regline', False):
        ref = trainset['ref_affinity'].values
        fitx = polyfit(ref, trainset['dg_calc'].values, 1)
        fit_fnx = poly1d(fitx)
        ax.plot(ref, fit_fnx(ref), 'r-', label="fit", linewidth=0.5)

    # Add diagonal and error margins
    if not combine_plots:
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()

        ax.plot(xlim, ylim, 'k-', linewidth=0.5)
        ax.plot((xlim[0], xlim[1] - settings['tollerance']), (ylim[0] + settings['tollerance'], ylim[1]), 'k--')
        ax.plot((xlim[0] + settings['tollerance'], xlim[1]), (ylim[0], ylim[1] - settings['tollerance']), 'k--')

    # Plot the test set if any
    testset = dataframe.testset
    if not testset.empty and settings.get('plot_test', True):
        label = 'test'
        if combine_plots:
            label = None
        ax = testset.plot(kind='scatter', x='ref_affinity', y='dg_calc', label=label, s=20, ax=ax)

        # Plot datalabels if needed
        if settings.get('plot_labels', False):
            for i, point in testset.iterrows():
                ax.text(point['ref_affinity'], point['dg_calc'], "{0:.0f}".format(point['case']), fontsize=8)

    ax.set_xlabel(r'$\Delta$$G_{Ref}$ (kJ/mol)', fontsize=15)
    ax.set_ylabel(r'$\Delta$$G_{Calc}$ (kJ/mol)', fontsize=15)
    ax.legend(loc="best", frameon=False)

    return ax
