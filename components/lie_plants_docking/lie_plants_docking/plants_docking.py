# -*- coding: utf-8 -*-

"""
Classes for protein-ligand docking using the PLANTS software:

  PLANTS: Protein-Ligand ANT System.
  "An ant colony optimization approach to flexible protein-ligand docking" Swarm Intell. 1, 115-134 (2007).
  O. Korb, T. Stützle, T.E. Exner
  URL: http://www.tcd.uni-konstanz.de/research/plants.php
"""

import logging
import os
import csv

from lie_plants_docking.docking_base import DockingBase
from lie_plants_docking.plants_conf import PLANTS_CONF_FILE_TEMPLATE
from lie_plants_docking.utils import cmd_runner
from lie_plants_docking.clustering import (coords_from_mol2, ClusterStructures)


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
    logger = logging.getLogger(__name__)

    def __init__(self, workdir=None, user_meta={}, **kwargs):

        self.user_meta = user_meta

        self.config = kwargs
        self.workdir = workdir

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
            resultcsv = os.path.join(self.workdir, resultcsv)
            if os.path.isfile(resultcsv):

                with open(resultcsv, 'r') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for i, row in enumerate(reader):
                        mol2 = row.get('TOTAL_SCORE', i)
                        results[mol2] = row
                        results[mol2]['path'] = os.path.join(
                            self.workdir, '{0}.mol2'.format(mol2))
                break

        # Run a clustering
        structures = [mol2.get('path') for mol2 in results.values()]
        xyz = coords_from_mol2(structures)
        c = ClusterStructures(xyz, labels=list(results.keys()))
        clusters = c.cluster(self.config.get('min_rmsd_tolerance', 4.0),
                             min_cluster_count=self.config.get('min_cluster_size', 2))

        for structure, res in clusters.items():
            results[structure].update(res)

        # Plot cluster results
        c.plot(to_file=os.path.join(self.workdir, 'cluster_dendrogram.pdf'))

        return results

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

        The PLANTS_CONF_FILE_TEMPLATE serves as a template where
        option values are replaced by format placeholders with the
        same name as the keys in the configuration dictionary.


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
        self.workdir = os.path.abspath(self.workdir)
        if not os.path.exists(self.workdir):
            self.logger.error('Working directory {0} does not exist'.format(self.workdir), **self.user_meta)
            return False
        if not os.access(self.workdir, os.W_OK):
            self.logger.error('Working directory {0} not writable'.format(self.workdir), **self.user_meta)
            return False

        exec_path = self.config.get('exec_path')
        if not os.path.exists(exec_path):
            self.logger.error('Plants executable not available at: {0}'.format(exec_path), **self.user_meta)
            return False
        if not os.access(exec_path, os.X_OK):
            self.logger.error('Plants executable {0} does not have exacutable permissions'.format(exec_path), **self.user_meta)
            return False

        if sum(self.config.get('bindingsite_center')) == 0 or len(self.config.get('bindingsite_center')) != 3:
            self.logger.error('Malformed binding site center definition: {0}'.format(self.config.get('bindingsite_center')), **self.user_meta)
            return False

        # Copy files to working directory
        if os.path.isfile(protein):
            self.config['protein_file'] = protein
        else:
            with open(os.path.join(self.workdir, 'protein.mol2'), 'w') as protein_file:
                protein_file.write(protein)
                self.config['protein_file'] = 'protein.mol2'

        if os.path.isfile(ligand):
            self.config['ligand_file'] = ligand
        else:
            with open(os.path.join(self.workdir, 'ligand.mol2'), 'w') as ligand_file:
                ligand_file.write(ligand)
                self.config['ligand_file'] = 'ligand.mol2'

        # Write PLANTS configuration file
        conf_file = os.path.join(self.workdir, 'plants.config')
        with open(conf_file, 'w') as conf:
            conf.write(PLANTS_CONF_FILE_TEMPLATE.format(**self.config))

        cmd = [exec_path, '--mode', mode, 'plants.config']
        self.logger.info(
            "Running plants_docking command:\n{}".format(' '.join(cmd)))
        output, error = cmd_runner(cmd, self.workdir)

        return True
