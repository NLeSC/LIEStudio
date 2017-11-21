import json
import re
from typing import Union, Optional, Callable

import os
from autobahn import wamp
from autobahn.wamp import RegisterOptions
from jsonschema import ValidationError
from mdstudio.api.converter import convert_obj_to_json

from mdstudio.api.api_result import APIResult
from mdstudio.api.schema import ISchema, EndpointSchema, validate_json_schema, ClaimSchema, \
    MDStudioClaimSchema, InlineSchema
from mdstudio.component.impl.common import CommonSession
from mdstudio.deferred.chainable import chainable
from mdstudio.deferred.return_value import return_value

SchemaType = Union[str, dict, ISchema]


def validation_error(schema, instance, error, prefix, uri):
    return \
        '{prefix} validation on uri {uri} failed with schema:\n{schema}\nfailed on instance {instance}. ' \
        'Subschema for {property}:\n{subschema}\ndid not match actual value:\n{subproperty}'.format(
            prefix=prefix,
            uri=uri,
            schema=json.dumps(schema, indent=2),
            instance=json.dumps(instance, indent=2),
            property='.'.join(error.schema_path),
            subschema=error.schema,
            subproperty=error.instance
        )


def register(uri, input_schema, output_schema, claim_schema=None, options=None, scope=None):
    # type: (str, SchemaType, SchemaType, Optional[SchemaType], bool, Optional[str], Optional[RegisterOptions], Optional[str]) -> Callable
    """
    Decorator for more complete WAMP uri registration

    Besides registering the uri, also wrap the function to validate json schemas on input and output.
    Store the schema definition and custom scopes in attributes of the function for later processing.

    :param uri:             WAMP uri to register on
    :type uri:              str
    :param input_schema:    JSON schema to check the input.
    :type input_schema:     ISchema
    :param output_schema:   JSON schema to check the output.
    :type output_schema:    ISchema
    :param details_arg:     Boolean indicating whether the wrapped function expects a details argument
                            (will be set in the RegisterOptions).
    :type details_arg:      bool
    :param match:           Matching approach for the uri. Defaults to 'exact' in crossbar.
    :type match:            str
    :param options:         Options for registration. Created if not provided.
    :type options:          wamp.RegisterOptions
    :param scope:           Custom scope name within this namespace. If none is provided, only exact uri permission grants access.
    :type scope:            str
    :return:                Wrapped function with extra attributes
    :rtype:                 function
    """

    if not input_schema:
        # print('Input on {uri} is not checked'.format(uri=uri))
        input_schema = InlineSchema({})
    elif isinstance(input_schema, str):
        if not re.match('\\w+://.*', input_schema):
            input_schema = 'endpoint://{}'.format(input_schema)

        input_schema = EndpointSchema(input_schema)
    elif isinstance(input_schema, dict):
        input_schema = InlineSchema(input_schema)

    if not output_schema:
        # print('Output on {uri} is not checked'.format(uri=uri))
        output_schema = InlineSchema({})
    elif isinstance(output_schema, str):
        if not re.match('\\w+://.*', output_schema):
            output_schema = 'endpoint://{}'.format(output_schema)

        output_schema = EndpointSchema(output_schema)
    elif isinstance(output_schema, dict):
        output_schema = InlineSchema(output_schema)

    claim_schemas = [MDStudioClaimSchema(CommonSession)]

    if not claim_schema:
        pass
    elif isinstance(claim_schema, str):
        if not re.match(r'\w+://.*', claim_schema):
            claim_schema = 'claims://{}'.format(claim_schema)

        claim_schema = ClaimSchema(claim_schema)
        claim_schemas.append(claim_schema)
    elif isinstance(claim_schema, dict):
        claim_schema = InlineSchema(claim_schema)
        claim_schemas.append(claim_schema)

    def wrap_f(f):
        @wamp.register(uri, options)
        @chainable
        def wrapped_f(self, request, *args, signed_claims=None, **kwargs):
            claims = yield super(CommonSession, self).call('mdstudio.auth.endpoint.verify', signed_claims)

            if 'error' in claims:
                res = APIResult(error=claims['error'])
            elif 'expired' in claims:
                res = APIResult(expired=claims['expired'])
            else:
                claims = claims['claims']

                try:
                    for s in claim_schemas:
                        validate_json_schema(s.to_schema(), claims)
                except ValidationError as e:
                    res = {'error': validation_error(s.to_schema(), claims, e, 'Claims', uri)}
                    self.log.error('{error_message}', error_message=res['error'])
                else:
                    if not self.authorize_request(uri, claims):
                        res = APIResult(error='Unauthorized call to {}'.format(uri))
                        self.log.error('{error_message}', error_message=res['error'])
                    else:
                        # @todo: catch exceptions and add error
                        # @todo: support warnings
                        try:
                            validate_json_schema(input_schema.to_schema(), request)
                        except ValidationError as e:
                            res = APIResult(
                                error=validation_error(input_schema.to_schema(), request, e, 'Input', uri))
                            self.log.error('{error_message}', error_message=res['error'])
                        else:
                            res = yield f(self, request, *args, claims=claims, **kwargs)

                            if not isinstance(res, APIResult):
                                res = APIResult(res)

                            if 'result' in res:
                                try:
                                    validate_json_schema(output_schema.to_schema(), res['result'])
                                except ValidationError as e:
                                    res['warning'] = validation_error(output_schema.to_schema(), res['result'], e, 'Output', uri)
                                    self.log.warn('{warning_message}', warning_message=res['warning'])

            convert_obj_to_json(res)
            return_value(res)

        wrapped_f.input_schema = input_schema
        wrapped_f.output_schema = output_schema
        wrapped_f.claims_schema = claim_schema

        wrapped_f.wrapped = f

        if scope:
            wrapped_f.uri = uri
            wrapped_f.scope = scope

        return wrapped_f

    return wrap_f
