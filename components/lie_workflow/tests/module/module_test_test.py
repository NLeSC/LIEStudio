# -*- coding: utf-8 -*-

"""
file: module_test.py

Unit tests for a single branched workflow
"""

import os
import sys
import unittest2
import logging
import time

from   lie_workflow                import Workflow
from   dummy_task_runners          import task_runner, calculate_accumulated_task_runtime

currpath = os.path.dirname(__file__)
    

class TestBranchedWorkflow(unittest2.TestCase):
    """
    Test simple branched workflow
    """
    
    workflow_spec_path = os.path.abspath(os.path.join(currpath, '../files/test-workflow-spec.json'))
    
    def setUp(self):
        """
        Load a simple branched workflow from a JSON specification
        """
        
        # Construct the workflow specification
        self.wf = Workflow()
        self.wf.task_runner = task_runner
        #self.wf.load(self.workflow_spec_path)
        
        # Define dummy input the dummy_task_runner knows how to handle
        self.wf.input(dummy=1)

    def test_workflow_single_branched(self):
        """
        Test single branched workflow successful execution.
        With threaded tasks, the total workflow runtime is less than the
        accumulated task runtime.
        """
        
        # Set some workflow metadata in the start node
        workdir = '/Users/mvdijk/Documents/WorkProjects/liestudio-master/lieproject'
        project_dir = os.path.join(workdir, str(int(time.time())))
        start = self.wf.get_task(1)
        start.set('workdir', project_dir)
        
        # Set 4 branched tasks
        for t in range(4):
            tid = self.wf.add_task('task{0}'.format(t+1))
            self.wf.input(tid=tid, sleep=1)
            self.wf.connect_task(1, t+2)
        
        # Set collect task
        c = self.wf.add_task('collect', custom_func="dummy_task_runners.reduce_function")
        for t in range(4):
            self.wf.connect_task(t+2, c)
            
        # Run the workflow
        self.wf.run()

        while self.wf.is_running:
            time.sleep(1)
        
        print(self.wf.save())