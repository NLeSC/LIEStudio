# -*- coding: utf-8 -*-

"""
file: task_specs.py

Graph node task classes
"""

import itertools
import jsonschema
import json
import random
import os
import six
import time

from twisted.internet import (reactor, threads)
from twisted.logger import Logger

from lie_graph.graph_orm import GraphORM
from lie_graph.graph_algorithms import dfs_paths
from lie_graph.graph_helpers import renumber_id
from lie_system import WAMPTaskMetaData

from .workflow_common import _schema_to_data

# Get the task schema definitions from the default task_schema.json file
TASK_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'task_schema.json')
task_schema = json.load(open(TASK_SCHEMA_PATH))

logging = Logger()


class _TaskBase(object):

    @property
    def status(self):

        return self.nodes[self.nid].get('status')

    @status.setter
    def status(self, status):
        options = (
            "ready", "submitted", "running", "failed", "aborted",
            "completed", "disabled")
        status = status.lower()
        if status in options:
            self.nodes[self.nid]['status'] = status
        else:
            logging.error('Task status tag {0} not supported'.format(status))

    def init_task(self, **kwargs):
        """
        Initiate the task.

        Called when adding a new task to the workflow.
        Initiates an instance of the default task data dictionary and adds
        type specific data to it.
        """

        logging.info(
            'Init task {0} ({1}). Update attributes'.format(
                self.nid, self.task_name))

        task_data = _schema_to_data(task_schema, data=kwargs)
        jsonschema.validate(task_data, task_schema)

        self.nodes[self.nid].update(task_data)

    def update_session(self, session_data=None):
        """
        Update a (WAMP) session
        """

        current_session = self.nodes[self.nid].get('session', {})
        updated_session = WAMPTaskMetaData(metadata=current_session)

        if session_data:
            updated_session.update(session_data)

        self.nodes[self.nid]['session'] = updated_session.dict()
        return self.nodes[self.nid]['session']

    def _process_reference(self, ref):
        """
        Resolve reference
        """

        if ref.startswith('$'):
            split = ref.strip('$').split('.')
            ref_nid = int(split[0])
            ref_key = split[1]

            return self._full_graph.nodes[ref_nid]['output_data'].get(ref_key, None)
        return ref

    def get_input(self):
        """
        Prepaire the input data
        """

        input_dict = {}
        for key, value in self.nodes[self.nid].get('input_data', {}).items():

            # Resolve reference
            if isinstance(value, str):
                input_dict[key] = self._process_reference(value)
            elif isinstance(value, list):
                input_dict[key] = [self._process_reference(v) if isinstance(v, str) else v for v in value]
            else:
                input_dict[key] = value

        return input_dict

    def cancel(self):
        """
        Cancel the task
        """

        if not self.active:
            logging.info(
                'Unable to cancel task {0} ({1}) not active'.format(
                    self.nid, self.task_name))
            return

        self.status = 'aborted'
        self.active = False
        logging.info(
            'Canceled task {0} ({1})'.format(self.nid, self.task_name))


class Task(_TaskBase):
    """
    A task runner class that runs Python functions or classes in
    threaded mode using Twisted `deferToThread`.
    """

    def run_task(self, runner, callback=None, errorback=None):

        logging.info('running "{0}"'.format(self.task_name))

        # Get task session
        session = WAMPTaskMetaData(
            metadata=self.nodes[self.nid].get('session', {}))

        d = threads.deferToThread(runner,
                                  session=session.dict(),
                                  **self.get_input())
        if errorback:
            d.addErrback(errorback, self.nid)
        if callback:
            d.addCallback(callback, self.nid)

        if not reactor.running:
            reactor.run(installSignalHandlers=0)


class WampTask(_TaskBase):

    def run_task(self, runner, callback, errorback=None):
        method_url = six.text_type(self.uri)
        logging.info('Task {0} ({1}) running on {2}'.format(
            self.nid, self.task_name, method_url))

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(
            metadata=self.nodes[self.nid].get('session', {}))

        # Call the service
        deferred = runner(
            method_url, session=session.dict(), **self.get_input())

        # Attach error callback
        if errorback:
            deferred.addErrback(errorback, self.nid)

        # Attach callback if needed
        deferred.addCallback(callback, self.nid)


class BlockingTask(_TaskBase):
    """
    A task runner class that runs Python functions or classes in
    blocking mode resulting in the main workflow thread to be
    blocked until a result is returned or an exception is raised.
    """

    def run_task(self, runner, callback, errorback=None):

        logging.info('running "{0}"'.format(self.task_name))

        # Get task session
        session = WAMPTaskMetaData(
            metadata=self.nodes[self.nid].get('session', {}))
        
        try:
            output = runner(
                session=session.dict(), **self.get_input())
        except Exception as e:
            if errorback:
                return errorback(e, self.nid)
            else:
                logging.error(
                    'Error in running task {0} ({1})'.format(
                        self.nid, self.task_name))
                logging.error(e)
                return

        callback(output, self.nid)


class StartTask(_TaskBase):
    """
    Workflow start task

    Responsible for handling intitial workflow input and pre-processing
    """

    def _start(self, session=None, **kwargs):

        # Check input
        status = 'completed'
        self.nodes[self.nid]['output_data'] = self.get_input()
        if 'file' in self.nodes[self.nid]['output_data']:
            path = self.nodes[self.nid]['output_data']['file']
            if not os.path.exists(path):
                logging.error('File does not exist: {0}'.format(path))
                status = 'failed'
            else:
                with open(path) as inp:
                    self.nodes[self.nid]['output_data']['file'] = inp.read()

        session.status = status
        session._metadata['utime'] = int(time.time())

        return {'session': session.dict()}

    def run_task(self, runner, callback, errorback=None):
        """
        Start tasks are always run as Twisted deferToThread to
        start a Twisted reactor to be used by other tasks.
        """

        session = WAMPTaskMetaData(
            metadata=self.nodes[self.nid].get('session', {}))

        #callback(self._start(session=session, **self.get_input()), self.nid)
        #return

        d = threads.deferToThread(self._start,
                                  session=session,
                                  **self.get_input())
        if errorback:
            d.addErrback(errorback, self.nid)
        if callback:
            d.addCallback(callback, self.nid)

        if not reactor.running:
            reactor.run(installSignalHandlers=0)


class Choice(_TaskBase):

    def run_task(self, runner, callback=None, errorback=None):
        """
        Make a choice for one or more connected task based on
        criteria using the input data.

        :param pos: task to choose when evaluation is positive
        :type pos:  :py:list
        :param neg: task to choose when evaluation is negative
        :type pos:  :py:list
        """

        session = WAMPTaskMetaData(
            metadata=self.nodes[self.nid].get('session', {}))

        finput = self.get_input()
        try:
            output = runner(
                session=session.dict(), **finput)
        except Exception as e:
            if errorback:
                return errorback(e, self.nid)
            else:
                logging.error(
                    'Error in running task {0} ({1})'.format(
                        self.nid, self.task_name))
                logging.error(e)
                return

        # Disable edges to tasks not in choice_nids
        disabled = []
        choice_nids = output.get('choice', [])
        for task in self.children():
            if not task.nid in choice_nids:
                task.status = 'disabled'
                disabled.append(str(task.nid))
        logging.info('Disabled tasks: {0}'.format(','.join(disabled)))

        output.update(finput)
        callback(output, self.nid)


class Mapper(_TaskBase):
    """
    Mapper class

    Task that parallelises input from an array to all descending tasks or
    upto a task that is assigned to collect the output the task
    lineage created by this mapper class.

    Tasks lineages are duplicated dynamically. The mapping procedure may be
    customized by providing a specialised runner function to the run_task
    method
    """

    def run_task(self, runner=None, callback=None, errorback=None):
        """
        :param runner:    custom mapper function
        :type runner:     function
        :param callback:  workflow runner callback function to pass results to
        :type callback:   function
        :param errorback: workflow runner errorback function to call upon
                          function error
        :type errorback:  function
        """

        map_argument = self.get('mapper_arg', 'mapper')
        task_input = self.get_input()
        if map_argument not in task_input:
            errorback(
                'Task {0} ({1}), mapper argument {2} not in input'.format(
                    self.nid, self.task_name, map_argument), self.nid)

        mapped = task_input[map_argument]
        if len(mapped):

            logging.info(
                'Task {0} ({1}), {2} items to map'.format(
                    self.nid, self.task_name, len(mapped)))

            # Get task session
            session = WAMPTaskMetaData(
                metadata=self.nodes[self.nid].get('session'))

            # Get the full descendant lineage from this Mapper task to
            # the Collect task assigned to the mapper
            collector_task = self._full_graph.query_nodes(
                {'to_mapper': self.nid})
            if collector_task:
                maptid = list(itertools.chain.from_iterable(
                    dfs_paths(self._full_graph, self.nid, collector_task.nid)))
                maptid = sorted(set(maptid))
                maptid.remove(self.nid)
                maptid.remove(collector_task.nid)
            else:
                maptid = self.descendants(return_nids=True)

            # Create sub graph of the mapper tasks lineage.
            # Call errorback if no task lineage.
            # A subgraph is a deep copy of the full graph but with all edges.
            # remove edges not having any link to the mapped tasks.
            if maptid:
                subgraph = self._full_graph.getnodes(maptid).copy(clean=False)
                maptidset = set(maptid)
                for edge in list(subgraph.edges.keys()):
                    if not set(edge).intersection(maptidset):
                        subgraph.remove_edge(edge)
            else:
                errorback(
                    'Task {0} ({1}), no tasks connected to Mapper task'.format(
                        self.nid, self.task_name), self.nid)
                return

            first_task = maptid[0]
            last_task = maptid[-1]
            mapper_data_mapping = self._full_graph.edges[(self.nid, first_task)]
            mapped_children = [first_task]
            for task in range(len(mapped)-1):

                g, tidmap = renumber_id(subgraph, self._full_graph._nodeid)
                self._full_graph += g

                if collector_task:
                    self._full_graph.add_edge(
                        tidmap[last_task], collector_task.nid)

                first_task = tidmap[first_task]
                last_task = tidmap[last_task]
                mapped_children.append(first_task)

            for i, child in enumerate(mapped_children):

                child = self._full_graph.getnodes([child])

                # Define input for the copied task
                if 'input_data' not in child:
                    self._full_graph.nodes[child.nid]['input_data'] = {}

                # Add all other input arguments to
                for key, value in task_input.items():
                    if not key == map_argument:
                        child['input_data'][key] = value

                # List item to dict if needed and perform data mapping
                tomap = mapped[i]
                if not isinstance(tomap, dict):
                    datamap = mapper_data_mapping.get('data_mapping', {})
                    datamap = datamap.get(map_argument, map_argument)
                    tomap = {datamap: tomap}
                child['input_data'].update(tomap)

            session.status = 'completed'
            callback({'session': session.dict()}, self.nid)

        else:
            errorback('Task {0} ({1}), no items to map'.format(
                self.nid, self.task_name), self.nid)


WORKFLOW_ORM = GraphORM(inherit=False)
WORKFLOW_ORM.map_node(StartTask, {'task_type': 'Start'})
WORKFLOW_ORM.map_node(Task, {'task_type': 'Task'})
WORKFLOW_ORM.map_node(Choice, {'task_type': 'Choice'})
WORKFLOW_ORM.map_node(BlockingTask, {'task_type': 'BlockingTask'})
WORKFLOW_ORM.map_node(WampTask, {'task_type': 'WampTask'})
WORKFLOW_ORM.map_node(Mapper, {'task_type': 'Mapper'})
