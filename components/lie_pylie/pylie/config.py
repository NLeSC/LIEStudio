# -*- coding: utf-8 -*-

import copy
import logging
import json

from .methods.fileio import _open_anything

logger = logging.getLogger('pylie')


class ConfigHandler(object):

    def __init__(self, config, instance=None):

        self._config = config
        self._instance = instance

        self._defaults = copy.copy(config)
        self._persist = {}
        self._initialised = True

    def __call__(self):

        return self._config

    def __repr__(self):

        return "<Configuration object {0} for instances: {1}>".format(id(self), ', '.join(self._instance))

    def __str__(self):
        """
        __str__ overload.

        Print friendly overview of settings
        """

        overview = []
        for k in sorted(self._config.keys()):
            overview.append('{0}: {1}\n'.format(k, self._config[k]))

        return ''.join(overview)

    def __getitem__(self, key):
        """
        __getitem__ overload.

        Get self._config values using dictionary style access, fallback to
        default __getitem__

        :param key: attribute name
        :type key:  :py:str

        :return: attribute
        """

        if key in self._config:
            return self._get(key)
        return self.__dict__[key]

    def __getattr__(self, key):
        """
        __getattr__ overload.

        Expose self._config dictionary keys as class attributes.
        fallback to the default __getattr__ behaviour.

        :param key: attribute name
        :type key:  :py:str

        :return:    attribute
        """

        if key in self._config:
            return self._get(key)
        return object.__getattr__(self, key)

    def __setattr__(self, key, value):
        """
        __setattr__ overload.

        Set self._config dictionary entries using class attribute setter methods
        fallback to the default __setattr__ behaviour.

        :param key:   attribute name.
        :type key:    :py:str

        :param value: attribute value
        """

        if '_initialised' not in self.__dict__:
            return dict.__setattr__(self, key, value)
        elif key in self._config:
            self._set(key, value)
        else:
            self.__setitem__(key, value)

    def __setitem__(self, key, value):
        """
        __setitem__ overload.

        Set self._config values using dictionary style access, fallback to
        default __setattr__

        :param key:   attribute name
        :type:        :py:str
        :param value: attribute value
        """

        if key in self._config:
            self._set(key, value)
        else:
            dict.__setattr__(self, key, value)

    def _get(self, key, default=None):
        persist_count = self._persist.get(key, None)
        if persist_count is not None:
            if persist_count > 0:
                self._persist[key] = self._persist[key] - 1
            else:
                del self._persist[key]
                self.revert(key)

        return self._config.get(key, default)

    def _set(self, key, value, strict=False):
        if key not in self._config and strict:
            raise KeyError('No key named "{0}" in configuration {1}'.format(key, ', '.join(self._instance)))

        self._config[key] = value

    def get(self, key, default=None):
        return self._get(key, default)

    def set(self, key, value, persist=0):
        self._set(key, value)
        if persist > 0:
            self._persist[key] = persist

    def items(self):

        return self._config.items()

    def default(self, key):

        return self._defaults.get(key, None)

    def remove(self, key):

        if key in self._config:
            del self._config[key]

    def revert(self, key):

        self._set(key, self.default(key))

    def update(self, indict, strict=False):
        """
        Update the settings dictionary with key,value pairs from another
        dictionary. If 'strict' than raise an error if the key is not in the
        dictionary.
        """

        for key, value in indict.items():
            self._set(key, value, strict=strict)

    def dict(self):

        return self._config or {}


class MetaConfigHandler(object):
    """
    MetaConfigHandler class

    Manages settings for all module functions and classes available module wide.
    The PYLIE_MASTER_CONFIG dictionary in pylie.config serves as the default
    source of settings.
    Settings are defined in principle by the function or class name followed by
    the setting variable name, dot seperated. In practice, any string will work

    Settings for multiple classes or function can be combined in one dictionary
    but with the risk of similar named functions to be overwritten.

    The default configuration may be updated by the user from a dictionary with
    custom configuration settings.
    Functions or classes requesting configuration settings will get a copy of the
    settings from the main configuration to allow for safe overloading the settings
    for that particular instance only.
    """

    def __init__(self, config):

        self.config = config

    def get(self, instance):
        """
        Return a copy of the configuration settings for particular function(s) or
        class instance(s) as a ConfigHandler object.
        Multikey configuration keys (strings separated by multiple dots) are parsed
        into a hierarchical dictionary object

        :param instance: Function or class name(s) to return configuration for.
        :ptype instance: String or list of strings
        """

        # Cast input to list
        if isinstance(instance, str):
            instance = ['Global', instance]
        elif isinstance(instance, list):
            instance = ['Global'] + instance

        # Make (nested) dictionary
        selection = {}
        for a in instance:

            for key, value in [n for n in self.config.items() if n[0].startswith(a)]:
                split_key = key.split('.')[1:]

                container = selection
                for i, part in enumerate(split_key):
                    part = part.strip()
                    if i < len(split_key) - 1:
                        if part not in container:
                            container[part] = {}
                        container = container[part]
                    else:
                        container[part] = value

        # Return a copy of the configuration dictionary wrapped in a controller object
        return ConfigHandler(copy.deepcopy(selection), instance=instance)

    def load(self, jsonfile):
        """
        Update the default pylie configuration with a custom configuration
        dictionary loaded from a JSON file format.

        :param jsonfile: configuration file in JSON format
        """

        fileobject = _open_anything(jsonfile)
        data = json.load(fileobject)

        self.update(data)

    def update(self, configdict):
        """
        Update the default pylie configuration with a custom configuration
        dictionary. Dictionary keys are not checked to allow settings for custom
        function or class overloads.

        :param configdict: Dictionary with configuration settings.
        """

        assert isinstance(configdict, dict), TypeError("Custom configuration needs to be defined as a dictionary")
        self.config.update(configdict)
