# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

from autobahn import wamp

from lie_system import WAMPTaskMetaData
from lie_structures.cheminfo_molhandle import mol_read

class CheminfoDescriptorsWampApi(object):
    """
    Cheminformatics descriptors WAMP API
    """

    @wamp.register(u'liestudio.cheminfo.descriptors')
    def get_descriptors(self, structure=None, mol_format=None, toolkit='pybel', session=None):

        # Retrieve the WAMP session information
        session = WAMPTaskMetaData(metadata=session)

        # Import the molecule
        molobject = mol_read(structure, mol_format=mol_format, toolkit=toolkit)
        desc = molobject.calcdesc()

        if desc:
            session.status = 'completed'
            return {'session': session.dict(), 'descriptors': desc}

        session.status = 'failed'
        return {'session': session.dict()}

