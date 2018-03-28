# -*- coding: utf-8 -*-

"""
file: cheminfo_molhandle.py

Cinfony driven cheminformatics fingerprint functions
"""

import logging

from twisted.logger import Logger

from . import toolkits

logging = Logger()


def available_descriptors():
    """
    List available molecular descriptors for all active cheminformatics
    packages

    The webel toolkit has a descriptor service but the supported
    descriptors are not listed in Cinfony. The toolkit is available
    however.

    :rtype: :py:dict
    """

    available_descs = {'webel': None}
    for toolkit, obj in toolkits.items():
        if hasattr(obj, 'descs'):
            available_descs[toolkit] = obj.descs

    return available_descs

