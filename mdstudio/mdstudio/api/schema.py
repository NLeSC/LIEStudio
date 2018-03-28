import json

import jsonschema
import os
import re
import six
from jsonschema import FormatChecker, Draft4Validator

from mdstudio.api.exception import RegisterException
from mdstudio.api.singleton import Singleton
from mdstudio.deferred.chainable import chainable
from mdstudio.deferred.return_value import return_value


class ISchema(object):
    def __init__(self):
        self.cached = {}

    def _retrieve_local(self, base_path, schema_path, versions=None):
        if versions is not None:
            if not isinstance(versions, (list, set)):
                versions = [versions]

            for version in versions:
                path = os.path.join(base_path, '{}.v{}.json'.format(schema_path, version))

                with open(path, 'r') as f:
                    self.cached[version] = json.load(f)
        else:
            path = os.path.join(base_path, '{}.json'.format(schema_path))

            with open(path, 'r') as f:
                self.cached[1] = json.load(f)

    @chainable
    def _recurse_subschemas(self, schema, session):
        success = True

        if isinstance(schema, dict):
            ref = schema.pop('$ref', None)

            if ref:
                ref_decomposition = re.match(r'(\w+)://(.+)', ref)
                if not ref_decomposition:
                    raise RegisterException('$ref value in the schema must hold a valid resource uri. This may be given as '
                                            'resource://<uri>, endpoint://<uri>, or https://<url>, you specified "{}"'.format(ref))
                subschema = self._schema_factory(ref_decomposition.group(1), ref_decomposition.group(2))

                if (yield subschema.flatten(session)):
                    schema.update(subschema.to_schema())
                else:
                    success = False

            if success:
                for k, v in schema.items():
                    recursed = yield self._recurse_subschemas(v, session)

                    if not recursed['success']:
                        success = False
                        break

                    schema[k] = recursed['schema']
        elif isinstance(schema, list):
            for v in schema:
                success = success and (yield self._recurse_subschemas(v, session))['success']

        return_value({
            'schema': schema,
            'success': success
        })

    @staticmethod
    def _schema_factory(schema_type, schema_path):
        factory_dict = {
            'resource': ResourceSchema,
            'mdstudio': MDStudioSchema,
            'endpoint': EndpointSchema,
            'https': HttpsSchema,
            'http': HttpsSchema
        }
        if schema_type not in factory_dict:
            raise RegisterException('You tried to specify an unknown schema type. '
                                    'Valid schemas are resource://<uri>, endpoint://<uri> and https://<url>. '
                                    'We got "{}" as schema type'.format(schema_type))

        return factory_dict[schema_type](schema_path)

    def to_schema(self):
        if not self.cached:
            raise NotImplementedError("This schema has not been or could not be retrieved.")

        if len(self.cached) > 1:
            return {
                'oneOf': list(self.cached.values())
            }
        else:
            return six.next(six.itervalues(self.cached))


class InlineSchema(ISchema):
    def __init__(self, schema):
        super(InlineSchema, self).__init__()
        self.schema = schema

    def flatten(self, session=None):
        return self._recurse_subschemas(self.schema, session)

    def to_schema(self):
        return self.schema


class HttpsSchema(ISchema):
    def __init__(self, uri):
        super(HttpsSchema, self).__init__()
        self.uri = 'https://{}'.format(uri)

    def flatten(self, session=None):
        return True

    def to_schema(self):
        return {'$ref': self.uri}


class EndpointSchema(ISchema):
    type_name = 'endpoint'

    def __init__(self, uri, versions=None):
        super(EndpointSchema, self).__init__()
        uri_decomposition = re.match(r'([\w/\-]+?)(/((v?\d+,?)*))?$', uri)
        if not uri_decomposition:
            raise RegisterException('An {0} schema uri must be in the form "{0}://<schema path>(/v<versions>), '
                                    'where <versions> is a comma separated list of version numbers. Only alphanumberic, and "/_-"'
                                    ' characters are supported. We got "endpoint://{1}".'.format(self.type_name, uri))
        self.schema_path = uri_decomposition.group(1)

        uri_versions = uri_decomposition.group(3)
        self.versions = versions or ([int(v) for v in uri_versions.replace('v', '').split(',')] if uri_versions else [1])

        self.schema_subdir = 'endpoints'

    @chainable
    def flatten(self, session=None):
        # type: (CommonSession) -> bool
        if self.cached:
            return_value(True)

        ldir = self.search_dir(session)
        if self.schema_subdir:
            ldir = os.path.join(ldir, self.schema_subdir)

        try:
            self._retrieve_local(ldir, self.schema_path, self.versions)
        except IOError as ex:
            raise RegisterException('Tried to access schema "{}/{}" with versions {}, '
                                    'but the schema was not found:\n{}'.format(ldir, self.schema_path, self.versions, str(ex)))

        success = True

        for version, schema in self.cached.items():
            flattened = yield self._recurse_subschemas(schema, session)
            self.cached[version] = flattened['schema']

            if not flattened['success']:
                success = False
                break

        if not success:
            self.cached = {}

        return_value(success)

    def search_dir(self, session):
        return session.component_schemas_path()


class MDStudioSchema(EndpointSchema):
    schema_subdir = None
    type_name = 'mdstudio'


class ClaimSchema(EndpointSchema):
    type_name = 'claims'

    def __init__(self, uri, versions=None):
        super(ClaimSchema, self).__init__(uri, versions)
        self.schema_subdir = 'claims'


@six.add_metaclass(Singleton)
class MDStudioClaimSchema(object):
    def __init__(self, session):
        with open(os.path.join(session.mdstudio_schemas_path(), 'claims.v1.json'), 'r') as base_claims_file:
            self.schema = json.load(base_claims_file)

    def to_schema(self):
        return self.schema

    def flatten(self, session):
        return True


class ResourceSchema(ISchema):
    def __init__(self, uri, versions=None):
        super(ResourceSchema, self).__init__()
        uri_decomposition = re.match(r'([\w\-]+)/([\w\-]+)/([\w/\-]+?)(/((v?\d+,?)*))?$', uri)
        if not uri_decomposition:
            raise RegisterException(
                'An resource schema uri must be in the form "resource://<vendor>/<component>/<schema path>(/v<versions>), '
                'where <versions> is a comma separated list of version numbers. Only alphanumberic, and "/_-" characters are supported. '
                'We got "resource://{}".'.format(uri))
        self.vendor = uri_decomposition.group(1)
        self.component = uri_decomposition.group(2)
        self.schema_path = uri_decomposition.group(3)

        uri_versions = uri_decomposition.group(5)

        self.versions = versions or ([int(v) for v in uri_versions.replace('v', '').split(',')] if uri_versions else [1])

    @chainable
    def flatten(self, session=None):
        # type: (CommonSession) -> bool
        if self.cached:
            return_value(True)

        if session.component_config.static.vendor == self.vendor and session.component_config.static.component == self.component:
            self._retrieve_local(os.path.join(session.component_schemas_path(), 'resources'), self.schema_path, self.versions)
        else:
            yield self._retrieve_wamp(session)

        success = True

        for version, schema in self.cached.items():
            flattened = yield self._recurse_subschemas(schema, session)
            self.cached[version] = flattened['schema']

            if not flattened['success']:
                success = False
                break

        if not success:
            self.cached = {}

        return_value(success)

    @chainable
    def _retrieve_wamp(self, session):
        for version in self.versions:
            self.cached[version] = yield session.call('mdstudio.schema.endpoint.get', {
                'name': self.schema_path,
                'version': version,
                'component': self.component,
                'type': 'resource'
            }, claims={
                'vendor': self.vendor
            })


def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

        for error in validate_properties(validator, properties, instance, schema):
            yield error

    return jsonschema.validators.extend(validator_class, {"properties": set_defaults})


DefaultValidatingDraft4Validator = extend_with_default(Draft4Validator)


def validate_json_schema(schema_def, instance):
    DefaultValidatingDraft4Validator(schema_def, format_checker=FormatChecker()).validate(instance)
