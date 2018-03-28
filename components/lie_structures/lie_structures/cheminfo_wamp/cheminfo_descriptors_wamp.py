# -*- coding: utf-8 -*-

from lie_structures.cheminfo_molhandle import mol_read
from mdstudio.api.endpoint import endpoint
from mdstudio.component.session import ComponentSession


class CheminfoDescriptorsWampApi(ComponentSession):
    """
    Cheminformatics descriptors WAMP API
    """
    def authorize_request(self, uri, claims):
        return True

    @endpoint('descriptors', 'descriptors_request', 'descriptors_response')
    def get_descriptors(self, request, claims):

        # Import the molecule
        molobject = mol_read(
            request["structure"], mol_format=request["mol_format"],
            toolkit=request["toolkit"])
        desc = molobject.calcdesc()

        if desc is not None:
            status = 'completed'
            output = desc
        else:
            status = 'failed'
            output = None

        return {'session': status, 'descriptors': output}
