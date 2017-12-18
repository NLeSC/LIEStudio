# -*- coding: utf-8 -*-

"""
file: workflow_spec.py

Classes required to build microservice oriented workflow specifications
 that can be run using the `Workflow` runner class
"""

import os
import json
import time
import jsonschema
import logging

from twisted.logger import Logger

from lie_graph.graph_io.io_json_format import read_dict, write_json
from lie_graph.graph_io.io_helpers import _open_anything

from .workflow_common import WorkflowError, _schema_to_data
from .workflow_task_specs import WORKFLOW_ORM

# Path to default workflow JSON schema part of the module
WORKFLOW_SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__), 'workflow_schema.json')

logging = Logger()


class WorkflowSpec(object):
    """
    Interface class for building workflow specifications.

    A workflow is a Directed Acyclic Graph (DAG) in wich the nodes represent
    tasks and the edges the connections between them. The Workflow class
    acts as manager collecting output from tasks and forwarding it to other
    tasks along the edges.
    The `lie_workflow` DAG follows the workflow principles as described by the
    Workflow Patterns initiative supporting many but not all of the described
    patterns (http://www.workflowpatterns.com).

    The task node is the basic functional unit in the DAG. It accepts input,
    offloads it to a microservice or dedicated Python function or class
    that performs work and collects the returned output.
    Offloading of work is performed by a dedicated task runner class that
    knows how to call external microservice or local Python function/class in
    asynchronous or blocking mode.
    In addition to a task node there are nodes required to construct specific
    workflow patterns such as:

    * Collect: a node that collects and combines the output of various tasks
      before forwarding it to the next.
    * Choice: a node that makes a choice on the next step to take based on the
      output of another node.

    :param init_default: upon class initiation, create default empty workflow.
    :type init_default:  :py:bool
    """

    def __init__(self, init_default=True):

        self.workflow = None

        # Init default empty workflow based on a workflow JSON schema
        if init_default:
            self.new()

    @staticmethod
    def _parse_schema(schema):
        """
        Parse a workflow JSON schema from various input sources

        Supports already parsed schemas as Python dictionaries and all formats
        supported by the `_open_anything` function that includes: strings,
        files, file objects and URL sources.

        :param schema: JSON workflow schema to parse
        :type schema:  mixed

        :return:       parsed schema
        :rtype:        :py:dict
        """

        # Schema already parsed as dictionary
        if isinstance(schema, dict):
            return schema

        # Try parsing using _open_anything
        schema_file_object = _open_anything(schema)
        if schema_file_object:
            return json.load(schema_file_object)
        else:
            logging.error(
                'Unsupported workflow JSON schema format {0}'.format(schema))

    def new(self, schema=WORKFLOW_SCHEMA_PATH):
        """
        Build new (empty) workflow specification based on a JSON schema.

        :param schema: JSON schema
        :type schema:  format supported by the `_parse_schema` method

        TODO: _schema_to_data function is a hack, should be replaced by
        a solid module
        """

        # Parse the schema, no validation performed
        schema_dict = self._parse_schema(schema)

        # Build workflow template from schema
        workflow_template = _schema_to_data(schema_dict)

        # Validate template
        jsonschema.validate(workflow_template, schema_dict)

        # (empty) nodes and edges are usually not available
        for d in ('nodes', 'edges'):
            if d not in workflow_template:
                workflow_template[d] = {}

        # Construct a lie_graph GraphAxis object
        self.workflow = read_dict(workflow_template)
        self.workflow.orm = WORKFLOW_ORM

        # Add start node and make root
        nid = self.add_task(task_type='Start', task_name='start')
        self.workflow.root = nid
        self.workflow.create_time = int(time.time())

        logging.info('Init default empty workflow')

    def load(self, workflow, schema=WORKFLOW_SCHEMA_PATH):
        """
        Load workflow specification

        Initiate a workflow from a workflow specification or instance thereof.
        Checks if the workflow defines a root node and if that node is a Start
        task.

        :param workflow: Predefined workflow object
        :type workflow:  GraphAxis
        """

        # Parse the workflow and the schema to validate the workflow
        workflow = self._parse_schema(workflow)
        schema_dict = self._parse_schema(schema)

        # Validate workflow specification
        jsonschema.validate(workflow, schema_dict)

        # Construct a lie_graph GraphAxis object
        self.workflow = read_dict(workflow)
        self.workflow.orm = WORKFLOW_ORM

        if self.workflow.root is None:
            raise WorkflowError('Workflow does not have a root node defined')

        if self.workflow.nodes[self.workflow.root]['task_type'] != 'Start':
            raise WorkflowError('Workflow root node is not of type: Start')

        wf_title = getattr(self.workflow, 'title', '')
        logging.info(
            'Load workflow specification. Title: {0}'.format(wf_title))

        wf_description = getattr(self.workflow, 'description', '')
        logging.info(
            'Description: {0}'.format(wf_description))

    def save(self, path=None):
        """
        serialize the workflow specification to JSON

        :param path: optionally write JSON string to file
        :type path:  :py:str

        :return: serialized workflow
        :rtype:  JSON string
        """

        json_string = write_json(self.workflow)
        if path:
            pred = os.path.exists(os.path.dirname(path))
            msg = 'Directory does not exist: {0}'.format(os.path.dirname(path))
            assert pred, msg
            try:
                with open(path, 'w') as json_to_file:
                    json_to_file.write(json_string)
                logging.info(
                    'Save workflow {0} to file: {1}'.format(
                        getattr(self.workflow, 'title', ''), path))
            except IOError:
                logging.error(
                    'Unable to write workflow to file: {0}'.format(path))

        return json_string

    def add_task(self, task_name=None, task_type='Task', **kwargs):
        """
        Add a new task to the workflow from the set of supported workflow
        task types defined in the workflow ORM.

        After a task of a specific type is added to the graph its init_task
        method is called wich adds default and type specific metadata to
        the node attributes. Additional keyword arguments to the `add_task`
        method are passed to the init_task method.

        :param task_type: Task type to add
        :type task_type:  :py:str
        :param task_name: Administrative name of the task
        :type task_name:  :py:str
        :param kwargs:    additonal keyword arguments passed to the task
                          init_task method.
        :type kwargs:     :py:dict

        :return:          Task node ID (nid) in the graph
        :rtype:           :py:int
        """

        # Task type needs to be supported by ORM
        pred_1 = isinstance(task_type, str),
        msg_1 = 'Workflow task type needs to be of type string'
        pred_2 = task_type in self.workflow.orm.mapped_node_types.get('task_type', [])
        msg_2 = 'Workflow task type "{0}" not supported by graph ORM'.format(
            task_type)
        assert pred_1, msg_1
        assert pred_2, msg_2

        # Add the task as node
        task_name = task_name or task_type.lower()
        nid = self.workflow.add_node(task_name, task_type=task_type)

        # If the task has a `init_task` method, run it.
        # Pass additonal keyword arguments.
        node = self.workflow.getnodes(nid)
        if hasattr(node, 'init_task'):
            node.init_task(**kwargs)

        return nid

    def connect_task(self, task1, task2, **kwargs):
        """
        Connect tasks by task ID (graph nid)

        Creates the directed graph edge connecting two tasks (nodes) together.
        The `data_mapping` edge argument enables name mapping for the output
        attributes of the first task to the input attributes of the second.

        :param task1:         first task of two tasks to connect
        :type task1:          :py:int
        :param task2:         second task of two tasks to connect
        :type task2:          :py:int
        :param data_mapping:  output-input data mapping
        :type data_mapping:   :py:dict
        :param data_select:   restrict input to selected keywords
        :type data_select:    :py:list
        """

        wf_nodes = self.workflow.nodes
        assert task1 in wf_nodes, 'Task {0} not in workflow'.format(task1)
        assert task2 in wf_nodes, 'Task {0} not in workflow'.format(task2)

        self.workflow.add_edge(task1, task2, **kwargs)

    def get_task(self, nid):
        """
        Return a task by task ID (graph nid)

        :param nid:       nid of task to return
        :type nid:        :py:int
        """

        if nid not in self.workflow.nodes:
            logging.warn('No workflow task with nid: {0}'.format(nid))
            return None

        return self.workflow.getnodes(nid)
