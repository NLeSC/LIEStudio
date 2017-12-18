# -*- coding: utf-8 -*-

import json
import os
import pkgutil


def _schema_to_data(schema, data=None, defdict=None):
    """
    Translate the schema for gromacs to an standard python
    dictionary
    """
    default_data = defdict or {}

    properties = schema.get('properties', {})
    for key, value in properties.items():
        if 'properties' in value:
            default_data[key] = _schema_to_data(value)
        elif 'default' in value:
            default_data[key] = value.get('default')

    # Update with existing data
    if data:
        default_data.update(data)

    return default_data


GROMACS_LIE_SCHEMA = os.path.join(
    pkgutil.get_data('lie_md', 'data/gromacs_lie_schema.json'))

SETTINGS = _schema_to_data(json.loads(GROMACS_LIE_SCHEMA))
