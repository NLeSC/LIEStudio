# -*- coding: utf-8 -*-

"""
Python runner for lie_atb module unit tests, run as:
::
    python tests
"""

import os
import sys
import unittest2
import logging

# Init basic logging
logging.basicConfig(level=logging.WARN)

# Add modules in package to path so we can import them
modulepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, modulepath)


def module_test_suite():
    """
    Run lie_atb module unit tests
    """
    loader = unittest2.TestLoader()

    print('Running lie_atb unittests')
    testpath = os.path.join(os.path.dirname(__file__), 'module')
    suite = loader.discover(testpath, pattern='module_*.py')
    runner = unittest2.TextTestRunner(verbosity=2)
    runner.run(suite)


if __name__ == '__main__':
    module_test_suite()