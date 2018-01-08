# -*- coding: utf-8 -*-

import logging
import sys
import os
import matplotlib

# Init maplotlib
from matplotlib import style
matplotlib.use('Agg')  # Use Agg for non-interactive plotting
style.use('ggplot')  # Because of AttributeError: Unknown property color_cycle bug in Pandas 1.7.1 with Matplotlib 1.5.0

# Make sure module is in path
modulepath = os.path.dirname(__file__)
if modulepath not in sys.path:
    sys.path.insert(0, modulepath)

# Initiate an instance of the py-lie master configuration file
from .config import MetaConfigHandler
from .settings import PYLIE_MASTER_CONFIG

pylie_config = MetaConfigHandler(PYLIE_MASTER_CONFIG)

from .info import info
from .model.liemdframe import LIEMDFrame
from .model.liedataframe import LIEDataFrame
from .model.lieseries import LIESeries
from .model.liemodelframe import LIEModelBuilder
from .model.scandataframe import LIEScanDataFrame

__module__ = 'pylie'
__docformat__ = 'restructuredtext'
__version__ = '{major:d}.{minor:d}.{micro:d}'.format(major=0, minor=1, micro=0)
__author__ = 'Marc van Dijk'
__status__ = 'pre-release beta1'
__date__ = '04 june 2014'

__all__ = ['LIEDataFrame', 'LIESeries', 'LIEModelBuilder', 'LIEScanDataFrame', 'LIEMDFrame']
__doc__ = info.format(version=__version__, author=__author__)

# Configure logger
logger = logging.getLogger(__module__)

# Log module version information
logger.info('Running {0} version {1} ({2})'.format(__module__, __version__, __status__))