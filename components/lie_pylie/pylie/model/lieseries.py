# -*- coding: utf-8 -*-

import numpy
from pandas import Series

from ..model.liebase import LIESeriesBase

OLD_PANDAS = issubclass(Series, numpy.ndarray)


def _is_empty(x):
    try:
        return x.is_empty
    except:
        return False


class LIESeries(LIESeriesBase):
    def __new__(cls, *args, **kwargs):

        if OLD_PANDAS:
            arr = Series.__new__(cls, *args, **kwargs)
        else:
            arr = Series.__new__(cls)
        if type(arr) is LIESeries:
            return arr
        else:
            return arr.view(LIESeries)

    @property
    def _constructor(self):

        """
        Ensure that the new DataFrame is always of type LIEDataFrameBase
        """

        return LIESeries

    def copy(self, order='C'):

        """
        Make a copy of this LIESeries object
        """
        # FIXME: this will likely be unnecessary in pandas >= 0.13
        return LIESeries(self.values.copy(order), index=self.index,
                         name=self.name).__finalize__(self)
