# -*- coding: utf-8 -*-

"""
LIEStudio propka component

PROPKA predicts the pKa values of ionizable groups in proteins and
protein-ligand complexes based in the 3D structure.

When using this component in scientific work please cite:
- Mats H.M. Olsson, Chresten R. Sondergard, Michal Rostkowski, and Jan H. Jensen
  "PROPKA3: Consistent Treatment of Internal and Surface Residues in Empirical
  pKa predictions." Journal of Chemical Theory and Computation, 7(2):525-537
  (2011)
"""

import os
from wamp_services import RunPropka

__module__ = 'lie_propka'
__docformat__ = 'restructuredtext'
__version__ = '{major:d}.{minor:d}'.format(major=0, minor=2)
__author__ = 'Marc van Dijk'
__status__ = 'pre-release beta1'
__date__ = '5 august 2016'
__licence__ = 'Apache Software License 2.0'
__url__ = 'https://github.com/MD-Studio/MDStudio'
__copyright__ = "Copyright (c) VU University, Amsterdam"
__rootpath__ = os.path.dirname(__file__)
__all__ = ['RunPropka']
