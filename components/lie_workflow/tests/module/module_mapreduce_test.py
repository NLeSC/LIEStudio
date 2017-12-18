# -*- coding: utf-8 -*-

"""
file: module_test.py

Unit tests for a Map-Reduce style workflow
"""

import os
import sys
import unittest2
import logging
import time

from   lie_workflow                import Workflow
from   dummy_task_runners          import task_runner, calculate_accumulated_task_runtime

currpath = os.path.dirname(__file__)


class TestArrayMapper(unittest2.TestCase):
    """
    Run a Map-Reduce style workflow using the Mapper task that
    maps data items from an array on parallelised copies of the
    descendant tasks
    """

    def setUp(self):
        """
        Load a simple map-reduce workflow from a JSON specification
        """

        # Construct the workflow specification
        self.wf = Workflow()
        self.wf.task_runner = task_runner

    def test_array_mapper(self):
        
        # Set some workflow metadata in the start node
        self.wf.input(mapper=[{'dummy':1}, {'dummy':2}, {'dummy': 3}])

        # Connect mapper to start
        t1 = self.wf.add_task('Map input', task_type='Mapper')
        self.wf.connect_task(1, t1)

        # Connect a worker
        t2 = self.wf.add_task('Worker')
        self.wf.input(t2, sleep=1)
        self.wf.connect_task(t1,t2)

        # Connect a collector
        t3 = self.wf.add_task('Collect', task_type='Collect', to_mapper=t1, custom_func='dummy_task_runners.reduce_function')
        self.wf.connect_task(t2,t3)

        # Run the workflow
        self.wf.run()

        while self.wf.is_running:
            time.sleep(1)

        self.assertFalse(self.wf.is_running)
        self.assertTrue(self.wf.is_completed)


class TestMapReduceWorkflow(unittest2.TestCase):
    """
    Run a Map-Reduce style workflow testing default mapping function of
    the workflow runner and output gathering function of a special
    Reduce task type.
    """
    
    workflow_spec_path = os.path.abspath(os.path.join(currpath, '../files/mapreduce-workflow-spec.json'))

    def setUp(self):
        """
        Load a simple map-reduce workflow from a JSON specification
        """
        
        # Construct the workflow specification
        self.wf = Workflow()
        self.wf.task_runner = task_runner
        self.wf.load(self.workflow_spec_path)
        
        # Define dummy input the dummy_task_runner knows how to handle
        self.wf.input(dummy=1)
    
    def test_workflow_mapreduce(self):
        """
        Test single map-reduce workflow successful execution
        """

        self.wf.workflow.nodes[5]['input_data']['sleep'] = 4
        self.wf.workflow.nodes[7]['input_data']['sleep'] = 2

        # Run the workflow
        self.wf.run()

        while self.wf.is_running:
            time.sleep(1)
        
        self.assertFalse(self.wf.is_running)
        self.assertTrue(self.wf.is_completed)

        runtime = calculate_accumulated_task_runtime(self.wf.workflow)
        self.assertLess(self.wf.runtime(), runtime)
        self.assertEqual(self.wf.workflow.nodes[10]['output_data']['dummy'], 21)

    def test_workflow_mapreduce_blocking(self):
        """
        Test map-reduce workflow successful execution using BlockingTasks.
        With all tasks converted from threaded Task to BlockingTasks objects,
        the total workflow runtime equals the accumulated task runtime.
        """

        # Convert all Task types to BlockingTask
        for n,v in self.wf.workflow.nodes.items():
            if v['task_type'] == 'Task':
                v['task_type'] = 'BlockingTask'

        self.wf.workflow.nodes[5]['input_data']['sleep'] = 4
        self.wf.workflow.nodes[7]['input_data']['sleep'] = 2

        # Run the workflow
        self.wf.run()

        while self.wf.is_running:
            time.sleep(1)

        self.assertFalse(self.wf.is_running)
        self.assertTrue(self.wf.is_completed)
        self.assertListEqual(self.wf.output().keys(), [10])

        runtime = calculate_accumulated_task_runtime(self.wf.workflow)
        self.assertEqual(self.wf.runtime(), runtime)
        self.assertEqual(self.wf.runtime(tid=5), 4)
        self.assertEqual(self.wf.runtime(tid=7), 2)

    def test_workflow_mapreduce_failed(self):
        """
        Test map-reduce workflow failed at task 6
        """

        # Instruct the runner to fail at node 6
        self.wf.workflow.nodes[6]['input_data']['fail'] = True

        # Run the workflow
        self.wf.run()

        while self.wf.is_running:
            time.sleep(1)

        self.assertFalse(self.wf.is_running)
        self.assertFalse(self.wf.is_completed)
        self.assertEqual(self.wf.failed_task, 6)

    def test_workflow_mapreduce_retrycount(self):
        """
        Test retry of failing nodes
        """

        # Set retrycount globally
        for task in self.wf.workflow.nodes:
            self.wf.workflow.nodes[task]['retry_count'] = 3

        # Instruct the runner to fail at node 7
        self.wf.workflow.nodes[8]['input_data']['fail'] = True
        self.wf.workflow.nodes[8]['input_data']['sleep'] = 2

        # Run the workflow
        self.wf.run()

        # Blocking: wait until workflow is no longer running
        while self.wf.is_running:
            time.sleep(1)

        self.assertFalse(self.wf.is_running)
        self.assertFalse(self.wf.is_completed)
        self.assertEqual(self.wf.workflow[8]['retry_count'], 0)
        self.assertEqual(self.wf.failed_task, 8)

        runtime = calculate_accumulated_task_runtime(self.wf.workflow)
        self.assertLess(runtime, self.wf.runtime())

    def test_workflow_mapreduce_crash(self):
        """
        Simulate a failed workflow due to abruptly failed (crashed)
        task.
        """

        # Instruct the runner to fail at node 8
        self.wf.workflow.nodes[8]['input_data']['crash'] = True

        # Run the workflow
        self.wf.run()

        # Blocking: wait until workflow is no longer running
        while self.wf.is_running:
            time.sleep(1)

        self.assertFalse(self.wf.is_running)
        self.assertFalse(self.wf.is_completed)
        self.assertEqual(self.wf.failed_task, 8)

    def test_workflow_mapreduce_breakpoint(self):
        """
        Simulate a breakpoint at node 8 and step over
        it manually to finish workflow
        """

        # Set a breakpoint at node 8
        self.wf.workflow.nodes[7]['breakpoint'] = True

        # Run the workflow
        self.wf.run()

        # Blocking: wait until the workflow hits an active breakpoint
        while self.wf.is_running:
            time.sleep(1)

        self.assertFalse(self.wf.is_running)
        self.assertFalse(self.wf.is_completed)
        self.assertEqual(self.wf.active_breakpoint, 7)

        # Step the breakpoint
        bp = self.wf.active_breakpoint
        self.wf.step_breakpoint(bp)

        # Run the workflow
        self.wf.run(tid=bp+1)

        # Blocking: wait until workflow is no longer running
        while self.wf.is_running:
            time.sleep(1)

        self.assertFalse(self.wf.is_running)
        self.assertTrue(self.wf.is_completed)
        self.assertIsNone(self.wf.active_breakpoint)

    def test_workflow_mapreduce_cancel(self):
        """
        Simulate canceling the workflow after 4 seconds.
        That should leave node 5 to be canceled
        """

        self.wf.workflow.nodes[5]['input_data']['sleep'] = 4
        self.wf.workflow.nodes[7]['input_data']['sleep'] = 2

        # Run the workflow
        self.wf.run()

        while self.wf.is_running:
            time.sleep(4)
            self.wf.cancel()

        self.assertFalse(self.wf.is_running)
        self.assertFalse(self.wf.is_completed)
        self.assertListEqual([n for n,v in self.wf.workflow.nodes.items() if v['status'] == 'aborted'], [5])