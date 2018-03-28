# -*- coding: utf-8 -*-

import sys
import os
import collections
import unicodedata
import locale
import logging

from .. import __version__

if sys.version_info[0] < 3:
    import StringIO
    import urlparse
    import urllib2 as urllib
else:
    from io import StringIO
    from urllib import parse as urlparse


def initial_node(nodes):
    """
    Return node ID of node with smallest _ID identifier.

    :param nodes: graph 'nodes' object

    :return:      node ID
    """

    minid = min([n['_id'] for n in nodes.values()])
    for node, attr in nodes.items():
        if attr['_id'] == minid:
            return node


def resolve_root_node(graph):
    """
    Resolve the node ID of the root node of the graph.

    For Graph objects there is no strict concept of a root node and by default
    the 'root' attribute of the grpah is not defined. Here, the root will
    resolve to the node nid with the smallest _id number which usually is the
    first node added when the graph was created.

    For GraphAxis object a root is essential for defining the graph hierarchy
    and thus, the graph 'root' attribute should be defined. If it is not
    defined it will also default to the node nid with the smallest _id number.
    If the user defined or default root is in the (sub)graph it is returned.
    If not, an attempt will be made to resolve it following:

    * If the graph is a single node, its node ID will be root.
    * If the graph has multiple nodes and the root is defined in the full_graph,
      return the node ID closest to the root

    :param graph: graph to resolve root node for
    :type grpah:  Graph or GraphAxis object

    :return:      root node ID
    """

    # Default graph root node
    root = graph.root or initial_node(graph.nodes())

    # If root in current (sub)graph, return
    if root in graph.nodes:
        return root

    # If one node, return as root
    if len(graph) == 1:
        return list(graph.nodes.keys())[0]

    # If multiple nodes, resolve closest to root
    if root in graph._full_graph.nodes():
        return initial_node(graph.nodes())


def coarse_type(n):

    if n.isdigit():
        return int(n)
    return n


def check_lie_graph_version(version=None):
    """
    Check if the graph version of the file is (backwards) compatible with
    the current lie_graph module version
    """
    
    try:
        version = float(version)
    except TypeError:
        logging.error('No valid lie_graph version identifier {0}'.format(version))
        return False
    
    if version > float(__version__):
        logging.error('Graph made with a newer version of lie_graph {0}, you have {1}'.format(version, __version__))
        return False
        
    return True    


def open_anything(source, mode='r'):
    """
    Open input available from a file, a Python file like object, standard
    input, a URL or a string and return a uniform Python file like object
    with standard methods.

    :param source: Input as file, Python file like object, standard
                   input, URL or a string
    :type source:  mixed
    :param mode:   file access mode, defaults to 'r'
    :type mode:    string
    :return:       Python file like object
    """

    # Check if the source is a file and open
    if os.path.isfile(source):
        logging.debug('Reading file from disk {0}'.format(source))
        return open(source, mode)

    # Check if source is file already openend using 'open' or 'file' return
    if hasattr(source, 'read'):
        logging.debug('Reading file {0} from file object'.format(source.name))
        return source

    # Check if source is standard input
    if source == '-':
        logging.debug('Reading file from standard input')
        return sys.stdin

    else:
        # Check if source is a URL and try to open
        try:
            if urlparse.urlparse(source)[0] == 'http':
                result = urllib.urlopen(source)
                logging.debug("Reading file from URL with access info:\n {0}".format(result.info()))
                return result
        except IOError:
            logging.info("Unable to access URL")

        # Check if source is file and try to open else regard as string
        try:
            return open(source)
        except IOError:
            logging.debug("Unable to access as file, try to parse as string")
            return StringIO.StringIO(str(source))


def flatten_nested_dict(config, parent_key='', sep='.'):
    """
    Flatten a nested dictionary by concatenating all
    nested keys.
    Keys are converted to a string representation if
    needed.

    :param config:     dictionary to flatten
    :type config:      :py:dict
    :param parent_key: leading string in concatenated keys
    :type parent_key:  :py:str
    :param sep:        concatenation separator
    :type sep:         :py:str
    :return:           flattened dictionary
    :rtype:            :py:dict
    """

    items = []
    for key, value in config.items():

        # parse key to string if needed
        if type(key) not in (str, unicode):
            logging.debug('Dictionary key {0} of type {1}. Parse to unicode'.format(key, type(key)))
            key = unicode(key)

        new_key = unicode(parent_key + sep + key if parent_key else key)
        if isinstance(value, collections.MutableMapping):
            items.extend(flatten_nested_dict(value, new_key, sep=sep).items())
        else:
            items.append((new_key, value))

    return dict(items)


def nest_flattened_dict(graph_dict, sep='.'):
    """
    Convert a dictionary that has been flattened by the
    `_flatten_nested_dict` method to a nested representation

    :param graph_dict: dictionary to nest
    :type graph_dict:  dict
    :param sep:        concatenation seperator
    :type sep:         str

    :return:           nested dictionary
    :rtype:            dict
    """

    nested_dict = {}
    for key, value in sorted(graph_dict.items()):

        splitted = key.split(sep)
        if len(splitted) == 1:
            nested_dict[key] = value

        d = nested_dict
        for k in splitted[:-1]:
            if k not in d:
                d[k] = {}
            d = d[k]

        d[splitted[-1]] = value

    return nested_dict


class FormatDetect(object):
    """
    Type cast string or unicode objects to float, integer or boolean.

    Uses localization to identify

    TODO: comma separated strings fail if one comma
    """

    def __init__(self, set_locale='en_US.UTF-8', decimal_point=None, thousands_sep=None):

        # Determine current localization and switch to international
        # en_US localization or other.
        self.curr_locale = locale.getdefaultlocale()
        if self.curr_locale != set_locale:
            logging.debug('Switch localization: {0} to {1}'.format('.'.join(self.curr_locale), set_locale))
            locale.setlocale(locale.LC_ALL, set_locale)

        # Register localization specific decimal and thousands seperator
        locenv = locale.localeconv()
        self.decimal_point = decimal_point or locenv['decimal_point']
        self.thousands_sep = thousands_sep or locenv['thousands_sep']

        # Register Boolean types
        self.true_types = ['true']
        self.false_types = ['false']

    def to_integer(self, value):

        if isinstance(value, (str, unicode)):
            return locale.atoi(value)
        return int(value)

    def to_number(self, value):

        if isinstance(value, (str, unicode)):
            return locale.atof(value)
        return float(value)

    def to_string(self, value):

        return unicode(value)

    def to_boolean(self, value):

        if value.lower() in self.true_types:
            return True
        if value.lower() in self.false_types:
            return False

        return value

    def to_detect(self, value):

        # if string contains spaces or very long, return
        if ' ' in value or len(value) > 100:
            return value

        # str to unicode
        value = self.to_string(value)
        unicode_cats = [unicodedata.category(i)[0] for i in value]

        # Comma seperated string
        if value.count(self.thousands_sep) > 1:
            return self.to_string(value)

        # first try to convert unicode to float
        try:
            parsed = locale.atof(value)
        except ValueError:
            parsed = value

        if isinstance(parsed, float):

            # Maybe it was an integer
            allnumbers = all([n[0] == 'N' for n in unicode_cats])
            if value.isdigit() or value.isnumeric() or allnumbers:
                parsed = locale.atoi(value)
            if value.count(self.decimal_point) == 0:
                parsed = int(parsed)

            return parsed

        # Try convert unicode to integer
        try:
            parsed = self.to_integer(value)
        except ValueError:
            parsed = value

        if not isinstance(parsed, int):

            # Cases that are fully numeric with thousand seperators (e.g. 123.222.12)
            if value.count(self.decimal_point) > 1 and value.count(self.thousands_sep) == 0:
                parsed = int(value.replace(self.decimal_point, ''))

            # Unicode could be a boolean
            parsed = self.to_boolean(value)

        return parsed

    def parse(self, value, target_type=None):
        """
        Parse an unknown value to a float, integer, boolean or else
        remain in unicode.

        :param value:       value to parse
        :param target_type: type to convert to as 'integer', 'number', 'string',
                            'boolean' or automatic 'detect'
        :return:            parsed value
        """

        # target type not defined then try detect
        if not target_type:

            # if value already parsed to a type other than str or unicode return
            if type(value) not in (str, unicode):
                return value

            target_type = 'detect'

        parse_method = getattr(self, 'to_{0}'.format(target_type), None)
        assert parse_method != None, 'Unknown type: {0}'.format(target_type)

        return parse_method(value)
