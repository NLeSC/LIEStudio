# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

import sys
import logging

from autobahn.wamp.exception import ApplicationError
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor

from lie_system import LieApplicationSession

# Override txaio logger to print result to stdout
lg = logging.getLogger('clilogger')
lg.setLevel(logging.INFO)
lg.addHandler(logging.StreamHandler(sys.stdout))


class CliWampApi(LieApplicationSession):
    """
    CLI WAMP methods.
    """

    def _result_callback(self, result):

        if 'session' in result:
            print(result['session'].get('status', 'failed'))
            del result['session']

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

        failure_message = ""
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

    @inlineCallbacks
    def onRun(self, details):

        # Define method uri
        uri = self.package_config['uri']
        del self.package_config['uri']

        # Get the session
        session_config = self.session_config

        # Call method and wait for results
        deferred = self.call(uri, session=session_config(), **self.package_config)
        deferred.addCallback(self._result_callback)
        deferred.addErrback(self._error_callback)

        yield True
