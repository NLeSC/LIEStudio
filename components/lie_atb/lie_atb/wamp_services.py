# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

import os
import sys
import json
import re

from autobahn import wamp

from lie_system import LieApplicationSession, WAMPTaskMetaData
from lie_atb import ATBServerApi, ATB_Mol
from lie_atb.settings import *

if sys.version_info.major == 3:
    from urllib.error import HTTPError, URLError
else:
    from urllib2 import HTTPError, URLError


class ATBWampApi(LieApplicationSession):
    """
    Automated Topology Builder API WAMP methods.
    """

    def _parse_server_error(self, error):
        """
        Parse ATB server JSON error construct
        """

        error_dict = {}
        if hasattr(error, 'read'):
            try:
                error_dict = json.load(error)
                self.logger.error('ATB server error: {0}'.format(error_dict.get('error_msg')))
            except Exception:
                self.logger.error('Unknown ATB server error')

        return error_dict

    def _exceute_api_call(self, call, **kwargs):
        """
        Execute ATB server API call
        """

        try:
            return call(**kwargs)
        except URLError, error:
            self.logger.error('ATB server URL {0} not known/reachable'.format(self.package_config.atb_url))
            return self._parse_server_error(error)
        except HTTPError, error:
            return self._parse_server_error(error)

    def _init_atb_api(self, api_token=None):
        """
        Start ATB server API interface.

        The ATB API is initiated at every WAMP method request using a global
        or user specific ATB API token.

        :param api_token: valid ATB server API token
        :type api_token:  :py:str

        :rtype:           ATBServerApi object
        """

        if not api_token:
            self.logger.error('Using the ATB server requires a valid API token')
            return None

        api = ATBServerApi(api_token=api_token,
                           timeout=self.package_config.atb_api_timeout,
                           debug=self.package_config.atb_api_debug,
                           host=self.package_config.atb_url)
        api.API_FORMAT = u'json'
        return api

    @wamp.register(u'liestudio.atb.submit')
    def atb_submit_calculation(self, pdb=None, isfile=True, netcharge=0, moltype='heteromolecule', public=True,
                               session=None, **kwargs):
        """
        Submit a new calculation to the ATB server

        :param pdb:       structure of the molecule in PDB format
        :type pdb:        :py:str
        :param netcharge: charge of the molecule
        :type netcharge:  :py:int
        :param moltype:   the type of molecule. Any in heteromolecule,
                          amino acid, nucleic acid, sugar, lipid, solvent.
        :type moltype     :py:str
        :param public:    either true or false, depending on whether of not
                          you want the submitted molecule to be made public.
        :type public:     bool
        :param session:   WAMP session dict.
        :type session:    :py:dict
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        # Init ATBServerApi
        api = self._init_atb_api(api_token=self.package_config.atb_api_token)
        if not api:
            self.logger.error('Unable to use the ATB API', **session)
            session['status'] = 'failed'
            return {'session': session}

        # Open file if needed
        if isfile and os.path.isfile(pdb):
            pdb = open(pdb, 'r').read()

        response = self._exceute_api_call(api.Molecules.submit, pdb=pdb, netcharge=netcharge, moltype=moltype,
                                          public=public)
        if response and response.get(u'status', None) == u'error':

            # Check if molecule has been calculated already
            if response.get(u'error_msg', '').startswith('Your submission matched a previously'):
                # Extract molid from response
                m = re.search('(?<=molid=)[0-9]*', response.get(u'error_msg', ''))
                molid = None
                if m:
                    molid = m.group()
                    if molid.isdigit():
                        molid = int(molid)

                # Get the molecule data for molid
                response = [self._exceute_api_call(api.Molecules.molid, molid=molid)]
                session['status'] = 'completed'
                return {'session': session, 'result': [mol.moldict for mol in response if isinstance(mol, ATB_Mol)]}

        return session

    @wamp.register(u'liestudio.atb.get_structure')
    def atb_structure_download(self, molid=None, ffversion='54A7', fformat='pdb_allatom_optimised', atb_hash='HEAD',
                               session=None, **kwargs):
        """
        Retrieve a structure file from the ATB server by molid

        Supports download of structures in the following file formats:
        - pqr_allatom_optimised:    APBS pqr format
        - pqr_allatom_unoptimised:  APBS pqr format
        - pqr_uniatom_optimised:    APBS pqr format
        - pqr_uniatom_unoptimised:  APBS pqr format
        - pdb_allatom_optimised:    PDB format
        - pdb_allatom_unoptimised:  PDB format
        - pdb_uniatom_optimised:    PDB format
        - pdb_uniatom_unoptimised:  PDB format
        - cif_allatom:              CIF format
        - cif_allatom_extended:     CIF format
        - cif_uniatom:              CIF format
        - cif_uniatom_extended:     CIF format

        :param molid:     ATB server molid
        :type molid:      int
        :param ffversion: ATB supported force field version
        :type ffversion:  :py:str
        :param fformat:   ATB supported file format
        :param session:   WAMP session dict.
        :type session:    :py:dict
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        if ffversion not in self.package_config.atb_forcefield_version:
            self.logger.error('Forcefield version {0} not supported. Choose from {1}'.format(ffversion,
                self.package_config.atb_forcefield_version), **session)
            session['status'] = 'failed'
            return {'session': session}

        if fformat not in SUPPORTED_STRUCTURE_FILE_FORMATS:
            self.logger.error('Structure format {0} not supported'.format(fformat), **session)
            session['status'] = 'failed'
            return {'session': session}

        # Init ATBServerApi
        api = self._init_atb_api(api_token=self.package_config.atb_api_token)
        if not api:
            self.logger.error('Unable to use the ATB API', **session)
            session['status'] = 'failed'
            return {'session': session}

        # Get the molecule by molid
        molecule = self._exceute_api_call(api.Molecules.molid, molid=molid)
        filename = None
        if 'workdir' in kwargs:
            filename = os.path.join(kwargs['workdir'], '{0}.{1}'.format(fformat, SUPPORTED_FILE_EXTENTIONS.get(fformat, 'txt')))

        if molecule and isinstance(molecule, ATB_Mol):
            structure = self._exceute_api_call(molecule.download_file, file=fformat,
                                               outputType=SUPPORTED_STRUCTURE_FILE_FORMATS.get(fformat, 'cry'),
                                               ffVersion=ffversion, hash=atb_hash, fnme=filename)
            session['status'] = 'completed'
            return {'session': session, 'result': structure}
        else:
            self.logger.error('Unable to retrieve structure file for molid: {0}'.format(molid), **session)
            session['status'] = 'failed'
            return {'session': session}

    @wamp.register(u'liestudio.atb.get_topology')
    def atb_topology_download(self, molid=None, ffversion='54A7', fformat='rtp_allatom', atb_hash='HEAD',
                              session=None, **kwargs):
        """
        Retrieve a topology and parameter files from the ATB server by molid

        Supports download of structures in the following file formats:
        - lammps_allatom_optimised:     LAMMPS MD
        - lammps_allatom_unoptimised:   LAMMPS MD
        - lammps_uniatom_optimised:     LAMMPS MD
        - lammps_uniatom_unoptimised:   LAMMPS MD
        - mtb96_allatom:                GROMOS96
        - mtb96_uniatom:                GROMOS96
        - mtb_allatom:                  GROMOS11
        - mtb_uniatom:                  GROMOS11
        - rtp_allatom:                  GROMACS
        - rtp_uniatom:                  GROMACS
        - cns_allatom_top:              CNS
        - cns_allatom_param:            CNS
        - cns_uniatom_top:              CNS
        - cns_uniatom_param:            CNS

        :param molid:       ATB server molid
        :type molid:        int
        :param ffversion:   ATB supported force field version
        :type ffversion:    :py:str
        :param fformat:     ATB supported file format
        :type fformat:      :py:str
        :param session:     WAMP session dict.
        :type session:      :py:dict
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        if ffversion not in self.package_config.atb_forcefield_version:
            self.logger.error('Forcefield version {0} not supported. Choose from {1}'.format(ffversion,
                self.package_config.atb_forcefield_version), **session)
            session['status'] = 'failed'
            return {'session': session}
        
        if fformat not in SUPPORTED_TOPOLOGY_FILE_FORMATS:
            self.logger.error('Structure format {0} not supported'.format(fformat), **session)
            session['status'] = 'failed'
            return {'session': session}

        # Init ATBServerApi
        api = self._init_atb_api(api_token=self.package_config.atb_api_token)
        if not api:
            self.logger.error('Unable to use the ATB API', **session)
            session['status'] = 'failed'
            return {'session': session}

        # Get the molecule by molid
        molecule = self._exceute_api_call(api.Molecules.molid, molid=molid)
        filename = None
        if 'workdir' in kwargs:
            filename = os.path.join(kwargs['workdir'], '{0}.{1}'.format(fformat,
                                                                        SUPPORTED_FILE_EXTENTIONS.get(fformat, 'top')))

        if molecule and isinstance(molecule, ATB_Mol):
            structure = self._exceute_api_call(molecule.download_file, file=SUPPORTED_TOPOLOGY_FILE_FORMATS[fformat],
                outputType='top', ffVersion=ffversion, hash=atb_hash, fnme=filename)
            session['status'] = 'completed'
            return {'session': session, 'result': structure}
        else:
            self.logger.error('Unable to retrieve topology/prameter file for molid: {0}'.format(molid), **session)
            session['status'] = 'failed'
            return {'session': session}

    @wamp.register(u'liestudio.atb.structure_query')
    def atb_structure_query(self, mol=None, isfile=True, structure_format='pdb', netcharge='*', session=None, **kwargs):
        """
        Query the ATB server database for molecules based on a structure

        16-11-2017: Method only works with HTTP GET

        :param mol:              the structure to search for
        :type mol:               :py:str
        :param structure_format: the file format for the uploaded structure.
                                 supported types: pdb, mol, mol2, sdf, inchi
        :type structure_format:  :py:str
        :param netcharge:        the net charge of the query molecule ranging
                                 from -5 to 5 or * if unknown.
        :type netcharge:         :py:int
        :param session:          WAMP session dict.
        :type session:           :py:dict
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        if structure_format not in ('pdb', 'mol', 'mol2', 'sdf', 'inchi'):
            self.logger.error('Unsupported structure format for ATB structure based search: {0}'.format(
                structure_format), **session)
            session['status'] = 'failed'
            return {'session': session}

        # Open file if needed
        if isfile and os.path.isfile(mol):
            mol = open(mol, 'r').read()

        # Init ATBServerApi
        api = self._init_atb_api(api_token=self.package_config.atb_api_token)
        if not api:
            self.logger.error('Unable to use the ATB API', **session)
            session['status'] = 'failed'
            return {'session': session}

        result = self._exceute_api_call(api.Molecules.structure_search, structure_format=structure_format,
            structure=mol, netcharge=netcharge, method=u'GET')

        output = {}
        session['status'] = 'completed'
        output['session'] = session
        output['matches'] = result.get('matches', [])
        if 'search_molecule' in result:
            for key in ('inchi', 'inchi_key'):
                output['search_{0}'.format(key)] = result['search_molecule'][key]

        return output

    @wamp.register(u'liestudio.atb.molecule_query')
    def atb_molecule_query(self, session=None, **kwargs):
        """
        Query the ATB server database for molecules based on molecule meta-data

        The ATB server molecules database can be queried using the
        ./api/v0.1/molecules/search.py endpoint using any of the following query
        attributes or 'any' for a whildcard search. Multiple query attributes
        will be chained using the AND logical operator.

        iupac:              the official IUPAC name of the  molecule (str)
        inchi_key:          the unique InChI code of the molecule (str)
        smiles:             canonical SMILES of the molecule (str)
        common_name:        the common name of the molecule (str)
        formula:            the molecular formula (e.a. C2H6O) (str)
        maximum_qm_level:   string of comma seperated integers.
        curation_trust:     level of expected accuracy of the molecule parameters
                            as string of comma seperated integers. 0 by default:
                            -1 = unfinished ATB molecule
                             0 = finished ATB molecule
                             1 = manual parameters from reliable users
                             2 = manual parameters from official source
        is_finished:        are calculations for the molecule still running
        user_label:         any user specific label that may have been given to
                            the molecule.
        is_finished:        query for finished molecules only
        max_atoms:          maximum number of atoms (int)
        min_atoms:          minimum number of atoms (int)
        has_pdb_hetId:      molecule has PDB heteroatom ID (bool)
        match_partial:      enable partial matching of string attributes (bool)
                            False by default.

        Query values are case insensitive but the attributes (keys) are.

        :param kwargs:  any of the accepted query key,value pairs.
        :param session: WAMP session dict.
        :type session:  :py:dict
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()
        
        # Only a subset of the keys in a ATB molecule record are queryable.
        # Do not continue in case of unsupported keys.
        not_supported = [n for n in kwargs if n.lower() not in ALLOWED_QUERY_KEYS]
        if not_supported:
            self.logger.error('Following ATB molecule search query attributes not allowed: {0}'.format(
                ','.join(not_supported)), **session)
            session['status'] = 'failed'
            return {'session': session}

        # Init ATBServerApi
        api = self._init_atb_api(api_token=self.package_config.atb_api_token)
        if not api:
            self.logger.error('Unable to use the ATB API', **session)
            session['status'] = 'failed'
            return {'session': session}

        # Get molecule directly using ATB molid
        if 'molid' in kwargs:
            response = [self._exceute_api_call(api.Molecules.molid, molid=kwargs['molid'])]
        else:
            # Execute ATB molecule search query
            response = self._exceute_api_call(api.Molecules.search, **kwargs)

        if isinstance(response, list):
            if not len(response):
                self.logger.info('ATB molecule query did not yield any results', **session)
            session['status'] = 'completed'
            return {'session': session, 'result': [mol.moldict for mol in response if isinstance(mol, ATB_Mol)]}
        else:
            self.logger.error('Unable to execute ATB molecule query', **session)
            session['status'] = 'failed'
            return {'session': session}


def make(config):
    """
    Component factory

    This component factory creates instances of the application component
    to run.

    The function will get called either during development using an
    ApplicationRunner, or as a plugin hosted in a WAMPlet container such as
    a Crossbar.io worker.
    The LieApplicationSession class is initiated with an instance of the
    ComponentConfig class by default but any class specific keyword arguments
    can be consument as well to populate the class session_config and
    package_config dictionaries.

    :param config: Autobahn ComponentConfig object
    """

    if config:
        return ATBWampApi(config, package_config=SETTINGS)
    else:
        # if no config given, return a description of this WAMPlet ..
        return {'label': 'LIEStudio ATB interface WAMPlet',
                'description': 'WAMPlet providing LIEStudio connectivity to the ATB server'}
