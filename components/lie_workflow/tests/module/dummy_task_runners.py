# -*- coding: utf-8 -*-

"""
file: dummy_task_runners

Dummy task runners to emulate various WAMP microservice response
constructs
"""

import os
import json
import logging
import time
import copy
import jsonschema

from lie_system import WAMPTaskMetaData
from lie_workflow import task_schema

dummy_task_schema_input = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "id": "http://liestudio/schemas/dummy_task.json",
    "title": "Dummy input task",
    "description": "Dummy task input schema",
    "type": "object",
    "properties": {
        "dummy": {
            "description": "Output number from the dummy",
            "type": "integer"
        },
        "sleep": {
            "description": "Let the dummy task sleep for x seconds",
            "type": "integer",
            "default": 0
        },
        "add_number": {
            "description": "Add a number to the input integer",
            "type": "integer",
            "default": 0
        },
        "fail": {
            "description": "Instruct the dummy task to fail",
            "type": "boolean",
            "default": False
        },
        "crash": {
            "description": "Instruct the dummy task to crash",
            "type": "boolean",
            "default": False
        }
    },
    "required": ["dummy"]
}

dummy_task_schema_output = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "id": "http://liestudio/schemas/dummy_task.json",
    "title": "Dummy task output",
    "description": "Dummy task output schema",
    "type": "object",
    "properties": {
        "dummy": {
            "description": "Output number from the dummy",
            "type": "integer"
        }
    }
}

def calculate_accumulated_task_runtime(workflow):
    """
    Calculate cumultative task runtime
    """
    
    runtime = 0
    for tid,task in workflow.nodes.items():
        session = task.get('session')
        if session:
            runtime += (session.get('utime',0) - session.get('itime',0))
    
    return runtime
    
def task_runner(session=None, **kwargs):
    """
    Run a task based on the information in the task_data.
    Task_data is validated according to the JSON task schema
    """
    
    # The session is validated by the WAMP framework but the tasks specific
    # data will have to be validated by the task
    jsonschema.validate(kwargs, dummy_task_schema_input)
    
    # Retrieve the WAMP session information
    session = WAMPTaskMetaData(metadata=session or {})
    
    # Simulate running the task
    time.sleep(kwargs.get('sleep',0))
    
    # Perform some calculations to simulate work
    # Add number to input
    output = kwargs['dummy'] + kwargs.get('add_number',0)
    
    # Fail or not
    if kwargs.get('fail', False):
        session.status = 'failed'
    else:
        session.status = 'completed'
    session._update_time(time_stamp='utime')
    
    # Crash?
    if kwargs.get('crash', False):
        raise Exception("Crashed task")
    
    # Prepaire the output
    session._metadata['utime'] = int(time.time())
    
    return {'session': session.dict(), 'dummy': output}

def reduce_function(session=None, **kwargs):
    """
    Dummy test reducer function taking the 'dummy' output from all previous
    tasks and adding them together
    """
    
    session = WAMPTaskMetaData(metadata=session or {})
    session.status = 'completed'
    session._metadata['utime'] = int(time.time())

    output = {'session': session.dict(), 'dummy': len(kwargs.get('dummy',[]))}
    return output
    