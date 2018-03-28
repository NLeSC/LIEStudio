# -*- coding: utf-8 -*-

"""
file: io_jsonschema_format.py

Functions for building and validating graphs based on a JSON schema definition.
http://json-schema.org
"""

import json
import sys

if sys.version_info[0] < 3:
    import urlparse
else:
    from urllib import parse as urlparse

from lie_graph.graph_axis.graph_axis_class import GraphAxis
from lie_graph.graph_axis.graph_axis_mixin import NodeAxisTools


def type_parse(value, ptype='string'):

    if not isinstance(value, (str, unicode)):
        return value

    if ptype == 'integer':
        return int(value)
    if ptype == 'number':
        return float(value)
    if ptype == 'boolean':
        if ptype.lower() == 'true':
            return True
        if ptype.lower() == 'false':
            return False

    return value


def type_validate(value, ptype='string'):

    if value == None:
        return value

    if ptype == 'string':
        if not isinstance(value, (str, unicode)):
            raise ValueError('Value {0} not of type {1}'.format(value, ptype))
    elif ptype == 'number':
        if not isinstance(value, float):
            raise ValueError('Value {0} not of type {1}'.format(value, ptype))
    elif ptype == 'integer':
        if not isinstance(value, int):
            raise ValueError('Value {0} not of type {1}'.format(value, ptype))
    elif ptype == 'boolean':
        if not isinstance(value, bool):
            raise ValueError('Value {0} not of type {1}'.format(value, ptype))
    elif ptype == 'array':
        if not isinstance(value, list):
            raise ValueError('Value {0} not of type {1}'.format(value, ptype))
    else:
        raise ValueError('Unknow type {0} for value {1}'.format(ptype, value))

    return value


class SchemaNodeTools(NodeAxisTools):

    def __iter__(self):
        """
        Implement class __iter__

        Directly iterate over child nodes

        :return: child node
        :rtype:  GraphAxis
        """

        for child in self.children(return_nids=True):
            yield self.getnodes(child)

    def set(self, key, value):
        """
        Overload default NodeTools set method to type check
        values to set according to JSON Schema type definition.

        :param key:   node attribute key
        :param value: node attribute value
        """

        schema = self.nodes[self.nid].get('_schema')
        if schema:
            self.nodes[self.nid][key] = type_validate(value, schema.get('type', 'string'))
        else:
            self.nodes[self.nid][key] = value


class SchemaCoreValidator(object):

    _meta_tags = [u'$schema', u'$ref', u'description', u'type', u'required', u'format',
                  u'properties']

    def schema_meta_data(self, schema):

        meta_data = dict([(k,v) for k,v in schema.items() if k in self._meta_tags])

        meta_data['draft'] = 'general'
        if '$schema' in meta_data:
            url = urlparse.urlparse(meta_data['$schema'])
            draft = 'general'
            for path_element in url.path.split('/'):
                if 'draft-' in path_element:
                    meta_data['draft'] = path_element.replace('draft-', '')
                    break

        return meta_data

    def parse_schema_level(self, schema):

        return dict([(k,v) for k,v in schema.items() if not isinstance(v, dict)])


class JSONSchemaParser(object):
    """
    JSON schema parser class.

    Builds an graph based (node) object Python object tree based on the JSON
    schema hierarchy.
    Each graph node contains data placeholders with defaults and the JSON
    schema rule set to validate the data.
    """
    def __init__(self, schema, validator=None, graph=None):

        self.schema = self.__parse_schema(schema)

        self.validator = validator or SchemaCoreValidator()
        schema_meta = self.validator.schema_meta_data(self.schema)

        # Init (new) graph
        self.graph = graph or GraphAxis()
        self.graph.node_tools = SchemaNodeTools
        if self.graph.empty():
            rid = self.graph.add_node('root')
            self.graph.root = rid

        # Start parsing
        self.parse_schema(self.schema, parent=self.graph.root)

    def __parse_schema(self, schema):

        return json.load(open(schema))

    def parse_schema(self, schema, parent=None):
        """
        Parse a JSON schema into a graph structure

        :param schema:  JSON schema to parse as file path
        :type schema:   :py:str
        :param parent:  Graph parent node ID used for recursive parsing.
                        Used internally.
        :type parent:   :py:int
        """

        # Get all JSON schema definitions for this data instance
        attributes = self.validator.parse_schema_level(schema)
        node = self.graph.getnodes(parent)

        # Add all JSON schema validation constraints to the parent node
        # as a '_schema' dictionary.
        node['_schema'] = attributes

        # Store default data or None
        node['value'] = attributes.get('default')

        # For all child elements in properties, make new node
        # and parse using recursive calls to parse_schema
        if 'properties' in schema:
            for child, attr in schema['properties'].items():
                nid = self.graph.add_node(child)
                self.graph.add_edge(parent, nid)
                self.parse_schema(attr, parent=nid)
