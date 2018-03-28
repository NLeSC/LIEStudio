# -*- coding: utf-8 -*-

"""
IO and subprocess related utility functions.

TODO: Should eventually make there way into the mdstudio module
      for general use.
"""

import os
import subprocess
import time
import json
import logging
import pkgutil

logger = logging.getLogger(__name__)


def _schema_to_data(schema, data=None, defdict=None):

    default_data = defdict or {}

    properties = schema.get('properties', {})

    for key, value in properties.items():
        if 'default' in value:
            if 'properties' in value:
                default_data[key] = _schema_to_data(value)
            else:
                default_data[key] = value.get('default')

    # Update with existing data
    if data:
        default_data.update(data)

    return default_data


def prepaire_work_dir(path, user=None, create=False):
    """
    Prepaire a docking working directory at the target path.
    The docking directory is a unique path with a basename composed out of:

        docking-<user name>-<time stamp>

    The function will check the existance of the target path, will try to
    create it if needed and checks if it is writable.
    If any of these checks fail, None will be returned.

    :param path:   target path to prepaire the dockign directory in
    :type path:    str
    :param user:   optional user name to use in the docking path basename
    :type user:    str
    :param create: create the docking directory or return path
    :type create:  bool

    :return:       path name or None in case path could not be created
    :rtype:        str
    """

    # Check if path
    if not path:
        logger.debug('No path defined')
        return None

    # Check if target path exists
    path = os.path.abspath(path)
    if not os.path.exists(path):
        logger.debug('Working directory does not exist. Try creating it: {0}'.format(path))

        # Does not exist, try to create it
        try:
            os.makedirs(path)
        except BaseException:
            logger.error('Unable to create working directory: {0}'.format(path))
            return None

    # Is target directory writable
    if not os.access(path, os.W_OK):
        logger.error('Working directory not writable: {0}'.format(path))
        return None

    # Compose docking directory basename
    dockdir = os.path.join(path, 'docking-{0}-{1}'.format(user or '', int(time.time())))
    while os.path.exists(dockdir):
        dockdir = os.path.join(path, 'docking-{0}-{1}'.format(user or '', int(time.time()) + 5))

    if create:
        try:
            os.makedirs(dockdir)
        except BaseException:
            logger.error('Unable to create working directory: {0}'.format(dockdir))
            return None
    else:
        logger.debug('Create docking working directory path: {0}'.format(dockdir))

    return dockdir


def cmd_runner(cmd, workdir):

    # Run cli command
    logger.debug('Execute cli process: {0}'.format(' '.join(cmd)))
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=workdir)
    output, errors = process.communicate()
    if process.returncode != 0:
        logger.warn('Executable stopped with non-zero exit code ({0}). Error: {1}'.format(process.returncode, errors))

    return output, errors


PLANTS_DOCKING_SCHEMA = os.path.join(
    pkgutil.get_data('lie_plants_docking', 'schemas/endpoints/docking_request.v1.json'))
settings = _schema_to_data(json.loads(PLANTS_DOCKING_SCHEMA))
