# -*- coding: utf-8 -*-

"""
LIEStudio docking component
This module performs molecular docking with the focus on docking
small molecular weight compounds (e.a. ligand) in protein
functional sites using the PLANTS molecular docking methods.
- PLANTS: Protein-Ligand ANT System.
"""

import os

__module__ = 'lie_plants_docking'
__docformat__ = 'restructuredtext'
__version__ = '{major:d}.{minor:d}'.format(major=0, minor=1)
__author__ = 'Marc van Dijk'
__status__ = 'pre-release beta1'
__date__ = '5 august 2016'
__licence__ = 'Apache Software License 2.0'
__url__ = 'https://github.com/NLeSC/LIEStudio'
__copyright__ = "Copyright (c) VU University, Amsterdam"
__rootpath__ = os.path.dirname(__file__)

from .plants_docking import PlantsDocking
from .utils import PLANTS_DOCKING_SCHEMA as plants_docking_schema
from .utils import settings


__all__ = ['PlantsDocking', 'plants_docking_schema', 'settings']
