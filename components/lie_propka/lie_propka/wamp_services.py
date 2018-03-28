# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

import os
import logging
import tempfile
import MDAnalysis as mda

from mdstudio.api.endpoint import endpoint
from mdstudio.component.session import ComponentSession

from propka import molecular_container
from propkatraj import get_propka
from .propka_helpers import parse_propka_pkaoutput


class Struct:

    def __init__(self, entries):
        self.__dict__.update(entries)


class RunPropka(object):
    def run_propkatraj(
            self, topology=None, trajectory=None, sel='protein',
            start=None, stop=None, step=None, session=None):
        """
        Run propkatraj

        Runs Propka3.1 on a MD trajectory in a format that can be handled by
        the MDanalysis package

        :param kwargs:  PROPKA options
        :type kwargs:   :py:dict
        :param session: WAMP session object
        :type session:  :py:dict

        :return:        PROPKA results
        :rtype:         :py:dict
        """
        # Load trajectory
        universe = mda.Universe(topology, trajectory)

        # Run propkatraj
        pkatrajdf = get_propka(universe, sel=sel, start=start, stop=stop, step=step)

        return {'session': session}

    def run_propka(self, propka_config):
        """
        see: https://github.com/jensengroup/propka-3.1
        """
        # Parse titration
        if propka_config['titrate_only']:
            newtitr = []
            for titr in propka_config['titrate_only'].split(','):
                chain, resnum_str = titr.split(":")
                newtitr.append((chain, int(resnum_str), " "))
            propka_config['titrate_only'] = newtitr

        # Create workdir and save file
        currdir = os.getcwd()
        workdir = os.path.join(propka_config['workdir'], tempfile.gettempdir())
        if not os.path.isdir(workdir):
            os.makedirs(workdir)
        os.chdir(workdir)
        logging.info('PropKa working directory: {0}'.format(workdir))

        pdb = propka_config['pdb']
        if propka_config['from_file']:
            pdbfile = os.path.join(workdir, 'propka.pdb')
            with open(pdbfile) as infile:
                infile.write(pdb)
        else:
            pdbfile = pdb

        # Wrap options dictionary as object (needed for PROPKA)
        propka_config = Struct(propka_config)

        # Run PROPKA
        my_molecule = molecular_container.Molecular_container(pdbfile, propka_config['parameters'])
        my_molecule.calculate_pka()
        my_molecule.write_pka()
        logging.info('Running PROPKA 3.1: {0}'.format(type(my_molecule.version).__name__.split('.')[-1]))

        # Parse PROPKA output
        output = {}
        for output_types in ('pka', 'propka_input'):
            outputfile = os.path.join(workdir, '{0}.{1}'.format(my_molecule.name, output_types))

            if not os.path.isfile(outputfile):
                logging.error('Propka failed to create output: {0}'.format(outputfile))
                status = 'failed'
                continue

            if output_types == 'pka':
                pkadf = parse_propka_pkaoutput(outputfile)
                output['pka'] = pkadf.to_dict()
                status = 'completed'

            output['{0}_file'.format(output_types)] = outputfile

        # Calculate molecule PI
        pi_labels = ('pi_folded', 'pi_unfolded')
        for i, pi in enumerate(my_molecule.getPI()):
            output[pi_labels[i]] = pi

        # Change back to original dir and return results
        os.chdir(currdir)
        return {'status': status, 'output': output}


class PropkaWampApi(ComponentSession, RunPropka):

    def authorize_request(self, uri, claims):
        """
        If you were allowed to call this in the first place,
        I will assume you are authorized
        """
        return True

    @endpoint('propka', 'propka_request', 'propka_response')
    def run_propka(self, request, claims):
        """
        For a detailed input description see:
          lie_propka/schemas/endpoints/propka_request.json

        For a detailed output description see:
          lie_propka/schemas/endpoints/propka_response.json
        """
        return super().run_propka(request)
