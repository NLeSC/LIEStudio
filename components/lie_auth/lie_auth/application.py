# -*- coding: utf-8 -*-

"""
file: wamp_services.py

WAMP service methods the module exposes.
"""

import datetime
import json

import base64
import copy
from autobahn import wamp
from autobahn.wamp.exception import ApplicationError
from jwt import encode as jwt_encode, decode as jwt_decode, DecodeError, ExpiredSignatureError
from oauthlib import oauth2
from oauthlib.common import generate_client_id as generate_secret
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue, Deferred

from mdstudio.api.endpoint import endpoint
from mdstudio.component.impl.core import CoreComponentSession
from mdstudio.deferred.chainable import chainable

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from mdstudio.utc import now
from mdstudio.db.model import Model
from .util import check_password, logging, ip_domain_based_access
from .oauth.request_validator import OAuthRequestValidator
from .authorizer import Authorizer


class AuthComponent(CoreComponentSession):
    """
    User management WAMP methods.
    """

    def pre_init(self):
        self.oauth_client = oauth2.BackendApplicationClient('auth')
        self.component_waiters.append(CoreComponentSession.ComponentWaiter(self, 'db'))
        self.component_waiters.append(CoreComponentSession.ComponentWaiter(self, 'schema'))
        self.status_list = {'auth': True}

    def on_init(self):
        self.db_initialized = False
        self.authorizer = Authorizer()

    def onInit(self, **kwargs):
        self.oauth_backend_server = oauth2.BackendApplicationServer(OAuthRequestValidator(self))

        self.autolog = False
        self.autoschema = False

        # TODO: check this before accessing the DB


        # # TODO: make this a dict of  {vendor}.{namespace}: [urilist] for faster lookup
        # self.registrations = []

    @chainable
    def _on_join(self):
        self.jwt_key = generate_secret()
        yield super(AuthComponent, self)._on_join()

    def onExit(self, details=None):
        """
        User component exit routines

        Terminate all active sessions on component shutdown

        :param settings: global and module specific settings
        :type settings:  :py:class:`dict` or :py:class:`dict` like object
        :return:         successful exit sequence
        :rtype:          bool
        """
        pass

    @wamp.register(u'mdstudio.auth.endpoint.sign', options=wamp.RegisterOptions(details_arg='details'))
    def sign_claims(self, claims, details=None):
        role = details.caller_authrole

        if not isinstance(claims, dict):
            raise TypeError()

        if role in ['db', 'schema', 'auth', 'logger']:
            claims['groups'] = ['mdstudio']
            claims['username'] = role
        else:
            raise NotImplementedError("Implement this")

        claims['exp'] = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)

        return jwt_encode(claims, self.jwt_key)

    @wamp.register(u'mdstudio.auth.endpoint.verify')
    def verify_claims(self, signed_claims):
        try:
            claims = jwt_decode(signed_claims, self.jwt_key)
        except DecodeError:
            return {'error': 'Could not verify user'}
        except ExpiredSignatureError:
            return {'expired': 'Request token has expired'}

        return {'claims': claims}

    @endpoint('mdstudio.auth.endpoint.ring0.set-status', {}, {})
    def ring0_set_status(self, request, claims=None):
        self.status_list[claims['username']] = request['status']

    @endpoint('mdstudio.auth.endpoint.ring0.get-status', {}, {})
    def ring0_get_status(self, request, claims=None):
        return self.status_list.get(request['component'], False)

    def authorize_request(self, uri, claims):
        if 'mdstudio' in claims['groups'] and uri.startswith('mdstudio.auth.endpoint.ring0'):
            return True

        return False

    @wamp.register(u'mdstudio.auth.endpoint.login')
    @inlineCallbacks
    def user_login(self, realm, authid, details):
        """
        Handles application authentication and authorization on the Crossbar
        WAMP session level by acting as the dynamic authorizer using any of
        the Crossbar supported authentication methods.

        For more information about crossbar authentication/authorization
        consult the online documentation at: http://crossbar.io/docs/Administration/

        This method also provides authentication based on IP/domain
        information in addition to the crossbar supported authentication
        methods.

        :param realm:   crossbar realm to connect to
        :type realm:    str
        :param authid:  authentication ID, usually username
        :type authid:   str
        :param details: additional details including authentication method
                        and transport details
        :type details:  :py:class:`dict`
        :return:        authentication response with the realm, user role and
                        user account info returned.
        :rtype:         :py:class:`dict` or False
        """

        authmethod = details.get(u'authmethod', None)

        # Resolve request domain
        domain = None
        if u'http_headers_received' in details:
            domain = details[u'http_headers_received'].get(u'host', None)
            details[u'domain'] = domain

        self.log.info('WAMP authentication request for realm: {realm}, authid: {authid}, method: {authmethod} domain: {domain}',
                      realm=realm, authid=authid, authmethod=authmethod, domain=domain)

        # Check for essentials (authid)
        if authid is None:
            raise ApplicationError('Authentication ID not defined')

        # Is the application only available for local users?
        if domain and self.package_config.get('only_localhost_access', False) and domain != 'localhost':
            raise ApplicationError('Access granted only to local users, access via domain {0}'.format(domain))

        # Is the domain blacklisted?
        black_list = self.package_config.get('domain-blacklist', [])
        if not ip_domain_based_access(domain, blacklist=black_list):
            logging.info('Access for domain {domain} blacklisted (pattern={blacklist})'.format(domain=domain, blacklist=black_list))
            raise ApplicationError('Access from domain {0} not allowed'.format(domain))

        username = authid.strip()
        user = yield self._get_user(username)

        # WAMP-ticket authetication
        if authmethod == u'ticket':
            is_valid = self._validate_user_login(user, username, details['ticket'])
            if is_valid:
                auth_ticket = {u'realm': realm, u'role': user['role'], u'extra': self._strip_unsafe_properties(user)}
            else:
                # Not a valid user, try  to find a matching client
                client = yield self._get_client(username)
                if client:
                    client['scope'] = ' '.join(client.pop('scopes'))
                    http_basic = self._http_basic_authentication(username, details['ticket'])
                    credentials = {u'client': client,
                                   u'http_basic': self._http_basic_authentication(client[u'clientId'], client[u'secret'])}

                    headers, body, status = self.oauth_backend_server.create_token_response(
                        u'mdstudio.auth.endpoint.login',
                        headers={u'Authorization': http_basic},
                        grant_type_for_scope=u'client_credentials',
                        credentials=credentials)

                    if status == 200:
                        user = {u'_id': client[u'_id']}
                        auth_ticket = {u'realm': realm, u'role': 'oauthclient', u'extra': {u'access_token': json.loads(body).get('accessToken')}}
                    else:
                        raise ApplicationError("com.example.invalid_ticket", "could not authenticate session")
                else:
                    raise ApplicationError("com.example.invalid_ticket", "could not authenticate session")

        # WAMP-CRA authentication
        elif authmethod == u'wampcra':
            if user:
                auth_ticket = {u'realm': realm, u'role': user['role'], u'extra': self._strip_unsafe_properties(user),
                               u'secret': user[u'password']}
            else:
                raise ApplicationError("com.example.invalid_ticket", "could not authenticate session")

        else:
            raise ApplicationError("No such authentication method known: {0}".format(authmethod))

        yield self._start_session(user[u'_id'], details.get(u'session', 0), auth_ticket[u'extra'].get('access_token'))

        # Log authorization
        self.log.info('Access granted. user: {user}', user=authid)

        returnValue(auth_ticket)

    # @endpoint(u'mdstudio.auth.endpoint.oauth.registerscopes', {}, {}, match='prefix')
    # @inlineCallbacks
    # def register_scopes(self, request, **kwargs):
    #     for scope in request['scopes']:
    #         # update/insert the uri scope
    #         yield Model(self, 'scopes').update_one(scope, {'$set': scope}, True)
    #
    #     returnValue(None)

    @wamp.register(u'mdstudio.auth.endpoint.authorize.admin')
    def authorize_admin(self, session, uri, action, options):
        role = session.get('authrole')
        authid = session.get('authid')

        authorization = False

        if action in ('call', 'subscribe', 'publish'):
            # Allow admin to call, subscribe and publish on any uri
            # TODO: possibly restrict this
            authorization = {'allow': True}

        if not authorization:
            self.log.warn('WARNING: {} is not authorized for {} on {}'.format(authid, action, uri))
        else:
            if 'disclose' not in authorization:
                authorization['disclose'] = False

            if uri.startswith('mdstudio.auth.endpoint.oauth'):
                authorization['disclose'] = True

            self._store_action(uri, action, options)

        return authorization

    @wamp.register(u'mdstudio.auth.endpoint.authorize.ring0')
    def authorize_ring0(self, session, uri, action, options):
        role = session.get('authrole')

        authorization = self.authorizer.authorize_ring0(uri, action, role)

        if not authorization:
            self.log.warn('WARNING: {} is not authorized for {} on {}'.format(role, action, uri))
        else:
            if 'disclose' not in authorization:
                authorization['disclose'] = False

            self._store_action(uri, action, options)

        return authorization


    @wamp.register(u'mdstudio.auth.endpoint.authorize.oauth')
    @inlineCallbacks
    def authorize_oauth(self, session, uri, action, options):
        role = session.get('authrole')

        authid = session.get('authid')

        authorization = False

        client = yield self._get_client(authid)
        session = yield self._get_session(session.get('session'))
        scopes = self.authorizer.oauthclient_scopes(uri, action, authid)

        headers = {'access_token': session['accessToken']}
        valid, r = self.oauth_backend_server.verify_request(uri, headers=headers, scopes=[scope for scope in scopes])

        valid = yield valid

        if valid:
            authorization = {'allow': True}

        if not authorization:
            self.log.warn('WARNING: {} is not authorized for {} on {}'.format(authid, action, uri))
        else:
            if 'disclose' not in authorization:
                authorization['disclose'] = False

            self._store_action(uri, action, options)

        returnValue(authorization)

    @wamp.register(u'mdstudio.auth.endpoint.authorize.public')
    def authorize_public(self, session, uri, action, options):
        #  TODO: authorize public to view unprotected resources
        authorization = False

        returnValue(authorization)

    @wamp.register(u'mdstudio.auth.endpoint.authorize.user')
    def authorize_user(self, session, uri, action, options):
        # TODO: authorize users to view (parts of) the web interface and to create OAuth clients on their group/user
        authorization = False

        returnValue(authorization)

    @endpoint(u'mdstudio.auth.endpoint.oauth.client.create', 'oauth/client/client-request', 'oauth/client/client-response')
    @inlineCallbacks
    def create_oauth_client(self, request, details=None):
        user = yield self._get_user(details.caller_authid)

        # TODO: check if user is permitted to access the requested scopes before creating the client
        clientInfo = copy.deepcopy(request)
        clientInfo['userId'] = user['_id']
        clientInfo['clientId'] = generate_secret()
        clientInfo['secret'] = generate_secret()

        yield Model(self, 'clients').insert_one(clientInfo)

        returnValue({
            'id': clientInfo['clientId'],
            'secret': clientInfo['secret']
        })

    @endpoint(u'mdstudio.auth.endpoint.oauth.client.getusername', {}, {})
    @inlineCallbacks
    def get_oauth_client_username(self, request):
        client = yield self._get_client(request['clientId'])

        if client:
            user = yield self._get_user({'_id': client['userId']})

            returnValue({'username': user['username']})
        else:
            returnValue({})

    @wamp.register(u'mdstudio.auth.endpoint.logout', options=wamp.RegisterOptions(details_arg='details'))
    @inlineCallbacks
    def user_logout(self, details):
        """
        Handles the user logout process by:
        - Retrieve user based on session_id

        :param session_id: user unique session ID
        :type session_id:  int
        """

        user = yield self._get_user(details.get('authid'))
        if user:
            self.log.info('Logout user: {0}, id: {1}'.format(user['username'], user['_id']))

            ended = yield self._end_session(user['uid'], details.get('session'))
            if ended:
                returnValue('{0} you are now logged out'.format(user['username']))

        returnValue('Unknown user, unable to logout')

    @wamp.register(u'mdstudio.auth.endpoint.retrieve')
    def retrieve_password(self, email):
        """
        Retrieve a forgotten password by email
        This will reset the users password and
        send a temporary password by email.

        :param email: user account email
        """

        raise Exception

    # # TODO: improve and register this method, with json schemas
    # @inlineCallbacks
    # def create_user(self, userdata, required=['username', 'email']):
    #     """
    #     Create new user and add to database
    #     """
    #
    #
    #     # TODO: handle the following section with json schema
    #     # ----------------------------------------------------------------------------
    #     user_template = copy.copy(USER_TEMPLATE)
    #
    #     # Require at least a valid username and email
    #     for param in required:
    #         if not userdata.get(param, None):
    #             self.log.error('Unable to create new user. Missing "{0}"'.format(param))
    #             returnValue({})
    #
    #     # If no password, create random one
    #     if not userdata.get('password', None):
    #         random_pw = generate_password()
    #         user_template['password'] = hash_password(random_pw)
    #
    #     user_template.update(userdata)
    #     # ----------------------------------------------------------------------------
    #
    #     # Username and email should not be in use
    #     user = yield self._get_user(userdata['username'])
    #     if user:
    #         self.log.error('Username {0} already in use'.format(userdata['username']))
    #         returnValue({})
    #
    #     user = yield self._get_user({'email': userdata['email']})
    #     if user:
    #         self.log.error('Email {0} already in use'.format(userdata['email']))
    #         returnValue({})
    #
    #     # Add the new user to the database
    #     result = yield Model(self, 'users').insert_one(user_template)
    #     if result:
    #         self.log.debug('Added new user. user: {username}, id: {id}', id=result, **user_template)
    #     else:
    #         self.log.error('Unable to add new user to database')
    #         returnValue({})
    #
    #     returnValue(user_template)

    # # TODO: expose and secure this
    # def remove_user(self, userdata):
    #     """
    #     Remove a user from the database
    #
    #     :param userdata: PyMongo style database query
    #     :type userdata:  :py:class:`dict`
    #     """
    #
    #     user = self.get_user(userdata)
    #     if not user:
    #         self.log.error('No such user to remove: {0}'.format(
    #             ' '.join(['{0},{1}'.format(*item) for item in userdata.items()])))
    #         return False
    #     else:
    #         self.log.info('Removing user "{username}", with uid {uid} from database'.format(**user))
    #         db['users'].delete_one(user)
    #
    #     return True

    def _validate_user_login(self, user, username, password):
        """
        Validate login attempt for user with password

        :param username: username to check
        :type username:  string
        :param password: password to check
        :type password:  string
        :rtype:          bool
        """

        password = password.strip()

        check = False
        if user:
            check = check_password(user['password'], password)
        else:
            self.log.debug('No such user')

        self.log.info('{status} login attempt for user: {user}',
                      status='Correct' if check else 'Incorrect', user=username)

        return check

    @inlineCallbacks
    def _get_user(self, filter):
        if type(filter) is not dict:
            filter = {'username': filter}

        res = yield Model(self, 'users').find_one(filter)

        returnValue(res)

    @inlineCallbacks
    def _get_client(self, client_id):
        client = yield Model(self, 'clients').find_one({'clientId': client_id})

        if client:
            returnValue(client)
        else:
            returnValue(None)

    def _http_basic_authentication(self, username, password):
        # mimic HTTP basic authentication
        # concatenate username and password with a colon
        http_basic = u'{}:{}'.format(username, password)
        # encode into an octet sequence (bytes)
        http_basic = http_basic.encode('utf_8')
        # encode in base64
        http_basic = base64.encodebytes(http_basic)

        return http_basic.decode('utf_8')

    @inlineCallbacks
    def _start_session(self, user_id, session_id, access_token):
        self.log.debug('Open session: {0} for user {1}'.format(session_id, user_id))
        res = yield Model(self, 'sessions').insert_one({'userId': user_id, 'sessionId': session_id, 'accessToken': access_token})
        returnValue(res)

    @inlineCallbacks
    def _get_session(self, session_id):
        res = yield Model(self, 'sessions').find_one({'sessionId': session_id})
        returnValue(res)

    @inlineCallbacks
    def _end_session(self, user_id, session_id):
        res = yield Model(self, 'sessions').delete_one({'userId': user_id, 'sessionId': session_id})
        returnValue(res > 0)

    def _strip_unsafe_properties(self, _user):
        user = _user.copy()

        for entry in self.package_config.get('unsafe_properties'):
            if entry in user:
                del user[entry]

        return user

    # @inlineCallbacks
    # def _retrieve_password(self, email):
    #     """
    #     Retrieve password by email
    #
    #     The email message template for user account password retrieval
    #     is stored in the self._password_retrieval_message_template variable.
    #
    #     * Locates the user in the database by email which should be a
    #       unique and persistent identifier.
    #     * Generate a new random password
    #     * Send the new password to the users email once. If the email
    #       could not be send, abort the procedure
    #     * Save the new password in the database.
    #
    #     :param email: email address to search user for
    #     :type email:  string
    #     """
    #
    #     user = yield self._get_user({'email': email})
    #     if not user:
    #       self.log.info('No user with email {0}'.format(email))
    #       return
    #
    #     new_password = generate_password()
    #     user['password'] = hash_password(new_password)
    #     self.log.debug('New password {0} for user {1} send to {2}'.format(new_password, user, email))
    #
    #     with Email() as email:
    #       email.send(
    #         email,
    #         self._password_retrieval_message_template.format(password=new_password, user=user['username']),
    #         'Password retrieval request for LIEStudio'
    #       )
    #       res = yield Model(self, 'users').update_one({'_id': user['_id']}, {'password': new_password})
    #
    #     returnValue(user)

    def _store_action(self, uri, action, options):
        registration = Model(self, 'registration_info')

        n = now().isoformat()

        if action == 'register':
            match = options.get('match', 'exact')

            @inlineCallbacks
            def update_registration():
                upd = yield registration.update_one(
                    {
                        'uri': uri,
                        'match': match
                    },
                    {
                        '$inc': {
                            'registrationCount': 1
                        },
                        '$set': {
                            'latestRegistration': n
                        },
                        '$setOnInsert': {
                            'uri': uri,
                            'firstRegistration': n,
                            'match': match
                        }
                    },
                    upsert=True,
                    date_fields=['update.$set.latestRegistration', 'update.$setOnInsert.firstRegistration']
                )

            # We cannot be sure the DB is already up, possibly wait
            yield DBWaiter(self, update_registration).run()
        elif action == 'call':
            @inlineCallbacks
            def update_registration():
                id = yield self.call(u'wamp.registration.match', uri)
                if id:
                    reg_info = yield self.call(u'wamp.registration.get', id)
                    yield registration.update_one(
                        {
                            'uri': reg_info['uri'],
                            'match': reg_info['match']
                        },
                        {
                            '$inc': {
                                'callCount': 1
                            },
                            '$set': {
                                'latestCall': now
                            }
                        },
                        date_fields=['update.$set.latestCall']
                    )

            # We cannot be sure the DB is already up, possibly wait
            yield DBWaiter(self, update_registration).run()

class DBWaiter(object):
    def __init__(self, session, callback):
        self.session = session
        self.callback = callback
        self.unsub = Deferred()
        self.called = False
        self.sub = None

        self.unsub.addCallback(self._unsubscribe)

    @inlineCallbacks
    def run(self):
        if not self.session.db_initialized:
            self.sub = yield self.session.on_event(self._callback_wrapper, u'mdstudio.db.endpoint.events.online')

            reactor.callLater(0.25, self._check_called)
        else:
            yield self.callback()
            self.called = True

    @inlineCallbacks
    def _callback_wrapper(self, event):
        yield self.callback()
        self.called = True
        self.unsub.callback(True)
        self.session.db_initialized = True

    def _unsubscribe(self, event=None):
        self.sub.unsubscribe()

    def _check_called(self):
        if self.session.db_initialized:
            if not self.called:
                self._callback_wrapper(True)
        else:
            reactor.callLater(0.25, self._check_called)
