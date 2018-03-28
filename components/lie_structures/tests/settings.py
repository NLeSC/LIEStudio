# -*- coding: utf-8 -*-

import os
import json

def _schema_to_data(schema, data=None, defdict=None):
    default_data = defdict or {}
    properties = schema.get('properties', {})

    for key, value in properties.items():
        if 'default' in value:
            if 'properties' in value:
                default_data[key] = _schema_to_data(value)
            else:
                default_data[key] = value.get('default')

    # Update with existing data
    if data:
        default_data.update(data)

    return default_data


STRUCTURES_SCHEMA = os.path.join(os.path.dirname(__file__), 'structures_schema.json')
BIOPYTHON_SCHEMA = os.path.join(os.path.dirname(__file__), 'biopython_schema.json')

settings = _schema_to_data(json.load(open(STRUCTURES_SCHEMA)))
