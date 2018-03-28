# -*- coding: utf-8 -*-

"""
Base class for docking
"""

import os
import shutil


class DockingBase(object):

    method = 'docking_base'

    def __setitem__(self, key, value):
        """
        __setitem__ overload.

        Set values using dictionary style access, fallback to
        default __setattr__

        :param key:   attribute name
        :type key:    str
        :param value: attribute value
        """

        if key in self._config or key in self.allowed_config_options:
            self._config[key] = value
        else:
            dict.__setattr__(self, key, value)

    def update(self, config):
        """
        Update the configuration settings for the docking method from a
        dictionary of custom settings.

        Configuration options (keys) are validated against the set of
        allowed (known) option names for the docking method.

        :param config: custom settings
        :type config:  :py:class:`dict`
        """

        for key, value in config.items():
            if key in self.allowed_config_options:
                self._config[key] = value
            else:
                self.logging.warn('{0} configuration file has no setting named: {0}'.format(self.method, key), **self.user_meta)
        self.logging.info('Override {0} configuration for options: {1}'.format(self.method, ', '.join(config.keys())), **self.user_meta)

    def delete(self):
        """
        Delete the working directory
        """

        if os.path.isdir(self._workdir):
            try:
                shutil.rmtree(self._workdir)
            except Exception as e:
                self.logging.warn('Unable to remove working directory: {0}, with error: {1}'.format(self._workdir, e), **self.user_meta)
        else:
            self.logging.warn('working directory {0} does not exist'.format(self._workdir), **self.user_meta)

    def clean(self, exclude=[]):
        """
        Clean the working directory by removing all files except those in `exclude`

        :param exclude: files to preserve
        :type exlude:   :py:list
        """

        folder_content = [f for f in os.listdir(self._workdir) if f not in exclude]
        self.logging.debug('Clean {0} files in directory: {1}'.format(len(folder_content), self._workdir), **self.user_meta)

        for file_to_remove in folder_content:
            file_to_remove = os.path.join(self._workdir, file_to_remove)
            try:
                if os.path.isfile(file_to_remove):
                    os.remove(file_to_remove)
                elif os.path.isdir(file_to_remove):
                    shutil.rmtree(file_to_remove)
            except Exception as e:
                self.logging.warn('Unable to remove path: {0}, with error: {1}'.format(file_to_remove, e))
