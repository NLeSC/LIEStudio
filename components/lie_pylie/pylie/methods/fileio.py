# -*- coding: utf-8 -*-

import sys
import os
import re
import logging
import numpy

from pandas import DataFrame

from .sybyl import AA_SYBYL_TYPES

if sys.version_info[0] < 3:
    import StringIO
    import urlparse
    import urllib2 as urllib
else:
    from io import StringIO
    from urllib import parse as urlparse

logger = logging.getLogger('pylie')


def _open_anything(source):

    # Check if the source is a file and open
    if os.path.isfile(source):
        logger.debug("Reading file from disk {0}".format(source))
        return open(source, 'r')

    # Check if source is file already openend using 'open' or 'file' return
    elif hasattr(source, 'read'):
        logger.debug("Reading file %s from file object" % source.name)
        return source

    # Check if source is standard input
    elif source == '-':
        logger.debug("Reading file from standard input")
        return sys.stdin

    else:
        # Check if source is a URL and try to open
        try:
            if urlparse.urlparse(source)[0] == 'http':
                result = urllib.urlopen(source)
                logger.debug("Reading file from URL with access info:\n %s" % result.info())
                return result
        except IOError:
            logger.info("Unable to access URL")

            # Check if source is file and try to open else regard as string
        try:
            return open(source)
        except IOError:
            logger.debug("Unable to access as file, try to parse as string")
            return StringIO.StringIO(str(source))


def read_gromacs_energy_file(file_or_buffer, columns=None, lowercase=True):
    """
    Read GROMACS molecular dynamics trajectory energy file

    Import all data columns into a pandas DataFrame including the compulsory
    'FRAME' and 'Time' columns. Using `columns`, a columns selection can be
    specified next to the FRAME and Time columns.

    :param file_or_buffer:  GROMACS energy file path or file-like object
    :param columns:         selection of columns to import
    :type columns:          :py:list
    :param lowercase:       convert all column headers to lowercase.
    :type lowercase:        :py:bool

    :return:                energy trajectory as Pandas DataFrame
    :rtype:                 :pandas:DataFrame
    """

    # Which columns to extract. Always the first two, FRAME and Time
    extract_columns = ['FRAME', 'Time']
    if columns:
        extract_columns.extend(columns)

    # Open the input regardless of its type using open_anything
    file_or_buffer = _open_anything(file_or_buffer)

    # Try getting the headers. GROMACS header starts with '#'
    header = file_or_buffer.readline()
    if not header.startswith('#'):
        logger.warn("Not sure if this is a GROMACS energy file. Header line does not start with #")

    # Frame and Time columns together with user specified ones should be present
    header = header.split()[1:]
    if set(extract_columns).intersection(set(header)) != set(extract_columns):
        missing = set(extract_columns).difference(set(header))
        logger.error("GROMACS energy file has no columns named: {0}".format(','.join(missing)))
        return None

    # If no columns selection defined, extract everything
    if not columns:
        extract_columns = header

    # Try parsing the numeric data into a numpy array
    try:
        data = numpy.loadtxt(file_or_buffer, comments='#')
    except IOError:
        logger.error("Unable to import trajectory data from GROMACS energy file {0}".format(file_or_buffer.name))
        return None

    # Extract relevant columns and return as Pandas DataFrame
    header_indexes = [header.index(n) for n in extract_columns]
    extract_columns = ['frame', 'time'] + extract_columns[2:]
    df = DataFrame(data[:, header_indexes], columns=extract_columns)

    # Lowercase headers?
    if lowercase:
        df.columns = [col.lower() for col in extract_columns]

    logger.debug("Imported Gromacs MD energy data from {0}, {1} datapoints".format(file_or_buffer.name, df.shape))
    file_or_buffer.close()
    return df


def read_lie_etox_file(file_or_buffer):
    # Open the input regardless of its type using open_anything
    file_or_buffer = _open_anything(file_or_buffer)

    ref_affinity = 1

    # Import data from file. Check for pose consistency
    data = []
    cursor = 4
    if ref_affinity is None:
        cursor -= 1
    for index, line in enumerate(file_or_buffer.readlines()):
        line = line.strip()
        if len(line) and not line.startswith('#'):
            line = [float(n) for n in line.split()]
            vdw = line[cursor:len(line):2]
            coul = line[cursor + 1:len(line):2]

            if len(vdw) != len(coul) or (len(vdw) + len(coul)) % 2 != 0:
                logger.error("Number of pose VdW energies not match Coul energies in line {0}".format(index))
            else:
                for pose in range(len(vdw)):
                    data.append(line[0:cursor] + [pose + 1, vdw[pose], coul[pose]])

    file_or_buffer.close()

    df = DataFrame(data,
                   columns=['case', 'ref_affinity', 'vdw_unbound', 'coul_unbound', 'poses', 'vdw_bound', 'coul_bound'])
    logger.info("Imported eTox LIE data from {0}, {1} datapoints".format(file_or_buffer.name, df.shape))

    return df


class MOL2Parser(object):
    """
    Parse a Tripos MOL2 file format.
    """
    def __init__(self, columns):

        self.mol_dict = dict([(n, []) for n in columns])

    def parse(self, mol_file):
        """
        Parse MOL2 atom definition into named columns and return as
        dictionary.
        Currently parses one model only and expects the order of the
        columns to be respectively: aton number, atom name, x-coor,
        y-coor, z-coor, SYBYL atom type, residue number, residue name
        and charge.
        MOL2 is a free format (no fixed column width). Their should be
        at least one empty space between each subsequent value on a line.
        The parser will raise an exception if this is not the case.

        :param mol_file:
        :return:
        """

        read = False
        model = 0
        for line in mol_file.readlines():
            if line.startswith('@<TRIPOS>ATOM'):
                read = True
                model += 1
                continue
            elif line.startswith('@<TRIPOS>BOND'):
                read = False
                break

            if read:
                l = line.split()
                if not len(l) >= 9:
                    raise IOError('FormatError in mol2. Line: {0}'.format(line))

                try:
                    self.mol_dict['atnum'].append(int(l[0]))
                    self.mol_dict['atname'].append(l[1].upper())
                    self.mol_dict['xcoor'].append(float(l[2]))
                    self.mol_dict['ycoor'].append(float(l[3]))
                    self.mol_dict['zcoor'].append(float(l[4]))
                    self.mol_dict['attype'].append(l[5])
                    self.mol_dict['resnum'].append(int(l[6]))
                    self.mol_dict['resname'].append(re.sub('{0}$'.format(l[6]), '', l[7]))
                    self.mol_dict['charge'].append(float(l[8]))
                except ValueError, e:
                    raise IOError('FormatError in mol2. Line: {0}, error {1}'.format(line, e))

        return self.mol_dict


class PDBParser(object):
    def __init__(self, columns):

        self.pdb_dict = dict([(n, []) for n in columns])

    def parse(self, pdb_file):

        atomline = re.compile('(ATOM)')
        hetatmline = re.compile('HETATM')
        modelline = re.compile('MODEL')

        modelcount = 0
        for line in pdb_file.readlines():
            line = line[:-1]

            if modelline.match(line):
                modelcount += 1
                continue

            if atomline.match(line):
                atomdict = self.__processatom(line, valuedict={'label': 'atom', 'model': modelcount})
                atomdict['attype'] = self.__assign_sybyl_atomtype(atomdict)
                for key, value in atomdict.items():
                    self.pdb_dict[key].append(value)
                continue

            if hetatmline.match(line):
                atomdict = self.__processatom(line, valuedict={'label': 'hetatm', 'model': modelcount})
                atomdict['attype'] = self.__assign_sybyl_atomtype(atomdict)
                for key, value in atomdict.items():
                    self.pdb_dict[key].append(value)

        return self.pdb_dict

    @staticmethod
    def __assign_sybyl_atomtype(valuedict):
        """
        Add SYBYL atom type information.

        Only supports predefined SYBYL types for common amino-acid atoms based
        on the AA_SYBYL_TYPES dictionary.
        """

        ra_id = '{0}-{1}'.format(valuedict.get('resname', ''), valuedict.get('atname', ''))
        return AA_SYBYL_TYPES.get(ra_id, None)

    def __processatom(self, line, valuedict=None):

        """Processes the atom line according to RCSB recomendations."""
        if not valuedict:
            valuedict = {}

        valuedict['atnum'] = self.__processatomline(line, 12, minlen=6, vtype='int')
        valuedict['atname'] = self.__processatomline(line, 16, minlen=12)
        valuedict['atalt'] = self.__processatomline(line, 17, minlen=16)
        valuedict['resname'] = self.__processatomline(line, 21, minlen=17)
        valuedict['chain'] = self.__processatomline(line, 21)
        valuedict['resnum'] = self.__processatomline(line, 26, minlen=22, vtype='int')
        valuedict['resext'] = self.__processatomline(line, 27)
        valuedict['xcoor'] = self.__processatomline(line, 38, minlen=30, vtype='float')
        valuedict['ycoor'] = self.__processatomline(line, 46, minlen=38, vtype='float')
        valuedict['zcoor'] = self.__processatomline(line, 54, minlen=46, vtype='float')
        valuedict['occ'] = self.__processatomline(line, 60, minlen=54, vtype='float')
        valuedict['b'] = self.__processatomline(line, 66, minlen=60, vtype='float')
        valuedict['segid'] = self.__processatomline(line, 75, minlen=72)
        valuedict['elem'] = self.__processatomline(line, 78, minlen=76)

        return valuedict

    @staticmethod
    def __processatomline(line, maxlen, minlen=None, vtype='string'):

        """Test if a ATOM related parameter is found at its correct location within the ATOM line
           (within the 'maxlen', 'minlen' character location identifiers). If it is found it is
           converted to the appropriate type using the 'vtype' argument. If the type is a string
           the letters are converted to upper case.
        """
        if minlen is None:
            if len(line) < maxlen or len(line[maxlen].strip()) == 0:
                return None
            else:
                if vtype == 'int':
                    return int(line[maxlen])
                elif vtype == 'float':
                    return float(line[maxlen])
                else:
                    return line[maxlen].upper()
        else:
            if len(line) < maxlen or len(line[minlen:maxlen].strip()) == 0:
                return None
            else:
                if vtype == 'int':
                    return int(line[minlen:maxlen])
                elif vtype == 'float':
                    return float(line[minlen:maxlen])
                else:
                    return (line[minlen:maxlen].strip()).upper()
