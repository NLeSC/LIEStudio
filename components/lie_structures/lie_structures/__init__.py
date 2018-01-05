# -*- coding: utf-8 -*-

"""
package:  lie_structures

LIEStudio small molecule cheminformatics functions

export RDBASE='/Users/mvdijk/Documents/WorkProjects/liestudio-master/liestudio/bin/RDkit'
export DYLD_LIBRARY_PATH='/Users/mvdijk/Documents/WorkProjects/liestudio-master/liestudio/bin/RDkit/lib'
export JPYPE_JVM=/System/Library/Frameworks/JavaVM.framework/JavaVM
export LD_LIBRARY_PATH=/System/Library/Frameworks/JavaVM.framework/Libraries:$LD_LIBRARY_PATH
export CLASSPATH=/Users/mvdijk/Documents/WorkProjects/liestudio-master/liestudio/bin/opsin-1.3.0-jar-with-dependencies.jar:/Users/mvdijk/Documents/WorkProjects/liestudio-master/liestudio/bin/cdk-1.4.15.jar

TODO: Incluce PyBioMed package?
TODO: Integrate Cambridge Structural Database, using CSD Python API
TODO: Integrate PaDEL-Descriptor package?
"""

import os

__module__ = 'lie_structures'
__docformat__ = 'restructuredtext'
__version__ = '{major:d}.{minor:d}'.format(major=0, minor=1)
__author__ = 'Marc van Dijk'
__status__ = 'pre-release beta1'
__date__ = '5 august 2016'
__licence__ = 'Apache Software License 2.0'
__url__ = 'https://github.com/NLeSC/LIEStudio'
__copyright__ = "Copyright (c) VU University, Amsterdam"
__rootpath__ = os.path.dirname(__file__)

from .settings import STRUCTURES_SCHEMA as structures_schema
from .settings import settings
from .cheminfo_pkgmanager import CinfonyPackageManager

# Load the toolkits
paths = dict([(k,v) for k,v in settings.items() if k in ('indy_path', 'rdk_path')])
toolkits = CinfonyPackageManager(paths)

