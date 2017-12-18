# -*- coding: utf-8 -*-

"""
package: pylie
file   : stats

Various statistical methods
"""

import numpy


def rss(response, observed):
    """
    Residual Sum of Squares or Error sum of squares

    It is the sum of the squared difference between the experimental response y
    and the response calculated by the regression model (residuals).
    """

    return sum(numpy.square(response - observed))


def tss(response):
    """
    Total Sum of Squares

    Total variance that a regression model can explain and is used as a reference
    quantity to calculate standardized quality parameters. Also denoted as SSY,
    it is the sum of the squared differences between the experimental responses
    and the average experimental response.
    """

    return sum(numpy.square(response - numpy.mean(response)))


def mss(response, observed):
    """
    Model Sum of Squares

    MSS = TSS - RSS
    """

    return tss(response) - rss(response, observed)


def rsd(response, observed, p):
    """
    Residual standard deviation (RSD)

    Most often denoted as Sy
    Other symbols that can be commonly used for the residual standard deviation
    are RSD, SE, and s.
    p is the degrees of freedom of the model
    """

    return numpy.sqrt(rss(response, observed) / (len(response) - p))


def sdec(response, observed):
    """
    Standard Deviation Error in Calculation (SDEC or SEC)

    Also known as RMSE where degrees of freedom equals number of observations.
    A more direct measure of the average error of the response estimates with
    respect to RSD.
    """

    return rsd(response, observed, 0)


def rsquared(response, observed):
    """
    Coefficient of determination (R squared)

    The multiple correlation coefficient R is the root of R-squared.
    """

    return 1 - (rss(response, observed) / tss(response))


def adj_rsequared(response, observed, p):
    """
    Adjusted Coefficient of determination (Adj. R squared)

    The multiple correlation coefficient R is the root of R-squared.
    """

    n = len(response)
    return 1 - ((1 - rsquared(response, observed)) * ((n - 1) / (n - p - 1)))


def ftest(response, observed, p):
    """
    F-ratio test in regression

    Defined as the ratio between the variance explained by the model to the
    residual variance, both scaled by the corresponding degrees of freedom.

    Analogously to adjusted R2, higher the F value better the model. This use of
    the F value in evaluating a regression model is correct, but some problems
    arise when one think that the F value was originally proposed as a statistical
    test, that is the calculated F needs to be compared with a critical value at
    some probability level in order to draw decisions.

    In effect, the null hypothesis H0 of the F-ratio test in regression states that
    all the regression coefficients are equal to zero (i.e. no regression model is
    obtained) against the alternative hypothesis H1 that at least one of the
    regression coefficients is different from zero (i.e. a regression model is
    obtained).
    Therefore, in multivariate analysis, where more than one independent variable
    is used, this test is very weak and, in practice, completely unuseful: in fact,
    we want all the variables included in the model to be relevant
    (or statistically significant) for the response we are modelling.
    """

    return (mss(response, observed) / (p - 1)) / (rss(response, observed) / (len(response) - p))


def press(response, test_observed):
    """
    Predictive Error Sum of Squares (PRESS)

    Goodness of prediction measure: It is the sum of the squared differences
    between the experimental response y and the response predicted by the
    regression model, i.e. for an object that was not used for model estimation.
    """

    return rss(response, test_observed)


def qsquared(response, test_observed):
    """
    Cross-validated R2 or Q2

    The test_observed set is usually obtained from a leave-one or leave-multiple
    out cross-validation cycle.

    For bad predictive models, Q2 can assume even negative values when PRESS is
    greater than TSS, meaning that in prediction the model performs worse than the
    no-model estimate, i.e. the mean response of the training set.
    """

    return 1 - (rss(response, test_observed) / tss(response))


def sdep(response, test_observed):
    """
    Standard Deviation error in Prediction (SDEP or SEP)

    The test_observed can either be the observed values of a test set after model
    fot on a training set or obtained from a leave-one or leave-multiple out
    cross-validation cycle.
    """

    return numpy.sqrt(press(response, test_observed) / len(response))
