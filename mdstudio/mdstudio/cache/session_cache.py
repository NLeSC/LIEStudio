from typing import Optional, Any, List, Union, Tuple

from mdstudio.cache import CacheType
from mdstudio.cache.cache import ICache
# from mdstudio.api.context import ContextManager
import mdstudio

class SessionCacheWrapper(ICache):

    def __init__(self, session, cache_type=CacheType.User):
        # type: (CommonSession, CacheType) -> None
        self.session = session  # type: CommonSession
        self.cache_type = cache_type

    def put(self, key, value, expiry=None):
        # type: (str, Any, Optional[int]) -> dict

        request = {
            'key': key,
            'value': value
        }
        if expiry:
            request['expiry'] = expiry

        return self._call('put', request)

    def put_many(self, values, expiry=None):
        # type: (List[Tuple[str, Any]], Optional[int]) -> dict

        values = []
        for v in values:
            values.append({
                'key': v[0],
                'value': v[1]
            })

        request = {
            'keyValues': values
        }
        if expiry:
            request['expiry'] = expiry

        return self._call('put', request)

    def get(self, key):
        # type: (str) -> dict
        return self._call('get', {
            'key': key
        })

    def extract(self, key):
        # type: (str) -> dict
        return self._call('extract', {
            'key': key
        })

    def has(self, key):
        # type: (str) -> dict
        return self._call('has', {
            'key': key
        })

    def touch(self, keys):
        # type: (Union[List[str], str]) -> dict
        if isinstance(keys, list):
            request = {'keys': keys}
        else:
            request = {'key': keys}
        return self._call('touch', request)

    def forget(self, keys):
        # type: (Union[List[str], str]) -> dict
        if isinstance(keys, list):
            request = {'keys': keys}
        else:
            request = {'key': keys}
        return self._call('forget', request)

    def _call(self, uri, request):
        return self.session.call('mdstudio.cache.endpoint.{}'.format(uri), request, claims=mdstudio.api.context.ContextManager.get('call_context').get_cache_claims(self.cache_type))
