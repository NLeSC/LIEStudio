# -*- coding: utf-8 -*-

import os
import logging
import itertools

from importlib import import_module
from collections import Counter


def _schema_to_data(schema, data=None, defdict=None):

    default_data = defdict or {}

    required = schema.get('required', [])
    properties = schema.get('properties', {})

    for key, value in properties.items():
        if key in required:
            if 'properties' in value:
                default_data[key] = _schema_to_data(value)
            else:
                default_data[key] = value.get('default')

    # Update with existing data
    if data:
        default_data.update(data)

    return default_data


class WorkflowError(Exception):

    def __init__(self, message):

        super(WorkflowError, self).__init__(message)

        logging.error(message)


def load_task_function(python_uri):
    """
    Python function or class loader

    Custom Python function can be run on the local machine using a blocking
    or non-blocking task runner.
    These functions are loaded dynamically ar runtime using the Python URI
    of the function as stored in the task 'custom_func' attribute.
    A function URI is defined as a dot-separated string in which the last
    name defines the function name and all names in front the absolute or
    relative path to the module containing the function. The module needs
    to be in the python path.

    Example: 'path.to.module.function'

    :param python_uri: Python absolute or relative function URI
    :type python_uri:  :py:str

    :return:           function object
    """

    func = None
    if python_uri:
        module_name = '.'.join(python_uri.split('.')[:-1])
        function_name = python_uri.split('.')[-1]

        try:
            imodule = import_module(module_name)
            func = getattr(imodule, function_name)
            logging.debug(
                'Load task runner function: {0} from module: {1}'.format(
                    function_name, module_name))
        except ImportError:
            msg = 'Unable to load task runner function: {0} from module: {1}'
            logging.error(msg.format(function_name, module_name))

    return func


def concat_dict(dict_list):
    """
    Concatenate list of dictionaries to one new dictionary

    Duplicated keys will have their values combined as list.

    :param dict_list:   list of dictionaries to concatenate into a new dict
    :type dict_list:    :py:list

    :return:            Concatenated dictionary
    :rtype:             :py:dict
    """
    keys = list(itertools.chain.from_iterable([d.keys() for d in dict_list]))
    key_count = Counter(keys)
    concatenated = dict([(k, None) if c == 1 else (k, []) for k, c in key_count.items()])

    for d in dict_list:
        for k, v in d.items():
            if key_count[k] > 1:
                concatenated[k].append(v)
            else:
                concatenated[k] = v

    return concatenated


class ManageWorkingDirectory(object):

    def __init__(self, workdir=None):

        self.path = None
        if workdir:
            self.set(workdir)

    @property
    def exists(self):

        if self.path:
            return os.path.exists(self.path)
        return False

    @property
    def iswritable(self):

        return os.access(self.path, os.W_OK)

    @staticmethod
    def _make_abspath(path):

        return os.path.abspath(path)

    def set(self, path):
        """
        Set path.

        :param path: Path to working directory
        :type path:  :py:str
        """

        self.path = self._make_abspath(path)

    def create(self):
        """
        Set working directory to store results.

        :return:        Absolute path to working directory
        :rtype:         :py:str
        """

        if self.exists and self.iswritable:
            logging.info('Project directory exists and writable: {0}'.format(self.path))
            return self.path

        try:
            os.makedirs(self.path, 0755)
        except Exception:
            raise WorkflowError('Unable to create project directory: {0}'.format(self.path))

        return self.path
