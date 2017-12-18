# -*- coding: utf-8 -*-

"""
file: module_workflow_test.py

Test pylie workflows
"""

import unittest2

from pandas import DataFrame

from pylie import LIEMDFrame
from pylie.methods.fileio import read_gromacs_energy_file
from pylie.workflows.filter_workflow import FilterWorkflow
from pylie.filters.filtersplines import FilterSplines


class TestPylieWorkflows(unittest2.TestCase):

    def test_filter_workflow(self):

        settings = {'doFilterSplines': True,
                    'doFilterGaussian': False,
                    'doFilterAlphaBetaScan': False,
                    'doPoseProbabilityFilter': False,
                    'prob_report_insignif': False,
                    'plotFilterSplines': False,
                    'plotFilterGaussian': False,
                    'plotFilterAlphaBetaScan': False,
                    'plot_results': False}
