# -*- coding: utf-8 -*-

"""
file: component_manager.py

"""

import fnmatch
import imp
import os
import sys
import pkgutil

from twisted.logger import Logger


def import_error(pkg):
    print(pkg)


def read_first_line(f):
    """
    Read the path in the first link of a file
    """
    with open(f, 'r') as f:
        return f.read().split()[0]


class ComponentManager(object):
    """
    LIEStudio application component manager

    :param config: component settings required for initiation
                   and exit routines
    :type config:  :py:class:`dict` or :lie_system:ConfigHandler instance
    :param prefix: prefix to add to component names on import to
                   avoid namespace collision
    :type prefix:  str
    """

    logging = Logger()

    def __init__(self, config={}, prefix=''):

        self.prefix = prefix
        self.shutdown_order = []

        self._config = config
        self._components = {}
        self._searchpath = []

    def __getattr__(self, component):

        return self.get_component(component)

    def __iter__(self):

        for component in self.components:
            yield (self.get_component(component))

    def _list_components(self, source, recursive=False):

        components = {}

        if recursive:
            for importer, name, isPkg in pkgutil.walk_packages(
                    [source], onerror=import_error):
                if isPkg:
                    components[name] = os.path.join(source, name)
        else:
            for importer, name, isPkg in pkgutil.iter_modules([source]):
                if isPkg:
                    components[name] = os.path.join(source, name)

        # Add egg-link components
        links = self._search_for_symbolic_links(source)

        return self._update_components(components, links)

    def _update_components(self, components, links):
        """
        add symbolic egg-links to the components
        """
        if links is None:
            return components
        else:
            components.update(links)
            return components

    def _search_for_symbolic_links(self, path):
        """
        Look for egg-link files and return a dictionary
        of names and paths
        """
        files = fnmatch.filter(os.listdir(path), '*egg-link')
        if not files:
            return None
        else:
            paths = [read_first_line(os.path.join(path, f)) for f in files]
            names = [p.split('/')[-1] for p in paths]

        return {n: p for n, p in zip(names, paths)}

    def add_searchpath(
            self, searchpath, prefix=None, search_method=lambda self,
            searchpath: self._list_components(searchpath)):
        """
        Add a component search path to the manager

        Add all Python modules (packages), or optionally those
        starting with `prefix` in the specified search path to
        the ComponentManager

        :param search_method: callback that list directories with components
        :type  search_method: lambda
        :param searchpath: path to component directory
        :type searchpath:  string
        :param prefix:     component name prefix to filter on
        :type prefix:      string
        """

        if not os.path.exists(searchpath):
            self.logging.error(
                'LIE component searchpath does not exist: {0}'.format(
                    searchpath))

        components = search_method(self, searchpath)
        if prefix:
            components = {
                k: v for k, v in components.items() if k.startswith(prefix)}

        if not components:
            self.logging.info(
                'No components found in path: {0} (prefix: {1})'.format(
                    searchpath, prefix or ''))

        self._components.update(components)
        self.logging.debug(
            "Added {0} components from search path: {1}".format(
                len(components), searchpath))

        # Add component directory to sys.path and self._searchpath
        if searchpath not in self._searchpath:
            self._searchpath.append(searchpath)
        if searchpath not in sys.path:
            sys.path.append(searchpath)

    def component_settings(self, components=None):
        """
        Load component settings

        Components may expose public settings as Python dictionary
        using the `settings` attribute in the module __init__.py file

        This fuctions queries all the components managed by the
        ComponentManager or a subset provided by the `components`
        attribute for public settings and will try to retrieve them.

        :param components: components to retrieve public settings for.
        :type components:  list of strings
        :rtype:            :py:class:`dict`
        """

        if components:
            assert isinstance(components, (tuple, list)), 'Components needs to be a tuple or list'
            components = [c for c in components if c in self._components]
        else:
            components = self._components.keys()

        settings_dict = {}
        for component in components:
            if hasattr(self.get_component(component), 'settings'):
                settings = self.get_component(component).settings
                settings_dict[component] = settings
                self.logging.debug(
                    'Load default settings from {0} component'.format(
                        component))

        return settings_dict

    def get_component(self, component, do_reload=False):
        """
        Load module by name

        By default the module is not reloaded if already loaded
        unless `do_reload` equals true.
        """
        if component in self._components:
            path, name = os.path.split(self._components[component])
            component_name = '{0}{1}'.format(self.prefix, name)
            if component_name in sys.modules and not do_reload:
                return sys.modules[component_name]

            # try:
            mfile, filename, data = imp.find_module(
                component, [path, os.path.join(path, component)])
            # except ImportError:
            #    mfile, filename, data = imp.find_module(component_name, [path])

            mod = imp.load_module(component_name, mfile, filename, data)
            return mod

    def bootstrap(self, components=None, order=[]):
        """
        Bootstrap components by calling their `oninit` function

        :param components: components to bootstrap. Defaults to all components
                           managed by the ComponentManager.
        :type components:  list of strings
        :param order:      bootstrap order
        :type order:       list of strings
        """

        if components:
            assert isinstance(components, (tuple, list)), 'Components needs to be of type tuple or list'
            components = [c for c in components if c in self._components]
        else:
            components = self._components.keys()

        if len(order):
            order = [c for c in order if c in components]
            order.extend([c for c in components if c not in order])
            components = order

        init_count = 1
        for component in components:
            if hasattr(self.get_component(component), 'oninit'):
                oninit = self.get_component(component).oninit
                if oninit:
                    self.logging.debug(
                        'Bootstrap component {0}'.format(component))
                    if oninit.func_code.co_argcount == 1:
                        oninit(self._config[component])
                    else:
                        oninit(self._config[component], self._config)

                    init_count += 1

        self.logging.debug(
            'Run bootstrap for {0} components. ({1} checked)'.format(
                init_count, len(components)))

    def shutdown(self, components=None, order=[]):
        """
        Shutdown components by calling their `onexit` function

        :param components: components to shutdown. Defaults to all components
                           managed by the ComponentManager.
        :type components:  list of strings
        :param order:      shutdown order
        :type order:       list of strings
        """

        if components:
            assert isinstance(components, (tuple, list)), 'Components needs to be of type tuple or list'
            components = [c for c in components if c in self._components]
        else:
            components = self._components.keys()

        if not len(order):
            order = self.shutdown_order

        if len(order):
            order = [c for c in order if c in components]
            order = [c for c in components if c not in order] + order
            components = order

        self.logging.debug(
            'Application shutdown procedure for {0} components'.format(
                len(components)))
        for component in components:
            if hasattr(self.get_component(component), 'onexit'):
                onexit = self.get_component(component).onexit
                if onexit:
                    self.logging.debug(
                        'Shutdown component {0}'.format(component))
                    onexit(self._config[component])
