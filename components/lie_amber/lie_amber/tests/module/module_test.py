# -*- coding: utf-8 -*-

"""
file: module_atb_test.py

Unit tests for the Automated Topology Builder server API
"""

import os
import unittest2
import shutil

from lie_amber import settings, amber_reduce, amber_acpype


class TestAPI(unittest2.TestCase):
    currpath = os.path.dirname(__file__)
    _files_dir = os.path.join(currpath, '../', 'files')
    
    def setUp(self):
        """
        ConfigHandlerTests class setup
        
        Define the temporary working directory
        """
        
        settings['workdir'] = self._files_dir
        self.files_to_delete = []
        
    def tearDown(self):
        """
        Cleanup after each unit test
        """

        for dfile in self.files_to_delete:
            if os.path.isfile(dfile):
                os.remove(dfile)
            if os.path.isdir(dfile):
                shutil.rmtree(dfile)
    
    def test_amber_reduce(self):
        """
        Test the Amber 'reduce' program
        """
        
        testfile = os.path.join(self._files_dir, 'sqm.pdb')
        outfile = os.path.join(self._files_dir, 'sqm_h.pdb')
        amber_reduce(testfile)
        self.files_to_delete.append(outfile)
        
        self.assertTrue(os.path.isfile(outfile))
    
    def test_amber_acepype(self):
        """
        Test the ACPYPE program
        """
        
        testfile = os.path.join(self._files_dir, 'sqm.pdb')
        outdir = amber_acpype(testfile, outtop='gmx', workdir=self._files_dir)
        self.files_to_delete.append(outdir)
        
        self.assertTrue(os.path.isdir(outdir))

