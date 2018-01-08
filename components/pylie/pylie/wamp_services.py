# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

import os
import tempfile
import json
import jsonschema
import pickle

from pandas import read_csv, read_json, read_excel, read_table, concat, DataFrame
from autobahn import wamp

from pylie import LIEMDFrame, LIEDataFrame, pylie_config
from pylie.filters.filtersplines import FilterSplines
from pylie.filters.filtergaussian import FilterGaussian
from pylie.methods.adan import ad_residue_decomp, ad_dene, ad_dene_yrange, parse_gromacs_decomp
from lie_system import LieApplicationSession, WAMPTaskMetaData

pylie_schema = json.load(open(os.path.join(os.path.dirname(__file__), 'pylie_schema.json')))

PANDAS_IMPORTERS = {'csv': read_csv, 'json': read_json, 'xlsx': read_excel, 'tbl': read_table}
PANDAS_EXPORTERS = {'csv': 'to_csv', 'json': 'to_json', 'xlsx': 'to_excel', 'tbl': 'to_string'}


class PylieWampApi(LieApplicationSession):
    """
    Pylie WAMP methods.

    Defines `require_config` to retrieve system and database configuration
    upon WAMP session setup
    """

    require_config = ['system']

    def _get_config(self, config, name):

        ref_config = pylie_config.get(name).dict()
        ref_config.update(config)

        # Validate the configuration
        jsonschema.validate(pylie_schema, ref_config)

        return ref_config

    def _import_to_dataframe(self, infile):

        if not os.path.isfile(infile):
            self.log.error('No such file: {0}'.format(infile))
            return

        ext = infile.split('.')[-1]
        if ext not in PANDAS_IMPORTERS:
            self.log.error('Unsupported file format: {0}'.format(ext))
            return

        df = PANDAS_IMPORTERS[ext](infile)
        if 'Unnamed: 0' in df:
            del df['Unnamed: 0']

        return df

    def _export_dataframe(self, df, outfile, file_format='csv'):

        if file_format not in PANDAS_EXPORTERS:
            self.log.error('Unsupported file format: {0}'.format(file_format))
            return False

        if hasattr(df, PANDAS_EXPORTERS[file_format]):
            method = getattr(df, PANDAS_EXPORTERS[file_format])

            # Export to file
            with open(outfile, 'w') as outf:
                method(outf)

            return True
        return False

    @wamp.register(u'liestudio.pylie.liedeltag')
    def calculate_lie_deltag(self, dataframe=None, alpha=0.5, beta=0.5, gamma=0.0, kBt=2.49, session=None, **kwargs):

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        # Filter DataFrame
        dfobject = LIEDataFrame(self._import_to_dataframe(dataframe))
        dg_calc = dfobject.liedeltag(params=[alpha, beta, gamma], kBt=kBt)

        # Create workdir to save file
        workdir = os.path.join(kwargs.get('workdir', tempfile.gettempdir()))
        if not os.path.isdir(workdir):
            os.mkdir(workdir)
            self.logger.debug('Create working directory: {0}'.format(workdir), **session)

        # Save dataframe
        file_format = kwargs.get('file_format', 'csv')
        filepath = os.path.join(workdir, 'liedeltag.{0}'.format(file_format))
        if self._export_dataframe(dg_calc, filepath, file_format=file_format):
            session['status'] = 'completed'
            return {'session': session, 'liedeltag_file': filepath, 'liedeltag': dg_calc.to_dict()}

        session['status'] = 'failed'
        return {'session': session}

    @wamp.register(u'liestudio.pylie.concat_dataframes')
    def concat_dataframes(self, dataframes=None, ignore_index=True, axis=0, join='outer', session=None, **kwargs):
        """
        Combine multiple tabular DataFrames into one new DataFrame using
        the Python Pandas library.

        :param dataframes: DataFrames to combine
        :type dataframes:  :py:list
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        # Import all files
        dfs = []
        for dataframe in dataframes:
            dfobject = self._import_to_dataframe(dataframe)
            if isinstance(dfobject, DataFrame):
                dfs.append(dfobject)

        # Concatenate dataframes
        if len(dfs) > 1:
            concat_df = concat(dfs, ignore_index=ignore_index, axis=axis, join=join)
            session['status'] = 'completed'

            # Create workdir to save file
            workdir = os.path.join(kwargs.get('workdir', tempfile.gettempdir()))
            if not os.path.isdir(workdir):
                os.mkdir(workdir)
                self.logger.debug('Create working directory: {0}'.format(workdir), **session)

            file_format = kwargs.get('file_format', 'csv')
            filepath = os.path.join(workdir, 'joined.{0}'.format(file_format))
            if self._export_dataframe(concat_df, filepath, file_format=file_format):
                return {'session': session, 'concat_mdframe': filepath}

        session['status'] = 'failed'
        return {'session': session}

    @wamp.register(u'liestudio.pylie.calculate_lie_average')
    def calculate_lie_average(self, mdframe=None, session=None, **kwargs):
        """
        Calculate LIE electrostatic and Van der Waals energy averages from
        a MDFrame.

        :param mdframe: path to LIEMDFrame
        :type mdframe:  :py:str
        :param session: WAMP session information
        :type session:  :py:dict
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        # Load MDFrame import configuration and update
        filter_config = self._get_config(kwargs, 'LIEMDFrame')

        if not mdframe or not os.path.isfile(mdframe):
            self.logger.error('MDFrame csv file does not exist: {0}'.format(mdframe), **session)
            session['status'] = 'failed'
            return {'session': session}

        # Create workdir to save file
        workdir = os.path.join(kwargs.get('workdir', tempfile.gettempdir()))
        if not os.path.isdir(workdir):
            os.mkdir(workdir)
            self.logger.debug('Create working directory: {0}'.format(workdir), **session)

        # Import CSV file and run spline fitting filter
        liemdframe = LIEMDFrame(read_csv(mdframe))
        if 'Unnamed: 0' in liemdframe.columns:
            del liemdframe['Unnamed: 0']

        ave = liemdframe.inliers(method=filter_config.get('inlierFilterMethod', 'pair')).get_average()
        filepath = os.path.join(workdir, 'averaged.csv')
        ave.to_csv(filepath)

        output = {}
        session['status'] = 'completed'
        if os.path.isfile(filepath):
            output['averaged'] = filepath
        else:
            session['status'] = 'failed'

        output['session'] = session

        return output

    @wamp.register(u'liestudio.pylie.gaussian_filter')
    def filter_gaussian(self, dataframe=None, confidence=0.975, plot=True, session=None, **kwargs):
        """
        Use multivariate Gaussian Distribution analysis to filter VdW/Elec
        values
        :param dataframe: DataFrame to filter
        :type dataframe:  :pylie:LIEDataFrame
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        # Filter DataFrame
        dfobject = LIEDataFrame(self._import_to_dataframe(dataframe))
        gaussian = FilterGaussian(dfobject, confidence=confidence)
        filtered = gaussian.filter()
        self.log.info("Filter detected {0} outliers.".format(len(filtered.outliers.cases)))

        # Create workdir to save file
        workdir = os.path.join(kwargs.get('workdir', tempfile.gettempdir()))
        if not os.path.isdir(workdir):
            os.mkdir(workdir)
            self.log.debug('Create working directory: {0}'.format(workdir), **session)

        # Plot results
        if plot:
            outp = os.path.join(workdir, 'gauss_filter.pdf')
            p = gaussian.plot()
            p.savefig(outp)

        # Save filtered dataframe
        file_format = kwargs.get('file_format', 'csv')
        filepath = os.path.join(workdir, 'gauss_filter.{0}'.format(file_format))
        if self._export_dataframe(filtered, filepath, file_format=file_format):
            session['status'] = 'completed'
            return {'session': session, 'gauss_filter': filepath}

        session['status'] = 'failed'
        return {'session': session}

    @wamp.register(u'liestudio.pylie.filter_stable_trajectory')
    def filter_stable_trajectory(self, mdframe=None, session=None, **kwargs):
        """
        Use FFT and spline-based filtering to detect and extract stable regions
        in the MD energy trajectory

        :param mdframe: path to LIEMDFrame
        :type mdframe:  :py:str
        :param session: WAMP session information
        :type session:  :py:dict
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        # Load FilterSplines configuration and update
        filter_config = self._get_config(kwargs, 'FilterSplines')

        # Validate the configuration
        jsonschema.validate(pylie_schema, filter_config)

        if not mdframe or not os.path.isfile(mdframe):
            self.logger.error('MDFrame csv file does not exist: {0}'.format(mdframe), **session)
            session['status'] = 'failed'
            return {'session': session}

        # Create workdir to save file
        workdir = os.path.join(kwargs.get('workdir', tempfile.gettempdir()))
        if not os.path.isdir(workdir):
            os.mkdir(workdir)
            self.log.debug('Create working directory: {0}'.format(workdir), **session)

        # Import CSV file and run spline fitting filter
        liemdframe = LIEMDFrame(read_csv(mdframe))
        if 'Unnamed: 0' in liemdframe.columns:
            del liemdframe['Unnamed: 0']

        splines = FilterSplines(liemdframe, **filter_config)
        liemdframe = splines.filter()

        output = {}
        # Report the selected stable regions
        filtered = liemdframe.inliers()
        for pose in filtered.poses:
            stable = filtered.get_stable(pose)
            if stable:
                output['stable_pose_{0}'.format(pose)] = stable

        # Create plots
        if filter_config.get('do_plot', False):
            currpath = os.getcwd()
            os.chdir(workdir)
            splines.plot(tofile=True, filetype=filter_config.get('plotFileType', 'pdf'))
            os.chdir(currpath)

        # Filter the mdframe
        if filter_config.get('do_filter', True):
            filepath = os.path.join(workdir, 'mdframe_splinefiltered.csv')
            filtered.to_csv(filepath)

            if os.path.isfile(filepath):
                output['filtered_mdframe'] = filepath

        session['status'] = 'completed'
        output['session'] = session

        return output

    @wamp.register(u'liestudio.pylie.collect_energy_trajectories')
    def import_mdene_files(self, bound_trajectory=None, unbound_trajectory=None, session=None, **kwargs):
        """
        Import GROMACS MD trajectory energy files into a LIEMDFrame.

        The constructed LIEMDFrame should represents simulations for the same
        system with one simulation for the unbound state of the ligand and one
        or more simulations for the bound system with the ligand in potentially
        multiple binding poses.

        :param bound_trajectory: one or multiple Gromacs energy trajectory
                                 file paths for bound systems
        :param unbound_trajectory: one or multiple Gromacs energy trajectory
                                 file paths for unbound systems
        :param lie_vdw_header:   header name for VdW energies
        :type lie_vdw_header:    str
        :param lie_ele_header:   header name for coulomb energies
        :type lie_ele_header:    :py:str
        :param case:             case ID
        :type case:              :py:int
        :param session:          WAMP session information
        :type session:           :py:dict
        """

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        # Load MDFrame import configuration and update
        mdframe_config = self._get_config(kwargs, 'LIEMDFrame')

        # Create workdir to save file
        workdir = os.path.join(kwargs.get('workdir', tempfile.gettempdir()))
        if not os.path.isdir(workdir):
            os.mkdir(workdir)
            self.logger.debug('Create working directory: {0}'.format(workdir), **session)

        # Support multiple trajectory paths at once
        if not isinstance(bound_trajectory, list):
            bound_trajectory = [bound_trajectory]
        if not isinstance(unbound_trajectory, list):
            unbound_trajectory = [unbound_trajectory]

        # Collect trajectories
        mdframe = LIEMDFrame()
        vdw_header = mdframe_config.get('lie_vdw_header', 'vdwLIE')
        ele_header = mdframe_config.get('lie_ele_header', 'EleLIE')
        for pose, trj in enumerate(bound_trajectory):
            if not os.path.exists(trj):
                self.log.error('File does not exists: {0}'.format(trj), **session)
                continue
            mdframe.from_file(trj, {vdw_header: 'vdw_bound_{0}'.format(pose + 1),
                                    ele_header: 'coul_bound_{0}'.format(pose + 1)},
                              filetype=mdframe_config['filetype'])
            self.log.debug('Import file: {0}, pose: {1}'.format(trj, pose))

        for trj in unbound_trajectory:
            if not os.path.exists(trj):
                self.logger.error('File does not exists: {0}'.format(trj), **session)
                continue
            mdframe.from_file(trj, {vdw_header: 'vdw_unbound', ele_header: 'coul_unbound'},
                              filetype=mdframe_config['filetype'])
            self.log.debug('Import unbound file: {0}'.format(trj))

        # Set the case ID
        mdframe.case = mdframe_config.get('case', 1)

        # Store to file
        filepath = os.path.join(workdir, 'mdframe.csv')
        mdframe.to_csv(filepath)

        session['status'] = 'completed'

        return {'session': session, 'mdframe': filepath}

    @wamp.register(u'liestudio.pylie.adan_residue_decomp')
    def adan_residue_decomp(self, decomp_files=None, model_pkl=None, cases=None, session=None, **kwargs):

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        # Load the model
        if not os.path.isfile(model_pkl):
            self.log.error('eTOX model file does not exist: {0}'.format(model_pkl))
            session['status'] = 'failed'
            return {'session': session}

        model = pickle.load(open(model_pkl))

        # Parse gromacs residue decomposition energy files to DataFrame
        decomp_dfs = []
        for dcfile in decomp_files:
            decomp_dfs.append(parse_gromacs_decomp(dcfile))

        # Run AD test
        ene = ad_residue_decomp(decomp_dfs, model['AD']['decVdw'], model['AD']['decEle'], cases=cases)

        # Create workdir and save file
        workdir = os.path.join(kwargs.get('workdir', None))
        if workdir:
            if not os.path.isdir(workdir):
                os.mkdir(workdir)
                self.log.debug('Create working directory: {0}'.format(workdir), **session)
            filepath = os.path.join(workdir, 'adan_residue_decomp.csv')
            ene.to_csv(filepath)

        session['status'] = 'completed'
        return {'session': session, 'decomp': ene.to_dict()}

    @wamp.register(u'liestudio.pylie.adan_dene')
    def adan_dene(self, dataframe=None, model_pkl=None, center=None, ci_cutoff=None, session=None, **kwargs):

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        # Load the model
        if not os.path.isfile(model_pkl):
            self.log.error('eTOX model file does not exist: {0}'.format(model_pkl))
            session['status'] = 'failed'
            return {'session': session}

        model = pickle.load(open(model_pkl))

        # Parse gromacs residue decomposition energy files to DataFrame
        dfobject = self._import_to_dataframe(dataframe)

        # Run AD test
        ene = ad_dene(dfobject, model['AD']['Dene']['CovMatrix'], center=center, ci_cutoff=ci_cutoff)

        # Create workdir and save file
        workdir = os.path.join(kwargs.get('workdir', None))
        if workdir:
            if not os.path.isdir(workdir):
                os.mkdir(workdir)
                self.log.debug('Create working directory: {0}'.format(workdir), **session)
            filepath = os.path.join(workdir, 'adan_dene.csv')
            ene.to_csv(filepath)

        session['status'] = 'completed'
        return {'session': session, 'decomp': ene.to_dict()}

    @wamp.register(u'liestudio.pylie.adan_dene_yrange')
    def adan_dene_yrange(self, dataframe=None, ymin=None, ymax=None, session=None, **kwargs):

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session).dict()

        # Parse gromacs residue decomposition energy files to DataFrame
        dfobject = self._import_to_dataframe(dataframe)

        # Run AD test
        ene = ad_dene_yrange(dfobject, ymin, ymax)

        # Create workdir and save file
        workdir = os.path.join(kwargs.get('workdir', None))
        if workdir:
            if not os.path.isdir(workdir):
                os.mkdir(workdir)
                self.log.debug('Create working directory: {0}'.format(workdir), **session)
            filepath = os.path.join(workdir, 'adan_dene_yrange.csv')
            ene.to_csv(filepath)

        session['status'] = 'completed'
        return {'session': session, 'decomp': ene.to_dict()}


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
        return PylieWampApi(config)
    else:
        # if no config given, return a description of this WAMPlet ..
        return {'label': 'LIEStudio pylie management WAMPlet',
                'description': 'WAMPlet proving LIEStudio pylie management endpoints'}
