import logging
from pprint import pprint  # noqa
from random import randint
from banal import ensure_list
from normality import normalize
from followthemoney import model
from followthemoney.types import registry

from aleph.core import es, cache
from aleph.model import Entity, Collection
from aleph.index.core import collections_index, entities_index, records_index
from aleph.index.util import query_delete, unpack_result, index_safe
from aleph.index.util import index_form, search_safe

log = logging.getLogger(__name__)


def index_collection(collection, sync=False):
    """Index a collection."""
    if collection.deleted_at is not None:
        return delete_collection(collection.id)

    data = {
        'foreign_id': collection.foreign_id,
        'created_at': collection.created_at,
        'updated_at': collection.updated_at,
        'label': collection.label,
        'kind': collection.kind,
        'summary': collection.summary,
        'category': Collection.DEFAULT,
        'publisher': collection.publisher,
        'publisher_url': collection.publisher_url,
        'info_url': collection.info_url,
        'data_url': collection.data_url,
        'casefile': collection.casefile,
        'secret': collection.secret,
        'collection_id': collection.id,
        'schemata': {},
        'team': []
    }
    texts = [v for v in data.values() if isinstance(v, str)]

    if collection.category in Collection.CATEGORIES:
        data['category'] = collection.category

    if collection.creator is not None:
        data['creator'] = {
            'id': collection.creator.id,
            'type': collection.creator.type,
            'name': collection.creator.name
        }
        texts.append(collection.creator.name)

    for role in collection.team:
        data['team'].append({
            'id': role.id,
            'type': role.type,
            'name': role.name
        })
        texts.append(role.name)

    stats = get_collection_stats(collection.id)
    data['count'] = stats['count']

    # expose entities by schema count.
    thing = model.get(Entity.THING)
    for schema, count in stats['schemata'].items():
        schema = model.get(schema)
        if schema is not None and schema.is_a(thing):
            data['schemata'][schema.name] = count

    # if no countries or langs are given, take the most common from the data.
    countries = ensure_list(collection.countries)
    countries = countries or stats['countries'].keys()
    data['countries'] = registry.country.normalize_set(countries)

    languages = ensure_list(collection.languages)
    languages = languages or stats['languages'].keys()
    data['languages'] = registry.language.normalize_set(languages)

    texts.extend([normalize(t, ascii=True) for t in texts])
    data['text'] = index_form(texts)
    return index_safe(collections_index(), collection.id, data,
                      refresh=sync)


def get_collection(collection_id):
    """Fetch a collection from the index."""
    result = es.get(index=collections_index(),
                    doc_type='doc',
                    id=collection_id,
                    ignore=[404],
                    _source_exclude=['text'])
    return unpack_result(result)


def flush_collection_stats(collection_id):
    cache.kv.delete(cache.key('cstats', collection_id))


def get_collection_stats(collection_id):
    """Compute some statistics on the content of a collection."""
    key = cache.key('cstats', collection_id)
    data = cache.get_complex(key)
    if data is not None:
        return data

    log.info("Generating collection stats: %s", collection_id)
    query = {
        'size': 0,
        'query': {
            'bool': {
                'filter': [
                    {'term': {'collection_id': collection_id}}
                ]
            }
        },
        'aggs': {
            'schemata': {'terms': {'field': 'schema', 'size': 1000}},
            'countries': {'terms': {'field': 'countries', 'size': 500}},
            'languages': {'terms': {'field': 'languages', 'size': 10}},
        }
    }
    result = search_safe(index=entities_index(), body=query)
    aggregations = result.get('aggregations', {})
    data = {'count': result['hits']['total']}

    for facet in ['schemata', 'countries', 'languages']:
        data[facet] = {}
        for bucket in aggregations[facet]['buckets']:
            data[facet][bucket['key']] = bucket['doc_count']
    expire = randint(3600 * 3, 3600 * 12)
    cache.set_complex(key, data, expire=expire)
    return data


def get_instance_stats(authz):
    collections = authz.collections(authz.READ)
    entities = 0
    for collection in collections:
        stats = get_collection_stats(collection)
        entities += stats['count']
    return {
        'collections': len(collections),
        'entities': entities
    }


def delete_collection(collection_id, sync=False):
    """Delete all documents from a particular collection."""
    es.delete(collections_index(), doc_type='doc', id=str(collection_id),
              refresh=sync, ignore=[404])


def delete_entities(collection_id):
    """Delete entities from a collection."""
    query = {'bool': {
        'must_not': {'term': {'schemata': 'Document'}},
        'must': {'term': {'collection_id': collection_id}}
    }}
    query_delete(entities_index(), query)


def delete_documents(collection_id):
    """Delete documents from a collection."""
    records_query = {'term': {'collection_id': collection_id}}
    query_delete(records_index(), records_query)
    query = {'bool': {
        'must': [
            {'term': {'schemata': 'Document'}},
            {'term': {'collection_id': collection_id}}
        ]
    }}
    query_delete(entities_index(), query)
