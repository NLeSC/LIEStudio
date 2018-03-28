# -*- coding: utf-8 -*-

"""
LIEStudio connector component for the Automated Topology Builder (ATB) server
at https://atb.uq.edu.au

When usig this component in scientific work please cite:

 -  Malde AK, Zuo L, Breeze M, Stroet M, Poger D, Nair PC, Oostenbrink C, Mark AE.
    An Automated force field Topology Builder (ATB) and repository: version 1.0.
    Journal of Chemical Theory and Computation, 2011, 7(12), 4026-4037.
    DOI: 10.1021/ct200196m
"""

import os
import sys

__module__ = 'lie_atb'
__docformat__ = 'restructuredtext'
__version__ = '{major:d}.{minor:d}'.format(major=0, minor=1)
__author__ = 'Marc van Dijk'
__status__ = 'pre-release beta1'
__date__ = '15 april 2016'
__licence__ = 'Apache Software License 2.0'
__url__ = 'https://github.com/NLeSC/LIEStudio'
__copyright__ = "Copyright (c) VU University, Amsterdam"
__rootpath__ = os.path.dirname(__file__)

__all__ = ['ATBServerApi', 'ATB_Mol']

from .settings import SETTINGS

if sys.version_info.major == 3:
    from .atb_api_py3 import ATB_Mol
    from .atb_api_py3 import API as ATBServerApi
else:
    from .atb_api_py2 import ATB_Mol
    from .atb_api_py2 import API as ATBServerApi

# Define module public API
settings = SETTINGS
