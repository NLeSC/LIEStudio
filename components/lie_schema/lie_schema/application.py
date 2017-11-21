import json

import time
from autobahn.wamp import PublishOptions
from lie_schema.exception import SchemaException
from lie_schema.schema_repository import SchemaRepository
from mdstudio.api.register import register
from mdstudio.component.impl.core import CoreComponentSession
from mdstudio.deferred.chainable import chainable
from mdstudio.deferred.return_value import return_value


class SchemaComponent(CoreComponentSession):
    """
    Database management WAMP methods.
    """

    def onConnect(self):
        return self.on_connect()

    @chainable
    def on_run(self):
        yield self.call('mdstudio.auth.endpoint.ring0.set-status', {'status': True})
        yield super(SchemaComponent, self).on_run()

    def pre_init(self):
        self.endpoints = SchemaRepository(self, 'endpoints')
        self.resources = SchemaRepository(self, 'resources')
        self.claims = SchemaRepository(self, 'claims')
        self.component_waiters.append(CoreComponentSession.ComponentWaiter(self, 'db'))

    @register(u'mdstudio.schema.endpoint.upload', {}, {})
    @chainable
    def schema_upload(self, request, claims=None, **kwargs):
        vendor = claims['vendor']
        component = request['component']

        endpoint_schemas = request['schemas'].get('endpoints')
        if endpoint_schemas:
            for schema in endpoint_schemas:
                yield self.endpoints.upsert(vendor, component, schema, claims)
        resource_schemas = request['schemas'].get('resources')
        if resource_schemas:
            for schema in resource_schemas:
                yield self.resources.upsert(vendor, component, schema, claims)
        claim_schemas = request['schemas'].get('claims')
        if claim_schemas:
            for schema in claim_schemas:
                yield self.claims.upsert(vendor, component, schema, claims)

    # @todo: validate using json schema draft
    @register(u'mdstudio.schema.endpoint.get', {}, {})
    @chainable
    def schema_get(self, request, claims=None, **kwargs):
        vendor = claims['vendor']
        component = request['component']
        schema_type = request['type']
        schema_name = request['name']
        version = request.get('version', 1)

        if schema_type == "endpoint":
            res = yield self.endpoints.find_latest(vendor, component, schema_name, version)
        elif schema_type == "resource":
            res = yield self.resources.find_latest(vendor, component, schema_name, version)
        elif schema_type == "claim":
            res = yield self.claims.find_latest(vendor, component, schema_name, version)
        else:
            raise SchemaException('Schema type "{}" is not known'.format(schema_type))

        if not res:
            error = 'Schema name "{}" with type "{}", and '\
                    'version "{}" on "{}/{}" was not found'.format(schema_name, schema_type, version, vendor, component)
            raise SchemaException(error)

        return_value(json.loads(res['schema']))

    def authorize_request(self, uri, claims):
        if uri == u'mdstudio.schema.endpoint.status':
            return True

        # @todo: check if user is part of group (in usermode)
        if claims['vendor'] in claims['groups']:
            return True
        # @todo: allow group/user specific access

        return False
