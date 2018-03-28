# -*- coding: utf-8 -*-

import os
import shutil

from mdstudio.api.endpoint import endpoint
from mdstudio.component.session import ComponentSession
from lie_amber.ambertools import (amber_acpype, amber_reduce)


class AmberWampApi(ComponentSession):
    """
    AmberTools WAMP methods.
    """
    def authorize_request(self, uri, claims):
        return True

    @endpoint('acpype', 'acpype-request', 'acpype-response')
    def run_amber_acpype(self, request, claims):
        """
        Call amber acpype package using a molecular `structure`.
        See the `schemas/endpoints/acpype-request.v1.json for
        details.
        """
        # Load ACPYPE configuration and update
        acpype_config = get_amber_config(request)

        return call_amber_package(request, acpype_config, amber_acpype)

    @endpoint('reduce', 'reduce-request', 'reduce-response')
    def run_amber_reduce(self, request, claims):
        """
        Call amber reduce using a  a molecular `structure`.
        See the the `schemas/endpoints/reduce-request.v1.json for
        details.
        """
        reduce_config = get_amber_config(request)

        return call_amber_package(request, reduce_config, amber_reduce)


def get_amber_config(request):
    """
    Remove the keywords not related to amber
    """
    d = request.copy()
    keys = ['workdir', 'structure', 'from_file']

    for k in keys:
        if k in d:
            d.pop(k)

    return d


def call_amber_package(request, config, function):
    """
    Create temporate files and invoke the `function` using `config`.
    """
    # Create workdir and save file
    workdir = request['workdir']
    create_dir(workdir)
    tmp_file = create_temp_file(
        request['structure'], request['from_file'], workdir)

    # Run amber function
    output = function(tmp_file, config, workdir)

    status = 'failed' if output is None else 'completed'

    return {'status': status, 'output': output}


def copy_structure(structure, from_file, tmp_file):
    if from_file and os.path.exists(structure):
        shutil.copyfile(structure, tmp_file)
    else:
        with open(tmp_file, 'w') as inp:
            inp.write(structure)


def create_dir(folder):
    if not os.path.isdir(folder):
        os.mkdir(folder)


def create_temp_file(structure, from_file, workdir):
    tmp_file = os.path.join(workdir, 'input.mol2')
    copy_structure(structure, from_file, tmp_file)

    return tmp_file
