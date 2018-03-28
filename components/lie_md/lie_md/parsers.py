# -*- coding: utf-8 -*-
from __future__ import print_function

import pyparsing as pp


def parse_file(p, file_name):
    """
    Wrapper over the parseFile method
    """
    try:
        return p.parseFile(file_name).asList()
    except pp.ParseException:
        msg = "Error Trying to parse: {} in file: {}".format(p, file_name)
        print(msg)
        raise


def skipSupress(z):
    """Suppress stream until `z`"""
    return pp.Suppress(pp.SkipTo(z))


# parse utils
natural = pp.Word(pp.nums)

float_number = pp.Regex(r'(\-)?(\d+)?(\.)(\d*)?([eE][\-\+]\d+)?')

skipLine = pp.Suppress(skipSupress('\n'))

comment = pp.Suppress(pp.Literal(';')) + skipLine

optional_comment = pp.ZeroOrMore(comment)

word = pp.Word(pp.alphanums + "*")

line = pp.Group(
    pp.OneOrMore(float_number | word) + pp.Optional(comment))

lines = pp.Group(pp.OneOrMore(line))

brackets = pp.Suppress("[") + word + pp.Suppress("]")

# High level parsers
section = brackets + optional_comment + lines

many_sections = pp.Group(pp.OneOrMore(section))


# Parser for itp files
itp_parser = optional_comment + many_sections

# Parser for the atom section of mol2 files
header_mol2 = skipSupress(pp.Literal("@<TRIPOS>ATOM")) + skipLine
parser_atoms_mol2 = header_mol2 + pp.Group(pp.OneOrMore(line + skipLine))
