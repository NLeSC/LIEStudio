# -*- coding: utf-8 -*-

"""
Classes for protein-ligand docking using the PLANTS software:

  PLANTS: Protein-Ligand ANT System.
  "An ant colony optimization approach to flexible protein-ligand docking" Swarm Intell. 1, 115-134 (2007).
  O. Korb, T. Stützle, T.E. Exner
  URL: http://www.tcd.uni-konstanz.de/research/plants.php
"""

import os
import csv

from twisted.logger import Logger
from lie_config import configwrapper

from .docking_base import DockingBase
from .plants_conf import PLANTS_CONF_FILE_TEMPLATE
from .utils import cmd_runner, settings
from .clustering import coords_from_mol2, ClusterStructures


@configwrapper('lie_plants_docking')
class PlantsDocking(DockingBase):
    """
    Class for running a protein-ligand docking using the PLANTS docking
    software:

      PLANTS: Protein-Ligand ANT System.
      "An ant colony optimization approach to flexible protein-ligand
       docking" Swarm Intell. 1, 115-134 (2007).
      O. Korb, T. Stützle, T.E. Exner
      URL: http://www.tcd.uni-konstanz.de/research/plants.php

    This class is compatible with PLANTS versions 1.1 and 1.2.
    If not otherwise defined, the PLANTS executable files are available
    in the bin directory of the lie_plants_docking package suffixed by the
    OS identifier as returned by `sys.platform`.
    Support is available for all of PLANTS default configuration options
    described in sections 1.0 of the PLANTS manual.

    Run a PLANTS docking as:
    ::
        docking = PlantsDocking(plants_config_dict)
        docking.run(protein, ligand)
        results_json = docking.results()

    :param user_meta:   user information included in Twisted based structured
                        log messages.
    :type user_meta:    dict
    :param kwargs:      additional keyword arguments are considered as
                        PLANTS configuration options
    :type kwargs:       dict
    """

    allowed_config_options = settings
    logging = Logger()

    def __init__(self, user_meta={}, **kwargs):

        self.user_meta = user_meta

        self._config = kwargs
        self._workdir = None

    def results(self):
        """
        Return PLANTS results

        PLANTS general docking results are stored in the features.csv
        and ranking.csv Comma Seperated Value files.
        Ranking is a subset of features. The latter contains additional
        scoring function specific data and is parsed in favour of the
        first.

        Results are parsed into a dictionary with the docking pose
        identifier as key. These identifiers are already sorted by
        PLANTS docking score.

        :return: general PLANTS docking results
        :rtype:  dict
        """

        # Read docking results: first try features.csv, else ranking.csv
        results = {}
        for resultcsv in ('features.csv', 'ranking.csv'):
            resultcsv = os.path.join(self._workdir, resultcsv)
            if os.path.isfile(resultcsv):

                with open(resultcsv, 'r') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for i, row in enumerate(reader):
                        mol2 = row.get('TOTAL_SCORE', i)
                        results[mol2] = row
                        results[mol2]['path'] = os.path.join(
                            self._workdir, '{0}.mol2'.format(mol2))
                break

        # Run a clustering
        structures = [mol2.get('path') for mol2 in results.values()]
        self.logging.info("STRUCTURES: ".format(structures))
        xyz = coords_from_mol2(structures)
        c = ClusterStructures(xyz, labels=results.keys())
        clusters = c.cluster(self._config.get('min_rmsd_tolerance', 4.0),
                             min_cluster_count=self._config.get('min_cluster_size', 2))

        for structure, res in clusters.items():
            results[structure].update(res)

        # Plot cluster results
        c.plot(to_file=os.path.join(self._workdir, 'cluster_dendrogram.pdf'))

        return results

    def format_config_file(self):
        """
        Format configuration as PLANTS *.conf file format

        The PLANTS_CONF_FILE_TEMPLATE serves as a template where
        option values are replaced by format placeholders with the
        same name as the keys in the configuration dictionary.

        Consistency of the configuration options is checked before
        configuration file creation to ensure that all required
        options are available. If options are missing from the
        configuration dictionary they will be added with default
        values.

        :return: PLANTS configuration file
        :rtype:  str
        """

        for key, value in self.allowed_config_options.items():
            if key not in self._config:
                self._config[key] = value
                self.logging.warn('Required "{0}" configuration option not defined. Add with default option {1}'.format(key, value), **self.user_meta)

        confstring = PLANTS_CONF_FILE_TEMPLATE.format(**self._config)
        return confstring

    def run(self, protein, ligand, mode='screen'):
        """
        Run a PLANTS docking for a given protein and ligand in mol2
        format in either 'screen' or 'rescore' mode.

        A docking run requires the following PLANTS configuration arguments
        to be defined:
        * exec_path: path to the PLANTS executable
        * workdir: a working directory to write docking results to
        * bindingsite_center: target ligand binding site in the protein defined
          as a 3D coordinate
        The `run` function will exit if any of these requirements are not
        resolved.

        :param protein: protein 3D structure in mol2 format
        :type protein:  str
        :param ligand:  ligand 3D structure in mol2 format
        :type ligand:   str
        :param mode:    PLANTS execution mode as either virtual
                        screening 'screen' or rescoring 'rescore'
        :type mode:     str

        :return:        boolean to indicate successful docking
        :rtype:         bool
        """

        # Check required PLANTS configuration arguments
        self._workdir = self._config.get('workdir', None)
        if self._workdir:
            self._workdir = os.path.abspath(self._workdir)
            if not os.path.exists(self._workdir):
                self.logging.error('Working directory {0} does not exist'.format(self._workdir), **self.user_meta)
                return False
            if not os.access(self._workdir, os.W_OK):
                self.logging.error('Working directory {0} not writable'.format(self._workdir), **self.user_meta)
                return False
        else:
            self.logging.error('Working directory not defined (workdir parameter)', **self.user_meta)
            return False

        exec_path = self._config.get('exec_path')
        if not os.path.exists(exec_path):
            self.logging.error('Plants executable not available at: {0}'.format(exec_path), **self.user_meta)
            return False
        if not os.access(exec_path, os.X_OK):
            self.logging.error('Plants executable {0} does not have exacutable permissions'.format(exec_path), **self.user_meta)
            return False

        if not self._config.get('bindingsite_center'):
            self.logging.error('Binding site center not defined', **self.user_meta)
            return False
        if sum(self._config.get('bindingsite_center')) == 0 or len(self._config.get('bindingsite_center')) != 3:
            self.logging.error('Malformed binding site center definition: {0}'.format(self._config.get('bindingsite_center')), **self.user_meta)
            return False

        # Copy files to working directory
        if os.path.isfile(protein):
            self._config['protein_file'] = protein
        else:
            with open(os.path.join(self._workdir, 'protein.mol2'), 'w') as protein_file:
                protein_file.write(protein)
                self._config['protein_file'] = 'protein.mol2'

        with open(os.path.join(self._workdir, 'ligand.mol2'), 'w') as ligand_file:
            ligand_file.write(ligand)
            self._config['ligand_file'] = 'ligand.mol2'

        # Write PLANTS configuration file
        conf_file = os.path.join(self._workdir, 'plants.config')
        with open(conf_file, 'w') as conf:
            conf.write(self.format_config_file())

        cmd = [exec_path, '--mode', mode, 'plants.config']
        self.logging.info(
            "Running plants_docking command:\n{}".format(' '.join(cmd)))
        output, error = cmd_runner(cmd, self._workdir)

        return True
