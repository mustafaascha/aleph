import logging
from banal import ensure_list
from elasticsearch import RequestError

from aleph.core import es
from aleph.util import backoff

log = logging.getLogger(__name__)

# This means that text beyond the first 100 MB will not be indexed
INDEX_MAX_LEN = 1024 * 1024 * 500
REQUEST_TIMEOUT = 60 * 60 * 6
REQUEST_RETRIES = 10
TIMEOUT = '%ss' % REQUEST_TIMEOUT
BULK_PAGE = 1000
# cf. https://www.elastic.co/guide/en/elasticsearch/reference/current/search-request-from-size.html  # noqa
MAX_PAGE = 9999


def backoff_cluster(failures=0):
    """This is intended to halt traffic to the cluster if it is in a
    recovery state, e.g. after a master failure or severe node failures.
    """
    backoff(failures=failures)


def unpack_result(res):
    """Turn a document hit from ES into a more traditional JSON object."""
    error = res.get('error')
    if error is not None:
        raise RuntimeError("Query error: %(reason)s" % error)
    if res.get('found') is False:
        return
    data = res.get('_source', {})
    data['id'] = str(res.get('_id'))
    if res.get('_score') is not None:
        data['score'] = res.get('_score')
    if 'highlight' in res:
        data['highlight'] = []
        for key, value in res.get('highlight', {}).items():
            data['highlight'].extend(value)
    return data


def authz_query(authz):
    """Generate a search query from an authz object."""
    # Hot-wire authorization entirely for admins.
    if authz.is_admin:
        return {'match_all': {}}
    collections = authz.collections(authz.READ)
    if not len(collections):
        return {'match_none': {}}
    return {'terms': {'collection_id': collections}}


def bool_query():
    return {
        'bool': {
            'should': [],
            'filter': [],
            'must': [],
            'must_not': []
        }
    }


def none_query(query=None):
    if query is None:
        query = bool_query()
    query['bool']['must'].append({'match_none': {}})
    return query


def field_filter_query(field, values):
    """Need to define work-around for full-text fields."""
    values = ensure_list(values)
    if not len(values):
        return {'match_all': {}}
    if field in ['_id', 'id']:
        return {'ids': {'values': values}}
    if len(values) == 1:
        if field in ['names', 'addresses']:
            field = '%s.text' % field
            return {'match_phrase': {field: values[0]}}
        return {'term': {field: values[0]}}
    return {'terms': {field: values}}


def query_delete(index, query, **kwargs):
    "Delete all documents matching the given query inside the index."
    for attempt in range(REQUEST_RETRIES):
        try:
            es.delete_by_query(index=index,
                               body={'query': query},
                               conflicts='proceed',
                               timeout=TIMEOUT,
                               request_timeout=REQUEST_TIMEOUT,
                               **kwargs)
            return
        except RequestError:
            raise
        except Exception as exc:
            log.warning("Query delete failed: %s", exc)
        backoff_cluster(failures=attempt)


def index_safe(index, id, body, **kwargs):
    """Index a single document and retry until it has been stored."""
    for attempt in range(REQUEST_RETRIES):
        try:
            es.index(index=index, doc_type='doc', id=id, body=body, **kwargs)
            body['id'] = str(id)
            body.pop('text', None)
            return body
        except RequestError:
            raise
        except Exception as exc:
            log.warning("Index error [%s:%s]: %s", index, id, exc)
        backoff_cluster(failures=attempt)


def search_safe(*args, **kwargs):
    # This is not supposed to be used in every location where search is
    # run, but only where it's a backend search that we could back off of
    # without hurting UX.
    for attempt in range(REQUEST_RETRIES):
        try:
            kwargs['doc_type'] = 'doc'
            return es.search(*args, **kwargs)
        except RequestError:
            raise
        except Exception as exc:
            log.warning("Search error: %s", exc)
        backoff_cluster(failures=attempt)


def index_form(texts):
    """Turn a set of strings into the appropriate form for indexing."""
    results = []
    total_len = 0

    for text in texts:
        # We don't want to store more than INDEX_MAX_LEN of text per doc
        if total_len > INDEX_MAX_LEN:
            # TODO: there might be nicer techniques for dealing with overly
            # long text buffers?
            results = list(set(results))
            total_len = sum((len(t) for t in results))
            if total_len > INDEX_MAX_LEN:
                break

        if isinstance(text, str):
            text = text.strip()
            if len(text):
                total_len += len(text)
                results.append(text)
    return results
