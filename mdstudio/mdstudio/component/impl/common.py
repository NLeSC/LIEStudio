import inspect
import json
import os
import re
from collections import OrderedDict
from copy import deepcopy

import yaml
from autobahn.twisted.wamp import ApplicationSession
from autobahn.wamp import PublishOptions, ApplicationError
from twisted.python.failure import Failure

from mdstudio.api.api_result import APIResult
from mdstudio.api.context import UserContext, GroupRoleContext, GroupContext, ContextManager
from mdstudio.api.converter import convert_obj_to_json
from mdstudio.api.exception import CallException
from mdstudio.api.request_hash import request_hash
from mdstudio.api.schema import validate_json_schema
from mdstudio.collection import merge_dicts, dict_property
from mdstudio.deferred.chainable import chainable, Chainable
from mdstudio.deferred.return_value import return_value
from mdstudio.logging.impl.session_observer import SessionLogObserver
from mdstudio.logging.log_type import LogType
from mdstudio.logging.logger import Logger


class CommonSession(ApplicationSession):
    class Config(object):
        class Static(dict):
            vendor = dict_property('vendor')
            component = dict_property('component')

        class Session(dict):
            username = dict_property('username')
            password = dict_property('password')
            realm = dict_property('realm')
            role = dict_property('role')
            session_id = dict_property('session_id')

        def __init__(self):
            self.static = self.Static()
            self.session = self.Session()
            self.settings = {}

        def __getitem__(self, attr):
            return getattr(self, attr)

        def to_dict(self):
            return {
                'static': self.static,
                'session': self.session,
                'settings': self.settings
            }

    def __init__(self, config=None):
        self.log = Logger(namespace=self.__class__.__name__)
        self.log_type = LogType.User
        self.default_call_context = None

        self.component_config = self.Config()
        self.function_scopes = self.extract_custom_scopes()  # @todo: register these
        self.load_environment(self.session_env_mapping, attribute='session')

        self.load_settings()

        self.pre_init()

        self.log_collector = SessionLogObserver(self, self.log_type)

        super(CommonSession, self).__init__(config)

        # load config from env/file, check with schema
        self.validate_settings()

        if config:
            config.realm = u'{}'.format(self.component_config.session.realm)

        context = self.component_config.session.get('context', None)

        if context is None:
            call_context = UserContext(self)
        else:
            if 'role' in context:
                call_context = GroupRoleContext(self, context['group'], context['role'])
            else:
                call_context = GroupContext(self, context['group'])

        self.default_call_context = call_context

        self.on_init()

    def pre_init(self):
        pass

    def on_init(self):
        pass

    def on_run(self):
        pass

    def on_exit(self):
        pass

    def authorize_request(self, uri, claims):
        self.log.warn("Authorization for {uri} should be implemented in the component", uri=uri)

        return False

    def default_context(self):
        return ContextManager({'call_context': self.default_call_context})

    def user_context(self):
        return ContextManager({'call_context': UserContext(self)})

    def group_context(self, group_name):
        return ContextManager({'call_context': GroupContext(self, group_name)})

    def grouprole_context(self, group_name, group_role):
        return ContextManager({'call_context': GroupRoleContext(self, group_name, group_role)})

    # noinspection PyMethodOverriding
    @chainable
    def call(self, procedure, request, claims=None, **kwargs):
        claims = ContextManager.get('call_context').get_claims(claims)
        claims['uri'] = procedure
        claims['action'] = 'call'

        request = deepcopy(request)
        convert_obj_to_json(request)

        claims['requestHash'] = request_hash(request)

        signed_claims = yield super(CommonSession, self).call(u'mdstudio.auth.endpoint.sign', claims)

        if signed_claims is None:
            claims.pop('requestHash')
            raise CallException('Claims were not signed. You are not authorized for signing: \n{}'.format(json.dumps(claims, indent=2)))

        def make_original_call():
            return Chainable(super(CommonSession, self).call(u'{}'.format(procedure), request, signed_claims=signed_claims, **kwargs))

        try:
            result = yield make_original_call()
        except ApplicationError:
            result = APIResult(error='Call to {uri} failed'.format(uri=procedure))

        if 'expired' in result:
            signed_claims = yield super(CommonSession, self).call(u'mdstudio.auth.endpoint.sign', claims)

            try:
                result = yield make_original_call()
            except ApplicationError:
                result = APIResult(error='Call to {uri} failed'.format(uri=procedure))

        if 'expired' in result:
            raise CallException(result['expired'])

        if 'error' in result:
            raise CallException(result['error'])

        if 'warning' in result:
            self.log.warn(result['warning'])

        return_value(result.get('data', None))

    @chainable
    def publish(self, topic, claims=None, options=None):
        claims = ContextManager.get('call_context').get_claims(claims)

        signed_claims = yield super(CommonSession, self).call(u'mdstudio.auth.endpoint.sign', claims)

        options = options or PublishOptions(acknowledge=True, exclude_me=False)

        result = yield super(CommonSession, self).publish(topic, signed_claims=signed_claims, options=options)  # type: Publication

        return_value(result)

    def subscribe(self, handler, topic, options=None):
        @chainable
        def _handler(*args, **kwargs):
            signed_claims = kwargs.pop('signed_claims', None)
            assert signed_claims, "Subscribe was called without claims"
            claims = yield super(CommonSession, self).call('mdstudio.auth.endpoint.verify', signed_claims)

            if not ('error' in claims or 'expired' in claims):
                claims = claims['claims']

                if not self.authorize_request(topic, claims):
                    self.log.warn("Unauthorized publish to {topic}", topic=topic)
                else:
                    return_value((yield handler(*args, claims=claims, **kwargs)))

        return super(CommonSession, self).subscribe(_handler, topic, options)

    def event(self, topic, *args, **kwargs):
        return super(CommonSession, self).publish(topic, *args, **kwargs)

    def on_event(self, handler, topic, options=None):
        return super(CommonSession, self).subscribe(handler, topic, options)

    @chainable
    def _on_join(self):
        yield self.upload_schemas()

        yield self.on_run()

        yield self.log_collector.start_flushing(self)

    @chainable
    def on_join(self):
        failures = 0
        successful = 0

        registrations = yield self.register(self)
        for _, endpoint in self.__class__.__dict__.items():
            from mdstudio.api.endpoint import WampEndpoint
            if isinstance(endpoint, WampEndpoint):
                yield endpoint.input_schema.flatten(self)
                yield endpoint.output_schema.flatten(self)
                for s in endpoint.claim_schemas:
                    yield s.flatten(self)

                endpoint.set_instance(self)
                try:
                    yield endpoint.register()
                    successful += 1
                except:
                    failures += 1

        yield self._on_join()

        for r in registrations:
            if isinstance(r, Failure):
                self.log.info("ERROR: {class_name}: {message}", class_name=self.class_name(), message=r.value)
                failures += 1
            else:
                successful += 1

        if failures > 0:
            self.log.info("ERROR {class_name}: failed to register {procedures} procedures", procedures=failures,
                          class_name=self.class_name())

        self.log.info("{class_name}: {procedures} procedures successfully registered",
                      procedures=successful, class_name=self.class_name())

    @chainable
    def onJoin(self, details):
        yield self.flatten_endpoint_schemas()

        # Update session config, they may have been changed by the application authentication method
        for var, details_var in self.session_update_vars.items():
            self.component_config.session[var] = getattr(details, details_var)

        yield self.on_join()

    # @chainable
    # def on_leave(self, details):
    #     self.log.info('{class_name} is leaving realm {realm}', class_name=self.class_name(),
    #                   realm=self.component_config.session.realm)
    #
    #     yield self.on_exit()
    #
    #     yield super(CommonSession, self).onLeave(details)
    #     yield self.disconnect()
    #
    # onLeave = on_leave

    def add_env_var_from_config(self, session_var, env_vars, attribute=None, default=None, converter=None, extract=os.getenv):
        if not attribute:
            attribute = 'settings'
        if not isinstance(env_vars, list):
            env_vars = [env_vars]

        for var in env_vars:
            env_var = extract(var)

            if env_var:
                if converter:
                    self.component_config[attribute][session_var] = converter(env_var)
                else:
                    self.component_config[attribute][session_var] = env_var
                return

        if default:
            self.component_config[attribute][session_var] = default

    def load_environment(self, mapping, attribute=None):
        for session_var, env_vars in mapping.items():
            converter = env_vars[2] if len(env_vars) == 3 else None
            self.add_env_var_from_config(session_var, env_vars[0], attribute, default=env_vars[1], converter=converter)

    def load_settings(self):
        for file in self.settings_files():
            settings_file = os.path.join(self.component_root_path(), file)

            if os.path.isfile(settings_file):
                with open(settings_file, 'r') as f:
                    merge_dicts(self.component_config.to_dict(), yaml.safe_load(f))

    def validate_settings(self):
        for path in self.settings_schemas():
            if os.path.isfile(path):
                with open(path, 'r') as f:
                    settings_schema = json.load(f)

                validate_json_schema(settings_schema, self.component_config.to_dict())

    def extract_custom_scopes(self):
        function_scopes = []

        # Scan for scopes on registrations
        for key, f in self.__class__.__dict__.items():
            try:
                function_scopes.append({
                    'scope': f.scope,
                    'uri': f.uri
                })
            except AttributeError:
                pass

        return function_scopes

    @chainable
    def upload_schemas(self):
        schemas = {
            'endpoints': self._collect_schemas('endpoints'),
            'resources': self._collect_schemas('resources')
        }

        if schemas['endpoints'] or schemas['resources']:
            try:
                with self.group_context(self.component_config.static.vendor):
                    yield self.call(u'mdstudio.schema.endpoint.upload', {
                        'component': self.component_config.static.component,
                        'schemas': schemas
                    }, claims={'vendor': self.component_config.static.vendor})
            except CallException as e:
                self.log.error('Error during schema uploading: {message}', message=str(e))
            else:
                self.log.info('Uploaded schemas for {package}', package=self.class_name())

    def _collect_schemas(self, *sub_paths):
        schemas = []
        root_dir = os.path.join(self.component_schemas_path(), *sub_paths)

        if os.path.isdir(root_dir):
            for root, dirs, files in os.walk(root_dir):
                if files:
                    for file in files:
                        path = os.path.join(root, file)
                        rel_path = os.path.relpath(path, root_dir).replace('\\', '/')
                        path_decomposition = re.match('(.*?)\\.?(v\\d+)?\\.json', rel_path)

                        with open(path, 'r') as f:
                            schema_entry = {
                                'schema': json.load(f),
                                'name': path_decomposition.group(1)
                            }

                        if path_decomposition.group(2):
                            schema_entry['version'] = int(path_decomposition.group(2).strip('v'))

                        schemas.append(schema_entry)

        return schemas

    @chainable
    def flatten_endpoint_schemas(self):
        # Scan for input/output schemas on registrations
        for key, f in self.__class__.__dict__.items():
            func = getattr(self, key)
            try:
                yield func.input_schema.flatten(self)
            except AttributeError:
                pass
            try:
                yield func.output_schema.flatten(self)
            except AttributeError:
                pass
            try:
                yield func.claims_schema.flatten(self)
            except AttributeError:
                pass

    # @todo
    @chainable
    def _register_scopes(self):
        return_value(True)
        if self.function_scopes:
            res = yield self.call(
                'mdstudio.auth.endpoint.oauth.registerscopes.{}'.format(self.component_info.get('namespace')),
                {'scopes': self.function_scopes})

            self.log.info('Registered {count} scopes for {package}', count=len(self.function_scopes),
                          package=self.component_info['package_name'])

    @property
    def session_env_mapping(self):
        return OrderedDict([
            ('username', (['MDSTUDIO_USERNAME'], None)),
            ('password', (['MDSTUDIO_PASSWORD'], None)),
            ('realm', (['MDSTUDIO_REALM'], 'mdstudio'))
        ])

    @property
    def session_update_vars(self):
        return OrderedDict([
            ('username', 'authid'),
            ('role', 'authrole'),
            ('session_id', 'session')
        ])

    @classmethod
    def class_name(cls):
        return cls.__name__

    @classmethod
    def component_root_path(cls):
        return os.path.abspath(os.path.dirname(os.path.dirname(inspect.getfile(cls))))

    @classmethod
    def component_schemas_path(cls):
        return os.path.abspath(os.path.join(os.path.dirname(inspect.getfile(cls)), 'schemas'))

    @classmethod
    def mdstudio_root_path(cls):
        return os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(inspect.getfile(CommonSession)), '..', '..', '..')))

    @classmethod
    def mdstudio_schemas_path(cls):
        return os.path.abspath(os.path.join(os.path.dirname(inspect.getfile(CommonSession)), '..', '..', 'schemas'))

    @classmethod
    def settings_files(cls):
        extensions = ['json', 'yml']
        prefixes = ['', '.']
        envs = cls.environments()
        if '' not in envs:
            envs.insert(0, '')
        result = []
        for env in envs:
            if env:
                env = '.{}'.format(env)
            for ext in extensions:
                for p in prefixes:
                    result.append('{}settings{}.{}'.format(p,env,ext))
        return result

    @classmethod
    def environments(cls):
        return os.getenv('MD_CONFIG_ENVIRONMENTS', '').split(',')

    @classmethod
    def settings_schemas(cls):
        return [os.path.join(cls.component_schemas_path(), 'settings.json'),
                os.path.join(cls.mdstudio_schemas_path(), 'settings.json')]
