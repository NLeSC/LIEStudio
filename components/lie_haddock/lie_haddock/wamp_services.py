# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

from mdstudio.api.endpoint import endpoint
from mdstudio.component.session import ComponentSession


class HaddockWampApi(ComponentSession):
    """
    HADDOCK docking WAMP methods.

    Defines `require_config` to retrieve system and database configuration
    upon WAMP session setup
    """

    @endpoint(u'get')
    def retrieve_haddock_project(self, request, claims):
        """
        Retrieve the docking results as tar zipped archive

        :param request: HADDOCK web server project name
        :type request:  :py:str
        """

    @endpoint(u'status')
    def haddock_project_status(self, request, claims):
        """
        Retrieve the status of a submitted haddock project

        :param request: HADDOCK web server project name
        :type request:  :py:str
        """

    @endpoint(u'submit')
    def submit_haddock_project(self, request, claims):
        """
        Submit a docking project to the HADDOCK web server

        :param request: HADDOCK web server project name
        :type request:  :py:str
        """
        pass
