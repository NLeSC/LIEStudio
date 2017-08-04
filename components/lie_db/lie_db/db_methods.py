# -*- coding: utf-8 -*-

"""
file: db_methods.py
"""

import os
import copy
import pytz
import getpass
import logging
import datetime
import itertools
import subprocess

from dateutil.parser import parse as parsedate
from pymongo.errors import ConnectionFailure
from twisted.logger import Logger
from pymongo import MongoClient
from distutils import spawn
from autobahn import wamp
from bson import ObjectId

from lie_corelib import WampSchema, validate_json_schema
from lie_corelib.db import IDatabaseWrapper

logger = Logger(namespace='db')

class MongoDatabaseWrapper(IDatabaseWrapper):
    def __init__(self, namespace, db):
        self._namespace = namespace
        self._db = db

    def count(self, collection=None, filter=None, skip=0, limit=0, fields=None):
        coll = self._get_collection(collection)
        if fields and 'date' in fields.keys():
            self._transform_to_datetime({'filter': filter}, fields['date'])

        return {'total': 0 if coll is None else coll.count(filter, skip=skip, limit=limit)}

    def delete_one(self, collection=None, filter=None, fields=None):
        coll = self._get_collection(collection)
        if fields and 'date' in fields.keys():
            self._transform_to_datetime({'filter': filter}, fields['date'])

        return {'count': 0 if coll is None else coll.delete_one(filter).deleted_count}

    def delete_many(self, collection=None, filter=None, fields=None):
        coll = self._get_collection(collection)
        if fields and 'date' in fields.keys():
            self._transform_to_datetime({'filter': filter}, fields['date'])

        return {'count': 0 if coll is None else coll.delete_many(filter).deleted_count}

    def find_one(self, collection=None, filter=None, projection=None, skip=0, sort=None, fields=None):
        coll = self._get_collection(collection)
        if fields and 'date' in fields.keys():
            self._transform_to_datetime({'filter': filter}, fields['date'])

        if coll is None:
            return {'result': None}
        else:
            if filter and 'id' in filter:
                filter['_id'] = ObjectId(filter.pop('id'))

            result = coll.find_one(filter, projection, skip, sort=sort)

            if result:
                result['id'] = str(result.pop('_id'))
                self._transform_datetime_to_isostring(result)

            return {'result': result}

    def find_many(self, collection=None, filter=None, projection=None, skip=0, limit=0, sort=None, fields=None):
        coll = self._get_collection(collection)
        if fields and 'date' in fields.keys():
            self._transform_to_datetime({'filter': filter}, fields['date'])

        if not coll:
            return {
                'result': [],
                'total': 0,
                'size': 0
            }
        
        if filter and 'id' in filter:
            filter['_id'] = ObjectId(filter.pop('id'))

        results = []

        for doc in coll.find(filter, projection, skip, sort=sort):
            doc['id'] = str(doc.pop('_id'))
            self._transform_datetime_to_isostring(doc)
            results.append(doc)

        return {
            'result': results,
            'total': self.count(collection, filter, skip, limit, fields),
            'size': len(results)
        }

    def insert_one(self, collection=None, insert=None, fields=None):
        coll = self._get_collection(collection, True)
        if fields and 'date' in fields.keys():
            self._transform_to_datetime({'insert': insert}, fields['date'])
        
        if isinstance(insert, dict) and 'id' in insert.keys():
            insert['_id'] = ObjectId(insert.pop('id'))

        return {'id': str(coll.insert_one(insert).inserted_id)}

    def insert_many(self, collection=None, insert=None, fields=None):
        coll = self._get_collection(collection, True)
        if fields and 'date' in fields.keys():
            self._transform_to_datetime({'insert': insert}, fields['date'])
        
        for doc in insert:
            if isinstance(doc, dict) and 'id' in doc.keys():
                doc['_id'] = ObjectId(doc.pop('id'))

        return {'ids': [str(id) for id in coll.insert_many(insert).inserted_ids]}

    def update_one(self, collection=None, filter=None, update=None, upsert=False, fields=None):
        coll = self._get_collection(collection, upsert)
        if fields and 'date' in fields.keys():
            self._transform_to_datetime({'filter': filter, 'update': update}, fields['date'])

        if coll is None:
            return self._update_response(upsert, None)

        updateresult = coll.update_one(filter, update, upsert)

        return self._update_response(upsert, updateresult)

    def update_many(self, collection=None, filter=None, update=None, upsert=False, fields=None):
        coll = self._get_collection(collection, upsert)
        if fields and 'date' in fields.keys():
            self._transform_to_datetime({'filter': filter, 'update': update}, fields['date'])

        if coll is None:
            return self._update_response(upsert, None)

        updateresult = coll.update_many(filter, update, upsert)

        return self._update_response(upsert, updateresult)

    def _update_response(self, upsert, updateresult=None):
        if updateresult is None:
            return {
                'matched': 0,
                'modifiedCount': 0
            }

        response = {
            'matched': updateresult.matched_count,
            'modifiedCount': updateresult.modified_count
        }

        if upsert and updateresult.upserted_id:
            response['upsertedId'] = str(updateresult.upserted_id)

        return response

    def _get_collection(self, collection=None, create=False):
        if isinstance(collection, dict):
            collection_name = collection['name']
        else:
            collection_name = collection

        if collection_name not in self._db.collection_names():
            if create:
                logger.info('Creating collection {collection} in {namespace}', collection=collection_name, namespace=self._namespace)
            else:
                return None

        return self._db[collection_name]

    def _transform_to_datetime(self, document, fields):
        if fields is None:
            return

        for field in fields:
            fields = field.split('.')
            self._transform_docfield_to_datetime(document, fields)

    def _transform_docfield_to_datetime(self, doc, field):
        subdoc = doc

        l = 0
        for level in field[:-1]:
            if isinstance(subdoc, dict) and level in subdoc:
                subdoc = subdoc[level]
            else:
                if isinstance(subdoc, list):
                    for d in subdoc:
                        self._transform_docfield_to_datetime(d, field[l:])
                subdoc = None
                break

            l = l + 1

        if subdoc is None:
            return

        key = field[-1]

        if isinstance(subdoc, list):
            for d in subdoc:
                d[key] = parsedate(d[key]).astimezone(pytz.utc)
        else:
            subdoc[key] = parsedate(subdoc[key]).astimezone(pytz.utc)
    
    def _transform_datetime_to_isostring(self, document):
        if isinstance(document, dict):
            iter = document.items()
        elif isinstance(document, list):
            iter = enumerate(document)
        else:
            return

        for key, value in iter:
            if isinstance(value, datetime.datetime):
                document[key] = value.isoformat()
            else:
                self._transform_datetime_to_isostring(value)

    def extract(self, result, property):
        return result[property]

    def transform(self, result, transformed):
        return None if result is None else transformed(result)

class MongoClientWrapper:
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._client = MongoClient(host, port)
        self._namespaces = {}

    def get_namespace(self, namespace):
        if namespace not in self._namespaces.keys():
            if namespace not in self._client.database_names():
                logger.info('Creating database for {namespace}', namespace=namespace)
            
            db = MongoDatabaseWrapper(namespace, self._client[namespace])
            self._namespaces[namespace] = db
        else:
            db = self._namespaces[namespace]

        return db
