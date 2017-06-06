# -*- coding: utf-8 -*-

"""
package:  lie_logger

LIEStudio logging component
"""

import os

__module__ = 'lie_logger'
__docformat__ = 'restructuredtext'
__version__ = '{major:d}.{minor:d}'.format(major=0, minor=1)
__author__ = 'Marc van Dijk'
__status__ = 'pre-release beta1'
__date__ = '15 april 2016'
__licence__ = 'Apache Software License 2.0'
__url__ = 'https://github.com/NLeSC/LIEStudio'
__copyright__ = "Copyright (c) VU University, Amsterdam"
__rootpath__ = os.path.dirname(__file__)

from .system_logger import init_application_logging, exit_application_logging
from .settings import settings

# Define component public API
oninit = init_application_logging
onexit = exit_application_logging
