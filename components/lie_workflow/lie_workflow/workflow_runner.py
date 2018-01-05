# -*- coding: utf-8 -*-

import os
import time
import threading
import json

from twisted.logger import Logger
from autobahn.wamp.exception import ApplicationError
from lie_system import WAMPTaskMetaData

from .workflow_common import WorkflowError, load_task_function, concat_dict, ManageWorkingDirectory

# Get the task schema definitions from the default task_schema.json file
TASK_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'task_schema.json')
task_schema = json.load(open(TASK_SCHEMA_PATH))

logging = Logger()


class _WorkflowQueryMethods(object):
    """
    Mixin class wit helper methods to query workflow global metadata
    """

    @property
    def is_running(self):
        """
        Returns the global state of the workflow as running or not.

        :rtype: :py:bool
        """

        return getattr(self.workflow, 'is_running', False)

    @is_running.setter
    def is_running(self, state):
        """
        Set the global state of the workflow as running or not.
        If the new state is 'False' first check if there are no other parallel
        active tasks.
        """

        if not state:
            state = len(self.active_tasks) >= 1
        self.workflow.is_running = state

    @property
    def is_completed(self):
        """
        Is the workflow completed successfully or not

        :rtype: :py:bool
        """

        return all(
            [task['status'] in ('completed', 'disabled')
             for task in self.workflow.nodes.values()])

    @property
    def has_failed(self):
        """
        Did the workflow finish unsuccessfully?
        True if there are no more active tasks and at least one task has failed
        or was aborted
        """

        if not len(self.active_tasks) and all(
                [task['status'] in ('failed', 'aborted')
                 for task in self.workflow.nodes.values()]):
            return True

        return False

    @property
    def starttime(self):
        """
        Return the time stamp at which the workflow was last started

        :rtype: :py:int
        """

        return getattr(self.workflow, 'start_time', None)

    @property
    def finishtime(self):
        """
        Return the time stamp at which the workflow finished or None
        if it has not yet finished

        :rtype: :py:int
        """

        if not self.is_running:
            return getattr(self.workflow, 'update_time', None)
        return None

    def runtime(self, tid=None):
        """
        Return the total workflow runtime in seconds or the
        runtime of a specific task defined by the task ID

        :param tid: task for wich to calculate the runtime
        :type tid:  :py:int

        :rtype: :py:int
        """

        if tid:
            task = self.workflow.getnodes(tid)
            session = task.session
            return session.get('utime', 0) - session.get('itime', 0)

        start = self.starttime or 0
        end = self.finishtime or 0
        if self.is_running:
            end = getattr(self.workflow, 'update_time', int(time.time()))

        return end - start

    @property
    def active_tasks(self):
        """
        Return all active tasks in the workflow

        :rtype: :py:list
        """

        return [tid for tid, task in self.workflow.nodes.items()
                if task['active']]

    @property
    def failed_task(self):

        for task in self.workflow.nodes.values():
            if task.get('status') == 'failed':
                return task['nid']

    @property
    def active_breakpoint(self):
        """
        Return task with active breakpoint or None
        """

        for task in self.workflow.nodes.values():
            if task.get('breakpoint', False):
                return task['nid']

    def summary(self):

        print('task  tid  links  status  runtime  output')
        for tid, task in self.workflow.nodes.items():
            session = task.get('session', {})
            print('{0}  {1}  {2}  {3}  {4}  {5}'.format(
                task['task_name'],
                tid,
                self.workflow.adjacency[tid],
                task['status'],
                session.get('utime', 0) - session.get('itime', 0),
                task.get('output_data', {})
            ))


class WorkflowRunner(_WorkflowQueryMethods):
    """
    This is the main class for running microservice oriented workflows.

    Running a workflow is based on a workflow specification build using the
    `WorkflowSpec` class. Such a workflow can be loaded into the `Workflow`
    class simply by overloading the Workflow.workflow attribute.
    The `Workflow` class also inherits the methods from the `WorkflowSpec`
    class allowing to build specification right from the `Workflow` class
    and even change a running workflow.

    The execution of workflow steps is performed on a different thread than
    the main Workflow object allowing the user to interact with the running
    workflow.
    The DAG including the metadata dat is generated while executing the steps
    can be serialized to JSON for persistent storage. The same JSON object is
    used as input to the Workflow class validated by a Workflow JSON schema.

    :param workflow:   the workflow DAG to run
    :type workflow:    JSON object
    """

    def __init__(self, workflow=None):

        # Workflow DAG placeholder
        self.workflow = workflow

        # Init inherit classes such as the WorkflowSpec
        super(WorkflowRunner, self).__init__()

        # Define task runner
        self.task_runner = None
        self.workflow_thread = None

    def _collect_input(self, task):
        
        # Get all parent task IDs
        parent_tasks = task.all_parents(return_nids=True)

        # Check if there are failed tasks among the ancestors and if we are
        # allowed to continue with less
        failed_ancestors = [
            tid for tid in parent_tasks if self.workflow.nodes[tid]['status']
            in ('failed', 'aborted')]
        if failed_ancestors:
            logging.error(
                'Failed parent tasks detected. Unable to collect all output')

        # Check if we can continue if only one of the input streams is available
        if task.get('continue_with_one', False):
            continue_next = any([self.workflow.nodes[tid]['status'] in
                                 ('completed', 'disabled') for tid in parent_tasks])
        # Check if the ancestors are all completed
        else:
            continue_next = all([self.workflow.nodes[tid]['status'] in
                                 ('completed', 'disabled') for tid in parent_tasks])

        collected_output = []
        if continue_next:
            msg = 'Task {0} ({1}): Output of {2} parent tasks available, continue'
            logging.info(msg.format(task.nid, task.task_name, len(parent_tasks)))
            
            # Collect output of previous tasks and apply data mapper and data
            # selection if needed
            for tid in parent_tasks:
                mapper = self.workflow.edges[(tid, task.nid)].get('data_mapping', {})
                select = self.workflow.edges[(tid, task.nid)].get('data_select',
                                            self.workflow.nodes[tid].get('output_data', {}).keys())
                new_dict = {mapper.get(k, k): '${0}.{1}'.format(tid, k) for k, v in
                            self.workflow.nodes[tid].get('output_data', {}).items() if k in select}
                collected_output.append(new_dict)
        else:
            logging.info(
                'Task {0} ({1}): Not all output available yet'.format(
                    task.nid, task.task_name))
            return

        return concat_dict(collected_output)
    
    def _error_callback(self, failure, tid):
        """
        Process the output of a failed task and stage the next task to run
        if allowed

        :param failure: Twisted deferred error stack trace
        :type failure:  exception
        :param tid:     Task ID of failed task
        :type tid:      :py:int
        """

        task = self.workflow.getnodes(tid)
        task.active = False
        task.status = 'failed'

        failure_message = ""
        if isinstance(failure, Exception) or isinstance(failure, str):
            failure_message = str(failure)
        elif isinstance(failure.value, ApplicationError):
            failure_message = failure.value.error_message()
        else:
            failure.getErrorMessage()

        logging.error(
            'Task {0} ({1}) crashed with error: {2}'.format(
                task.nid, task.task_name, failure_message))
        self.is_running = False
        self.workflow.update_time = int(time.time())

        return

    def _output_callback(self, output, tid):
        """
        Process the output of a task and stage the next task to run

        :param output: output of the task
        :type output:  :py:dict

        TODO: what to do if output is returned but without a session object
              or session object is unchanged? Set a breakpoint and let the
              user check?
        """
        
        # Get the task
        task = self.workflow.getnodes(tid)

        # Output callback called means task is not active.
        # TODO: this will change when returns status == 'running'
        task.active = False

        # If the task returned no output at all, fail it
        session = WAMPTaskMetaData()
        if output:
            session = WAMPTaskMetaData(metadata=output.get('session'))
            # Remove when done
            del output['session']

        else:
            logging.error(
                'Task {0} ({1}) returned no output'.format(
                    task.nid, task.task_name))
            task.status = 'failed'

        # Update the task output data only if not already 'completed'
        if task.status not in ('completed', 'failed'):
            if 'output_data' not in self.workflow.nodes[tid]:
                self.workflow.nodes[tid]['output_data'] = {}
            self.workflow.nodes[tid]['output_data'].update(output)

            # Update the task meta data
            task.status = session.status
            self.workflow.nodes[tid]['session'] = session.dict()
            self.workflow.update_time = int(time.time())

        logging.info(
            'Task {0} ({1}), status: {2}'.format(
                task.nid, task.task_name, task.status))

        # If the task is completed, go to next
        next_task_nids = []
        if task.status == 'completed':
            
            # Get next task(s) to run
            next_tasks = [t for t in task.children() if t.status != 'disabled']
            logging.info(
                '{0} new tasks to run with the output of {1} ({2})'.format(
                    len(next_tasks), task.nid, task.task_name))

            for ntask in next_tasks:
                # Get output from all tasks connected to new task
                output = self._collect_input(ntask)
                if output is not None:
                    if 'input_data' not in ntask.nodes[ntask.nid]:
                        ntask.nodes[ntask.nid]['input_data'] = {}
                
                    ntask.nodes[ntask.nid]['input_data'].update(output)
                    next_task_nids.append(ntask.nid)

                # TODO: all tasks should provide output but the start task does not. Fix
                elif task.task_type == 'Start':
                    next_task_nids.append(ntask.nid)

        # If the task failed, retry if allowed and reset status to "ready"
        if task.status == 'failed' and task.retry_count > 0:
            task.retry_count = task.retry_count - 1
            task.status = 'ready'

            logging.warn(
                'Task {0} ({1}) failed. Retry ({2} times left)'.format(
                    task.nid, task.task_name, task.retry_count))
            next_task_nids.append(task.nid)

        # If the active failed an no retry is allowed, stop working.
        if task.status == 'failed' and task.retry_count == 0:
            logging.error('Task {0} ({1}) failed'.format(
                task.nid, task.task_name))
            self.is_running = False
            return

        # If the task is completed but a breakpoint is defined, wait for the
        # breakpoint to be lifted
        if task.breakpoint:
            logging.info(
                'Task {0} ({1}) finished but breakpoint is active'.format(
                    task.nid, task.task_name))
            self.workflow.is_running = False
            return

        # Not more new tasks
        if not next_task_nids:

            # Not finsihed but no active tasks anymore/breakpoint
            if not self.active_tasks and not self.is_completed:
                logging.info(
                    'The workflow is not finished but there are no more active tasks')
                breakpoint = self.active_breakpoint
                if breakpoint:
                    logging.info(
                        'Active breakpoint on task {0}'.format(breakpoint))
                self.is_running = False
                return

            # Finish of if there are no more tasks to run and all are completed
            if self.is_completed or self.has_failed:
                logging.info('finished workflow')
                self.is_running = False
                return

        # Launch new tasks
        for tid in next_task_nids:
            self._run_task(tid)

    def _run_task(self, tid):
        """
        Run a task by task ID (tid)

        Primary function to run a task using the task_runner registered with
        the class or a custom Python runner function or class.
        This function together with the output and error callbacks are run from
        within the task runner thread.

        Tasks to run are processed using the following rules:

        * If the task is currently active, stop and have the output callback
          function deal with it.
        * If the task has status 'ready' run it.
        * In all other cases, pass the task data to the output callback
          function. This is usefull for hopping over finished tasks when
          relaunching a workflow for instance.

        :param tid: Task node identifier
        :type tid:  :py:int
        """

        # Get the task object from the graph. nid is expected to be in graph.
        # Check if the task has a 'run_task' method.
        task = self.workflow.getnodes(tid)
        err = 'Task {0} ({1}) requires "run_task" method'.format(task.nid, task.task_name)
        assert hasattr(task, 'run_task'), logging.error(err)

        # Bailout if the task is active
        if task.active:
            logging.debug(
                'Task {0} ({1}) already active'.format(
                    task.nid, task.task_name))
            return

        # Run the task if status is 'ready'
        if task.status == 'ready':

            # Update the task session
            session = WAMPTaskMetaData()
            if 'authid' in self.workflow.nodes[self.workflow.root]['session']:
                session.authid = self.workflow.nodes[self.workflow.root]['session']['authid']
            self.workflow.nodes[tid]['session'] = session.dict()

            # Check if there is 'input' defined
            # TODO: should be handled by a common function
            if 'input_data' not in task:

                # Check if previous task has output and use it as input
                # for the current
                parent = task.parent()
                if parent and 'output_data' in parent:
                    logging.info(
                        'Use output of parent task to tid {0} ({1})'.format(
                            task.nid, parent.nid))

                    # Define reference to output
                    ref = dict(
                        [(key, '${0}.{1}'.format(parent.nid, key)) for key
                         in parent.output_data])
                    self.input(tid, **ref)

            # Do we need to store data to disk
            if task.get('store_output', False) and 'workdir' not in task.get('input_data', {}):
                workdir = self.workflow.nodes[self.workflow.root]['workdir']
                workdir = os.path.join(
                    workdir, 'task-{0}-{1}'.format(
                        task.nid, session['task_id']))
                wd = ManageWorkingDirectory(workdir=workdir)
                if wd.create():
                    self.input(task.nid, workdir=wd.path)

            self.is_running = True
            self.workflow.update_time = int(time.time())

            # Set workflow task meta-data
            task.active = True
            task.status = 'running'

            logging.info(
                'Task {0} ({1}), status: {2}'.format(
                    task.nid, task.task_name, task.status))
            task.run_task(
                load_task_function(task.get('custom_func', None)) or self.task_runner,
                callback=self._output_callback,
                errorback=self._error_callback)

        # In all other cases, pass task data to default output callback
        # instructing it to not update the data but decide on the followup
        # workflow step to take.
        else:
            self._output_callback({'session': task.get('session')}, tid)

    def delete(self):
        pass

    def cancel(self):
        """
        Cancel the full workflow.

        This method will send a cancel request to all active tasks in the
        running workflow. Once there are no more active tasks the workflow
        run method will stop and the deamon thread will be closed.

        For canceling specific tasks please use the `cancel` function of the
        specific task retrieved using the `WorkflowSpec.get_task` method or
        workflow graph methods.
        """

        if not self.is_running:
            logging.info('Workflow is not running.')
            return

        # Get active task
        active_tasks = [task['nid'] for task in self.workflow.nodes.values()
                        if task['active']]

        logging.info(
            'Canceling {0} active tasks in the workflow: {1}'.format(
                len(active_tasks), active_tasks))

        for tid in active_tasks:
            task = self.workflow.getnodes(tid)
            task.cancel()

        self.is_running = False
        self.workflow.update_time = int(time.time())

    def step_breakpoint(self, tid):
        """
        Continue a workflow at a task that is paused by a breakpoint

        :param tid: workflow task ID with active breakpoint
        :type tid:  :py:int
        """

        # Do some checks
        if tid not in self.workflow.nodes:
            logging.warn('No task with ID {0} in workflow'.format(tid))
            return

        task = self.workflow.getnodes(tid)
        if not task.get('breakpoint', False):
            logging.warn('No active breakpoint set on task {0}'.format(tid))
            return

        # Remove the breakpoint
        task.breakpoint = False
        logging.info(
            'Remove breakpoint on task {0} ({1})'.format(tid, task.task_name))

    def input(self, tid, **kwargs):
        """
        Define task input and configuration data
        """

        if tid not in self.workflow.nodes:
            logging.warn('No task with ID {0} in workflow'.format(tid))
            return

        if 'input_data' not in self.workflow.nodes[tid]:
            self.workflow.nodes[tid]['input_data'] = {}

        self.workflow.nodes[tid]['input_data'].update(kwargs)

    def output(self, tid=None):
        """
        Get workflow output
        Returns the output associated to all terminal tasks (leaf nodes) of
        the workflow or of any intermediate tasks identified by the task ID

        :param tid: task ID to return output for
        :type tid:  :py:int
        """

        if tid not in self.workflow.nodes:
            logging.warn('No task with ID {0} in workflow'.format(tid))

        if tid:
            leaves = self.workflow.getnodes(tid)
        else:
            leaves = self.workflow.leaves()

        output = {}
        for task in leaves:
            if task.status == 'completed':
                output[task.nid] = task.output_data

        return output

    def set_wamp_session(self, tid=None, session_data=None):
        """
        Initiate a WAMP session in the (Start) node
        """

        tid = tid or self.workflow.root
        task = self.workflow.getnodes(tid)
        return task.update_session(session_data)

    def run(self, tid=None):
        """
        Run the workflow specification or instance thereof until finished,
        failed or a breakpoint is reached.

        A workflow is started from the first 'Start' task and then moves
        onwards. It can be started from any other task provided that the
        parent task was successfully completed.

        The workflow will be executed on a different thread allowing for
        interactivity with the workflow instance while the workflow is
        running.

        :param tid:      Start the workflow from task ID
        :type tid:       :py:int
        """

        # Start from workflow root by default
        tid = tid or self.workflow.root

        # Check if tid exists
        if tid not in self.workflow.nodes:
            raise WorkflowError(
                'Task with tid {0} not in workflow'.format(tid))

        # If there are steps that store results locally (store_output == True)
        # a working directory should be defined.
        if any([task.get('store_output', False) for task in self.workflow.nodes.values()]):
            workdir = self.workflow.nodes[self.workflow.root].get('workdir')
            workdir = ManageWorkingDirectory(workdir=workdir)
            if not workdir.path:
                raise WorkflowError('Local storage requested but no storage path defined')
            else:
                self.workflow.nodes[self.workflow.root]['workdir'] = workdir.create()

        logging.info(
            'Running workflow: {0}, start task ID: {1}'.format(
                self.workflow.title, tid))

        # Always set is_running to True to allow for immediate interactive use
        # preventing race conditions. If the already running, return
        if self.is_running:
            return
        self.workflow.is_running = True

        # Set workflow start time if not defined. Don't rerun to allow
        # continuation of unfinished workflow.
        if not hasattr(self.workflow, 'start_time'):
            self.workflow.start_time = int(time.time())

        self.workflow_thread = threading.Thread(target=self._run_task, args=[tid])
        self.workflow_thread.daemon = True
        self.workflow_thread.start()
