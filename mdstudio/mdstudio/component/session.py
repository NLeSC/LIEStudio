import json

from mdstudio.api.scram import SCRAM
from mdstudio.cache.impl.connection import GlobalCache
from mdstudio.component.impl.common import CommonSession
from mdstudio.db.connection_type import ConnectionType
from mdstudio.db.impl.connection import GlobalConnection
from mdstudio.deferred.chainable import chainable
from mdstudio.deferred.return_value import return_value
from mdstudio.session import GlobalSession


class ComponentSession(CommonSession):
    # type: IDatabase
    db = None

    def on_connect(self):
        auth_methods = [u'wampcra']
        authid, self.client_nonce = SCRAM.authid(self.component_config.session.username)
        auth_role = u'user'

        self.join(self.config.realm, authmethods=auth_methods, authid=authid, authrole=auth_role)

    onConnect = on_connect

    def on_challenge(self, challenge):
        server_nonce = json.loads(challenge.extra['challenge']).get('session')
        client_nonce = self.client_nonce

        self.auth_message = SCRAM.auth_message(client_nonce, server_nonce)

        _, _, salted_password = SCRAM.salted_password(self.component_config.session.password, challenge.extra['salt'], challenge.extra['iterations'])
        client_key = SCRAM.client_key(salted_password)
        self.server_key = SCRAM.server_key(salted_password)
        stored_key = SCRAM.stored_key(client_key)
        client_signature = SCRAM.client_signature(stored_key, self.auth_message)

        client_proof = SCRAM.client_proof(client_key, client_signature)

        return SCRAM.binary_to_str(client_proof)

    onChallenge = on_challenge

    @chainable
    def on_join(self):
        yield super(ComponentSession, self).on_join()

        # notify that this is our session
        GlobalSession(self)

        self.db = GlobalConnection.get_wrapper(ConnectionType.User)
        self.cache = GlobalCache.get_wrapper(ConnectionType.User)

    @chainable
    def onJoin(self, details):
        server_proof = SCRAM.str_to_binary(details.authextra['serverProof'])
        server_signature = SCRAM.server_signature(self.server_key, self.auth_message)

        if server_proof != server_signature:
            self.log.error('Server not authenticated')
            yield self.leave()
            
        yield super(ComponentSession, self).onJoin(details)

    @chainable
    def flush_logs(self, logs):
        with self.default_context() as c:
            result = yield self.call(u'mdstudio.logger.endpoint.push-logs', {'logs': logs}, c.get('call_context').get_log_claims())

        return_value(result)
