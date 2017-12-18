# -*- coding: utf-8 -*-

"""
Python unit test function for lie_atb module, run as:
::
    test = module_test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(test)
"""

import os
import sys
import unittest2
import logging

# Init basic logging
logging.basicConfig(level=logging.DEBUG)

# Add modules in package to path so we can import them
modulepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, modulepath)


def module_test_suite():
    """
    Run lie_atb module unit tests
    """

    testpath = os.path.join(os.path.dirname(__file__), 'module')
    loader = unittest2.TestLoader()
    suite = loader.discover(testpath, pattern='module_*.py')
    return suite
