# -*- coding: utf-8 -*-

"""
LIEStudio component providing an interface to the Amber Tools software suite
available at http://ambermd.org
When using this component in scientific work please cite:
- D.A. Case, R.M. Betz, W. Botello-Smith, D.S. Cerutti, T.E. Cheatham, III,
  T.A. Darden, R.E. Duke, T.J. Giese, H. Gohlke, A.W. Goetz, N. Homeyer,
  S. Izadi, P. Janowski, J. Kaus, A. Kovalenko, T.S. Lee, S. LeGrand, P. Li,
  C. Lin, T. Luchko, R. Luo, B. Madej, D. Mermelstein, K.M. Merz, G. Monard,
  H. Nguyen, H.T. Nguyen, I. Omelyan, A. Onufriev, D.R. Roe, A. Roitberg,
  C. Sagui, C.L. Simmerling, J. Swails, R.C. Walker, J. Wang, R.M. Wolf,
  X. Wu, L. Xiao, D.M. York and P.A. Kollman (2016), AMBER 2016,
  University of California, San Francisco.
"""

import os

__module__ = 'lie_amber'
__docformat__ = 'restructuredtext'
__version__ = '{major:d}.{minor:d}'.format(major=0, minor=2)
__author__ = 'Marc van Dijk'
__status__ = 'pre-release beta1'
__date__ = '15 april 2016'
__licence__ = 'Apache Software License 2.0'
__url__ = 'https://github.com/NLeSC/LIEStudio'
__copyright__ = "Copyright (c) VU University, Amsterdam"
__rootpath__ = os.path.dirname(__file__)

from .ambertools import (amber_acpype, collect_acpype_output, amber_reduce)


__all__ = ['amber_acpype', 'amber_reduce', 'collect_acpype_output']
