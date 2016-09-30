# -*- coding: utf-8 -*-

"""
Main application bootstrapping
"""

import os
import sys
import json
import atexit
import shutil

try:
  import _preamble
except ImportError:
  try:
    sys.exc_clear()
  except AttributeError:
    # exc_clear() (and the requirement for it) has been removed from Py3
    pass

# Package info
__module__    = 'liestudio'
__docformat__ = 'restructuredtext'
__version__   = '{major:d}.{minor:d}.{micro:d}'.format(major=0, minor=1, micro=0)
__author__    = 'Marc van Dijk'
__status__    = 'pre-release beta1'
__date__      = '19 april 2016'
__copyright__ = 'Copyright (c) 2016, VU University, Amsterdam, the Netherlands'
__rootpath__  = os.path.dirname(os.path.abspath(__file__))
__pyv__       = sys.version_info[0:2]

# Check if Python virtual environment is in sys.path
venvpath = os.path.join(__rootpath__, 'lie_venv/lib/python{0}.{1}/site-packages'.format(*__pyv__))
if venvpath not in sys.path:
    raise Exception('Python virtual environment not active')

# Import required system packages
from  lie_system     import ComponentManager
from  lie_config     import get_config
from  twisted.logger import Logger

logging = Logger()

def _format_crossbar_cliargs(args):
    """
    Format crossbar configuration to a sys.argv list of command line arguments
    that can be parsed by the crossbar cli argparser.
    
    :param args: crossbar configuration to format
    :type args:  ConfigHandler instance
    :rtype:      list
    """
    
    options = []
    commands = {}
    for key,value in args.items():
        
        key_split = key.split('.')
        
        # Only accept one or two argument commands
        if len(key_split) == 1:
            if isinstance(value, bool) and value:
                options.extend(['--{0}'.format(key_split[0])])
            else:    
                options.extend(['--{0}'.format(key_split[0]), value])
        elif len(key_split) == 2:
            if not key_split[0] in commands:
                commands[key_split[0]] = []
            if isinstance(value, bool) and value:
                commands[key_split[0]].append(['--{0}'.format(key_split[1])])
            else:    
                commands[key_split[0]].append(['--{0}'.format(key_split[1]), value])
        else:
            logging.warn('Invalid crossbar CLI settings: {0} = {1}'.format(key,value))
        
    for command, args in commands.items():
        options.append(command)
        for arg in args:
            options.extend(arg)
    
    return options

def bootstrap_app(args):
    
    # If custom configuration file does not exists, exit.
    app_settings = os.path.join(__rootpath__, 'data/settings.json')
    if not os.path.isfile(args.config) and args.config != app_settings:
        raise IOError('No custom application configuration file at: {0}'.format(args.config))

    # If no application settings.json file, copy default settings file.
    elif not os.path.isfile(args.config):
        
        # copy base settings file
        default_config_file = os.path.join(__rootpath__, 'data/settings_default.json')
        if os.path.isfile(default_config_file):
            shutil.copyfile(default_config_file, app_settings)
            args.config = app_settings
            logging.debug('Init default application configuration file at: {0}'.format(args.config))
        else:
            raise IOError('No application configuration file at: {0}'.format(args.config))

    # Parse JSON settings file and init global ConfigHandler
    config = get_config()
    with open(args.config) as settingsfile:
        settings = json.loads(settingsfile.read())
        config.load(settings)

    # Update some global configuration settings
    config['system.app_path'] = __rootpath__
    config['lie_logger.global_log_level'] = args.loglevel

    # Initiate ComponentManager with component search paths
    # Only load modules with prefix 'lie_' from virtual environment site-packages 
    components = ComponentManager(config=config)
    components.add_searchpath(venvpath, prefix='lie_')  
    for path in config.system.get('component_path',[]):
        components.add_searchpath(path)

    # Update application configuration with component settings
    # not yet defined.
    default_component_settings = components.component_settings()
    for component in default_component_settings:
        if not component in config:
            config.update({component: default_component_settings[component]})

    # Bootstrap components  
    components.bootstrap(order=config.system.bootstrap_order)
    components.shutdown_order = config.system.shutdown_order

    # Register component shutdown procedures with the atexit module
    atexit.register(components.shutdown)
    
    # format crossbar configuration to a sys.argv list that can be
    # parsed by the crossbar cli argparser.
    crossbar_cliargs = _format_crossbar_cliargs(config.crossbar)
    
    # Import crossbar and start main event loop
    from crossbar.controller.cli import run
    run(prog='crossbar', args=crossbar_cliargs)


if __name__ == '__main__':
  
    # Launch app from command line.
    # Parse CLI arguments and bootstrap app
    from cli import lie_cli

    bootstrap_app(lie_cli(__rootpath__))
