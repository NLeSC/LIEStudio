# coding=utf-8
from typing import Optional, Union, Dict, Any, List

from mdstudio.api.paginate import paginate_cursor
from mdstudio.db.connection_type import ConnectionType
from mdstudio.db.cursor import Cursor
from mdstudio.db.database import DocumentType, ProjectionOperators, SortOperators, IDatabase, AggregationOperator
from mdstudio.db.fields import Fields
from mdstudio.db.impl.connection import GlobalConnection
from mdstudio.db.index import Index
from mdstudio.db.response import ReplaceOneResponse, UpdateOneResponse, UpdateManyResponse
from mdstudio.deferred.chainable import chainable, Chainable
from mdstudio.deferred.return_value import return_value
from mdstudio.api.context import ContextCallable
from mdstudio.util.exception import MDStudioException


# noinspection PyShadowingBuiltins
class Model(ContextCallable):

    class Paginate(object):

        def __init__(self, model):
            self.model = model

            super(Model.Paginate, self).__init__()

        @chainable
        def find_many(self, mfilter, *args, **kwargs):
            # type: (DocumentType, Optional[ProjectionOperators], Optional[int], Optional[int], SortOperators, Optional[Fields]) -> Cursor

            @chainable
            def get_results(mfilter, paging, meta, self=self, args=args, **kwargs):

                if paging or isinstance(paging, dict):
                    paging['total'] = yield self.model.count(mfilter)
                    paging['page'] = meta['page']
                    paging['lastPage'] = paging['total'] // (meta['page'] * meta['limit'] - 1)

                results = yield self.model.find_many(filter, *args, **kwargs['db']).to_list()
                return_value(results)

            results, prev_meta, next_meta = yield paginate_cursor(mfilter, get_results, **kwargs)

            return_value((results, prev_meta, next_meta))


    # type: IDatabase
    wrapper = None

    # type: ConnectionType
    connection_type = ConnectionType.User

    date_time_fields = []
    date_fields = []
    encrypted_fields = []

    def __init__(self, wrapper=None, collection=None, connection_type=None):
        # type: (Optional[IDatabase], Optional[str], Optional[ConnectionType]) -> None
        super(Model, self).__init__()

        self._wrapper = wrapper or GlobalConnection.get_wrapper(connection_type or self.connection_type)
        self._check_wrapper()

        if issubclass(self.__class__, Model) and self.__class__ != Model and collection is None:
            self.collection = self.__class__.__name__.lower()
        else:
            if not collection:
                raise MDStudioException('No collection name was given!')
            self.collection = collection

        self.paginate = self.Paginate(self)

    def insert_one(self, insert, fields=None):
        # type: (DocumentType, Optional[Fields]) -> Union[str, Chainable]
        fields = self.fields(fields)
        insert_one = self.wrapper.insert_one(self.collection,
                                             insert=insert,
                                             fields=fields)
        return self.wrapper.extract(insert_one, 'id')

    def insert_many(self, insert, fields=None):
        # type: (List[DocumentType], Optional[Fields]) -> Union[List[str], Chainable]
        fields = self.fields(fields)
        insert_many = self.wrapper.insert_many(self.collection,
                                               insert=insert,
                                               fields=fields)
        return self.wrapper.extract(insert_many, 'ids')

    def replace_one(self, dbfilter, replacement, upsert=False, fields=None):
        # type: (DocumentType, DocumentType, bool, Optional[Fields]) -> Dict[ReplaceOneResponse, Any]
        fields = self.fields(fields)
        replace_one = self.wrapper.replace_one(self.collection,
                                               filter=dbfilter,
                                               replacement=replacement,
                                               upsert=upsert,
                                               fields=fields)
        return self.wrapper.transform(replace_one, ReplaceOneResponse)

    def count(self, filter=None, skip=None, limit=None, fields=None, cursor_id=None, with_limit_and_skip=False):
        # type: (Optional[DocumentType], Optional[int], Optional[int], Optional[Fields], Optional[str], bool) -> Union[int, Chainable]
        fields = self.fields(fields)
        count = self.wrapper.count(self.collection,
                                   filter=filter,
                                   skip=skip,
                                   limit=limit,
                                   fields=fields,
                                   cursor_id=cursor_id,
                                   with_limit_and_skip=with_limit_and_skip)
        return self.wrapper.extract(count, 'total')

    def update_one(self, dbfilter, update, upsert=False, fields=None):
        # type: (DocumentType, DocumentType, bool, Optional[Fields]) -> Union[UpdateOneResponse, Chainable]
        fields = self.fields(fields)
        update_one = self.wrapper.update_one(self.collection,
                                             filter=dbfilter,
                                             update=update,
                                             upsert=upsert,
                                             fields=fields)
        return self.wrapper.transform(update_one, UpdateOneResponse)

    def update_many(self, dbfilter, update, upsert=False, fields=None):
        # type: (DocumentType, DocumentType, bool, Optional[Fields]) -> Union[UpdateManyResponse, Chainable]
        fields = self.fields(fields)
        update_many = self.wrapper.update_many(self.collection,
                                               filter=dbfilter,
                                               update=update,
                                               upsert=upsert,
                                               fields=fields)
        return self.wrapper.transform(update_many, UpdateManyResponse)

    @chainable
    def find_one(self, dbfilter, projection=None, skip=None, sort=None, fields=None):
        # type: (DocumentType, Optional[ProjectionOperators], Optional[int], SortOperators, Optional[Fields]) -> Union[Optional[dict], Chainable]
        fields = self.fields(fields)
        result = self.wrapper.find_one(self.collection,
                                       filter=dbfilter,
                                       projection=projection,
                                       skip=skip,
                                       sort=sort,
                                       fields=fields)
        result = yield self.wrapper.extract(result, 'result')
        if fields:
            fields.convert_call(result)
        return_value(result)

    def find_many(self, dbfilter, projection=None, skip=None, limit=None, sort=None, fields=None):
        # type: (DocumentType, Optional[ProjectionOperators], Optional[int], Optional[int], SortOperators, Optional[Fields]) -> Cursor
        fields = self.fields(fields)
        results = self.wrapper.find_many(self.collection,
                                         filter=dbfilter,
                                         projection=projection,
                                         skip=skip,
                                         limit=limit,
                                         sort=sort,
                                         fields=fields)

        return self.wrapper.make_cursor(results, fields)

    @chainable
    def find_one_and_update(self, dbfilter, update, upsert=False, projection=None, sort=None, return_updated=False, fields=None):
        # type: (DocumentType, DocumentType, bool, Optional[ProjectionOperators], SortOperators, bool, Optional[Fields]) -> Union[Optional[dict], Chainable]
        fields = self.fields(fields)
        result = self.wrapper.find_one_and_update(self.collection,
                                                  filter=dbfilter,
                                                  update=update,
                                                  upsert=upsert,
                                                  projection=projection,
                                                  sort=sort,
                                                  return_updated=return_updated,
                                                  fields=fields)
        result = yield self.wrapper.extract(result, 'result')
        if fields:
            fields.convert_call(result)
        return_value(result)

    @chainable
    def find_one_and_replace(self, dbfilter, replacement, upsert=False, projection=None, sort=None, return_updated=False, fields=None):
        # type: (DocumentType, DocumentType, bool, Optional[ProjectionOperators], SortOperators, bool, Optional[Fields]) -> Union[Optional[dict], Chainable]
        fields = self.fields(fields)
        result = self.wrapper.find_one_and_replace(self.collection,
                                                   filter=dbfilter,
                                                   replacement=replacement,
                                                   upsert=upsert,
                                                   projection=projection,
                                                   sort=sort,
                                                   return_updated=return_updated,
                                                   fields=fields)

        result = yield self.wrapper.extract(result, 'result')
        if fields:
            fields.convert_call(result)
        return_value(result)

    @chainable
    def find_one_and_delete(self, dbfilter, projection=None, sort=None, fields=None):
        # type: (DocumentType, Optional[ProjectionOperators], SortOperators, Optional[Fields]) -> Union[Optional[dict], Chainable]
        fields = self.fields(fields)
        result = self.wrapper.find_one_and_delete(self.collection,
                                                  filter=dbfilter,
                                                  projection=projection,
                                                  sort=sort,
                                                  fields=fields)

        result = yield self.wrapper.extract(result, 'result')
        if fields:
            fields.convert_call(result)
        return_value(result)

    def distinct(self, field, dbfilter=None, fields=None):
        # type: (str, Optional[DocumentType], Optional[Fields]) -> Union[List[dict], Chainable]
        fields = self.fields(fields)
        results = self.wrapper.distinct(self.collection,
                                        field=field,
                                        filter=dbfilter,
                                        fields=fields)
        return self.wrapper.extract(results, 'results')

    def aggregate(self, pipeline):
        # type: (List[AggregationOperator]) -> Cursor
        results = self.wrapper.aggregate(self.collection,
                                         pipeline=pipeline)
        return self.wrapper.make_cursor(results, None)

    def delete_one(self, dbfilter, fields=None):
        # type: (DocumentType, Optional[Fields]) -> Union[int, Chainable]
        fields = self.fields(fields)
        delete_one = self.wrapper.delete_one(self.collection,
                                             filter=dbfilter,
                                             fields=fields)
        return self.wrapper.extract(delete_one, 'count')

    def delete_many(self, dbfilter, fields=None):
        # type: (DocumentType, Optional[Fields]) -> Union[int, Chainable]
        fields = self.fields(fields)
        delete_many = self.wrapper.delete_many(self.collection,
                                               filter=dbfilter,
                                               fields=fields)
        return self.wrapper.extract(delete_many, 'count')

    def create_indexes(self, collection, indexes):
        # type: (DocumentType, List[Index]) -> Any

        create_indexes = self.wrapper.create_indexes(collection, indexes)
        return self.wrapper.extract(create_indexes, 'names')

    def drop_all_indexes(self, collection):
        # type: (DocumentType) -> Any

        self.wrapper.drop_all_indexes(collection)

    def drop_indexes(self, collection, indexes):
        # type: (DocumentType, List[Index]) -> Any

        self.wrapper.drop_indexes(collection, indexes)

    def fields(self, other=None):
        own_fields = Fields(date_times=self.date_time_fields, dates=self.date_fields, encrypted=self.encrypted_fields)
        if other:
            own_fields = own_fields.merge(other)
        if own_fields.is_empty():
            return None
        return self._return_fields(own_fields)

    @property
    def wrapper(self):
        return self._wrapper(self.call_context)

    def _return_fields(self, fields):
        return fields

    def _check_wrapper(self):

        if not isinstance(self._wrapper, IDatabase):
            raise MDStudioException('Wrapper should inherit IDatabase')
        if not isinstance(self._wrapper, ContextCallable):
            raise MDStudioException('Wrapper should inherit ContextCallable')
