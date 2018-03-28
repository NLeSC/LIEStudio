# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

import logging
import sys

from autobahn.wamp.exception import ApplicationError
from lie_cli.cli_parser import lie_cli_parser
from mdstudio.component.session import ComponentSession

from twisted.internet import reactor

# Override txaio logger to print result to stdout
lg = logging.getLogger('clilogger')
lg.setLevel(logging.INFO)
lg.addHandler(logging.StreamHandler(sys.stdout))


class CliWampApi(ComponentSession):
    """
    CLI WAMP methods.
    """
    def authorize_request(self, uri, claims):
        """
        If you were allowed to call this in the first place,
        I will assume you are authorized
        """
        return True

    def _result_callback(self, result):

        # Format output and log to stdout
        if len(result) == 1:
            lg.info(result.values()[0])
        else:
            for k, v in result.items():
                lg.info('{0} = {1}'.format(k, v))

        # Disconnect from broker and stop reactor event loop
        self.disconnect()
        reactor.stop()

    def _error_callback(self, failure):

        failure_message = failure
        if isinstance(failure, Exception) or isinstance(failure, str):
            failure_message = str(failure)
        elif isinstance(failure.value, ApplicationError):
            failure_message = failure.value.error_message()
        else:
            failure.getErrorMessage()
        self.log.error('Unable to process: {0}'.format(failure_message))

        # Disconnect from broker and stop reactor event loop
        self.disconnect()
        reactor.stop()

    def on_run(self):
        config = lie_cli_parser()

        # # Define method uri
        uri = config['uri']
        del config['package_config']['uri']

        # Call method and wait for results
        with self.group_context('mdgroup'):
            deferred = self.call(uri, config["package_config"])
            deferred.addCallback(self._result_callback)
            deferred.addErrback(self._error_callback)
