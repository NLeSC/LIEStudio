# -*- coding: utf-8 -*-

"""
file: io_web_format.py

Functions for reading and writing hierarchical data structures defined by the
Spider data modelling package as .web format files.

A .web format defines data blocks containing key, value pairs or Array data
as hierarchically nested blocks enclosed using braces '(' and '),' and indented
for visual clarity.

Every data item in the format is written on a new line and is either a
traditional key, value pair as: 'key = value,' or a single that are together
combined into an array like:

    key = FloatArray (
        1.0,
        2.0,
    )

Key, value pairs and array type data structures can be freely combined such as
in:

    c2segments = LabeledRangePairArray (
        LabeledRangePair (
            r = LabeledRangeArray (
                LabeledRange (
                    start = 1,
                    end = 12,
                    chain = 'A',
                ),
                LabeledRange (
                    start = 1,
                    end = 12,
                    chain = 'B',
                ),
            ),
        ),
    ),

The data inside a LabeledRange are key, value pairs but LabeledRange and also
LabeledRangePair are array types. The latter two are stored as nodes in the
graph and are automatically assigned a key as "itemX" where X is an incremented
integer.

The type of any piece of data is loosely defined by a type identifier in front
of every new data block that closely reassembles a Python style class name.
The 'FloatArray' identifier in the expression above would be an example.
These identifiers are usually coupled to classes in charge of data exchange
by an object relations mapper such as the one used in the lie_graph package.
"""

import logging
import sys

from lie_graph.graph_axis.graph_axis_class import GraphAxis
from lie_graph.graph_axis.graph_axis_methods import node_parent
from lie_graph.graph_io.io_helpers import open_anything, FormatDetect, resolve_root_node
from lie_graph.graph_helpers import GraphException
from lie_graph.graph_mixin import NodeTools
from lie_graph.graph_orm import GraphORM

if sys.version_info[0] < 3:
    import StringIO
else:
    from io import StringIO


class WebNodeTools(NodeTools):

    def get(self, key=None, default=None, defaultattr=None):
        """
        Serialize all string/unicode values as quoted strings
        """

        key = key or self.node_value_tag
        target = self.nodes[self.nid]

        if key in target:
            if key == self.node_value_tag and isinstance(target[key], (str, unicode)):
                return "'{0}'".format(target[key])
            return target[key]

        return target.get(defaultattr, default)


class RestraintsInterface(NodeTools):
    """
    Class to handle residue restraint specific formatting for .web
    files to custom `get` and `set` methods used during graph
    import and export.
    """

    def get(self, key=None, default=None, defaultattr=None):
        """
        Serialize residue restraints as a comma separated string

        Expects an iterable with integer values but will return
        a string anyway.

        :return:  string of comma separated residue numbers
        :rtype:   :py:str
        """

        key = key or self.node_value_tag
        target = self.nodes[self.nid]

        if key in target:

            if key == self.node_value_tag:
                if isinstance(target[key], (list, tuple)):
                    joined = ','.join([str(i) for i in target[key]])
                    return "'{0}'".format(joined)

                if len(target[key]):
                    logging.warning('RestraintsInterface get method expected an iterable, got {0}.'.format(type(target[key])))

            return repr(target[key])

        return target.get(defaultattr, default)

    def set(self, key, value=None):
        """
        Parse residue restraint definitions from a comma separated string of
        integer values to a list

        :param key:     node key to set
        :type key:      :py:str
        :param value:   node value to set
        :type value:    :py:str
        """

        if key == self.node_value_tag:
            if value == None:
                value = []

            if isinstance(value, (str, unicode)):
                value = [int(n) for n in value.strip("'").split(',') if n]
            assert all([isinstance(n, int) for n in value])

        self.nodes[self.nid][key] = value


def read_web(web, graph=None, orm_data_tag='haddock_type', node_key_tag=None, edge_key_tag=None, auto_parse_format=False):
    """
    Import hierarchical data structures defined in the Spider .web format

    The data block type identifiers used in the .web format are stored in
    the nodes using the `orm_data_tag` attribute. These can be used by the
    Graph ORM mapper for custom data exchange in the graph.

    :param web:               Spider .web data format to import
    :type web:                file, string, stream or URL
    :param graph:             graph object to import TGF data in
    :type graph:              :lie_graph:Graph
    :param orm_data_tag:      data key to use for .web data identifier
    :type orm_data_tag:       :py:str
    :param node_key_tag:      data key to use for parsed node labels.
    :type node_key_tag:       :py:str
    :param edge_key_tag:      data key to use for parsed edge labels.
    :type edge_key_tag:       :py:str
    :param auto_parse_format: automatically detect basic format types
    :type auto_parse_format:  :py:bool

    :return:                  Graph object
    :rtype:                   :lie_graph:Graph
    """

    web_file = open_anything(web)
    if not isinstance(graph, GraphAxis):
        graph = GraphAxis()

    # Define node/edge data labels
    if node_key_tag:
        graph.node_key_tag = node_key_tag
    if edge_key_tag:
        graph.edge_key_tag = edge_key_tag

    # Build .web parser ORM with format specific conversion classes
    weborm = GraphORM()
    weborm.map_node(RestraintsInterface, {graph.node_key_tag: 'activereslist'})
    weborm.map_node(RestraintsInterface, {graph.node_key_tag: 'passivereslist'})

    # Set current ORM aside and register parser ORM.
    curr_orm = graph.orm
    graph.orm = weborm

    # Auto-convert format types
    if auto_parse_format:
        autoformat = FormatDetect()
        logging.info('Init automatic format conversion')

    curr_obj_nid = None
    object_open_tags = 0
    object_close_tags = 0
    array_key_counter = 1
    array_store = []
    for i, line in enumerate(web_file.readlines()):
        line = line.strip()
        if len(line):

            # Detect start of new object definition
            if line.endswith('('):

                # Process data
                meta_data = [n.strip() for n in line.strip('(').split('=', 1)]
                ddict = {orm_data_tag: meta_data[-1], 'is_array': False}
                if len(meta_data) > 1:
                    node_key = meta_data[0]
                else:
                    node_key = 'item{0}'.format(array_key_counter)
                    ddict['is_array'] = True
                    array_key_counter += 1

                # Clear the array store
                array_store = []

                # First object defines graph root
                if graph.empty():
                    curr_obj_nid = graph.add_node(node_key, **ddict)
                    graph.root = curr_obj_nid

                # Add new object as child of current object
                else:
                    child_obj_nid = graph.add_node(node_key, **ddict)
                    graph.add_edge(curr_obj_nid, child_obj_nid)
                    curr_obj_nid = child_obj_nid

                object_open_tags += 1

            # Detect end of object definition
            elif line.startswith(')'):

                # If there is data in the array store, add it to node
                if len(array_store):
                    array_node = graph.getnodes(curr_obj_nid)
                    array_node.is_array = True
                    array_node.set(graph.node_value_tag, array_store)

                # Reset array key counter
                array_key_counter = 1

                # Move one level up the object three
                curr_obj_nid = node_parent(graph, curr_obj_nid, graph.root)
                object_close_tags += 1

            # Parse object parameters
            else:

                # Parse key,value pairs and add as leaf node
                params = [n.strip() for n in line.rstrip(',').split('=', 1)]
                params = [n.strip("'") for n in params]
                if auto_parse_format:
                    params = [autoformat.parse(v) for v in params]

                if '=' in line and len(params) == 2:
                    leaf_nid = graph.add_node(params[0])
                    graph.add_edge(curr_obj_nid, leaf_nid)

                    leaf_node = graph.getnodes(leaf_nid)
                    leaf_node.set(graph.node_value_tag, params[1])

                # Parse single values as array data
                elif len(params) == 1:

                    # Store array items as nodes
                    array_store.extend(params)

                else:
                    logging.warning('Unknown .web data formatting on line: {0}, {1}'.format(i, line))

    web_file.close()

    # Object blocks opening '(' and closing ')' tag count should be balanced
    assert object_open_tags == object_close_tags, 'Unbalanced object block, something is wrong with the file format'

    # Restore original ORM
    graph.orm = curr_orm

    return graph


def write_web(graph, orm_data_tag='haddock_type', node_key_tag=None, indent=2, root_nid=None,):
    """
    Export a graph in Spyder .web format

    .. note::
    Web graph export uses the Graph iternodes and iteredges methods to retrieve
    nodes and edges and 'get' the data labels. The behaviour of this process is
    determined by the single node/edge mixin classes and the ORM mapper.

    :param graph:         Graph object to export
    :type graph:          :lie_graph:Graph
    :param orm_data_tag:  data key to use for .web data identifier
    :type orm_data_tag:   :py:str
    :param node_key_tag:  node data key
    :type node_key_tag:   :py:str
    :param indent:        .web file white space indentation level
    :type indent:         :py:int
    :param root_nid:      Root node ID in graph hierarchy

    :return:              Spyder .web graph representation
    :rtype:               :py:str
    """

    # Define node data tags to export
    node_key_tag = node_key_tag or graph.node_key_tag
    node_value_tag = graph.node_value_tag

    # Buid ORM with format specific conversion classes
    weborm = GraphORM()
    weborm.map_node(RestraintsInterface, {graph.node_key_tag: 'activereslist'})
    weborm.map_node(RestraintsInterface, {graph.node_key_tag: 'passivereslist'})

    # Resolve the root node (if any) for hierarchical data structures
    if root_nid:
        assert root_nid in graph.nodes, GraphException('Root node ID {0} not in graph'.format(root_nid))
    else:
        root_nid = resolve_root_node(graph)
        assert root_nid is not None, GraphException('Unable to resolve root node ID')

    # Set current NodeTools aside and register new one
    curr_nt = graph.node_tools
    graph.node_tools = WebNodeTools

    # Set current ORM aside and register new one.
    curr_orm = graph.orm
    graph.orm = weborm

    # Create empty file buffer
    string_buffer = StringIO.StringIO()

    # Traverse node hierarchy
    def _walk_dict(node, indent_level):

        # First, collect all leaf nodes and write
        for leaf in [n for n in node.children(include_self=True) if n.isleaf]:

            # Format 'Array' types when they are list style leaf nodes
            if leaf.get('is_array', False):
                string_buffer.write('{0}{1} = {2} (\n'.format(' ' * indent_level,
                                                             leaf.get(node_key_tag),
                                                             leaf.get(orm_data_tag)))

                array_indent = indent_level + indent
                for array_type in leaf.get(node_value_tag, default=[]):
                    string_buffer.write('{0}{1},\n'.format(' ' * array_indent, array_type))

                string_buffer.write('{0}),\n'.format(' ' * indent_level))

            # Format key, value pairs
            else:
                string_buffer.write('{0}{1} = {2},\n'.format(' ' * indent_level,
                                                             leaf.get(node_key_tag),
                                                             leaf.get(node_value_tag, default='')))

        # Second, process child non-leaf nodes
        for child in [n for n in node.children() if not n.isleaf]:

            # Write block header
            key = ''
            if not child.get('is_array', False):
                key = '{0} = '.format(child.get(node_key_tag))
            string_buffer.write('{0}{1}{2} (\n'.format(' ' * indent_level, key, child.get(orm_data_tag)))

            # Indent new data block one level down and walk children
            indent_level += indent
            _walk_dict(child, indent_level)

            # Close data block and indent one level up
            indent_level -= indent
            string_buffer.write('{0}),\n'.format(' ' * indent_level))

    rootnode = graph.getnodes(root_nid)

    if rootnode.isleaf:
        _walk_dict(rootnode, 0)
    else:
        string_buffer.write('{0} (\n'.format(rootnode.get(orm_data_tag)))
        _walk_dict(rootnode, indent)
        string_buffer.write(')\n')

    # Restore original ORM and NodeTools
    graph.node_tools = curr_nt
    graph.orm = curr_orm

    # Reset buffer cursor
    string_buffer.seek(0)
    return string_buffer.read()
