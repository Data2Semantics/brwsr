from SPARQLWrapper import SPARQLWrapper, JSON, XML, TURTLE
import json
import logging
import requests
import config
from app import app
import rdfextras
import traceback
rdfextras.registerplugins()
from rdflib import Dataset
import rdflib.util

log = app.logger
log.setLevel(logging.DEBUG)

LOCAL_STORE = config.LOCAL_STORE
LOCAL_FILE = config.LOCAL_FILE

SPARQL_ENDPOINT_MAPPING = config.SPARQL_ENDPOINT_MAPPING

SPARQL_ENDPOINT = config.SPARQL_ENDPOINT

DEFAULT_BASE = config.DEFAULT_BASE

QUERY_RESULTS_LIMIT = config.QUERY_RESULTS_LIMIT
CUSTOM_PARAMETERS = config.CUSTOM_PARAMETERS

labels = {}

g = Dataset()

if LOCAL_STORE:
    log.info("Loading local file: {}".format(LOCAL_FILE))
    try:
        format = rdflib.util.guess_format(LOCAL_FILE)
        g.load(LOCAL_FILE, format=format)
    except:
        log.error(traceback.format_exc())
        raise Exception("Cannot guess file format for {} or could not load file".format(LOCAL_FILE))


def visit(url, format='html'):
    log.debug("Starting query")

    if LOCAL_STORE:
        return visit_local(url, format=format)
    else:
        return visit_sparql(url, format=format)


def visit_sparql(url, format='html'):
    sparql = None
    for prefix, endpoint in SPARQL_ENDPOINT_MAPPING.items():
        if url.startswith(DEFAULT_BASE + prefix + '/'):
            sparql = SPARQLWrapper(endpoint)
            break
    if not sparql:
        sparql = SPARQLWrapper(SPARQL_ENDPOINT)
        log.debug("Will be using {}".format(SPARQL_ENDPOINT))

    sparql.setReturnFormat(JSON)
    for key, value in CUSTOM_PARAMETERS.items():
        sparql.addParameter(key, value)

    if format == 'html':
        q = u"""SELECT DISTINCT ?s ?p ?o ?g WHERE {{
            {{
            GRAPH ?g {{
                {{
                    <{url}> ?p ?o .
                    BIND(<{url}> as ?s)
                }} UNION {{
                    ?s ?p <{url}>.
                    BIND(<{url}> as ?o)
                }} UNION {{
                    ?s <{url}> ?o.
                    BIND(<{url}> as ?p)
                }}
            }}
            }} UNION {{
                {{
                    <{url}> ?p ?o .
                    BIND(<{url}> as ?s)
                }} UNION {{
                    ?s ?p <{url}>.
                    BIND(<{url}> as ?o)
                }} UNION {{
                    ?s <{url}> ?o.
                    BIND(<{url}> as ?p)
                }}
            }}
        }} LIMIT {limit}""".format(url=url, limit=QUERY_RESULTS_LIMIT)

        log.debug(q)

        sparql.setQuery(q)

        results = sparql.query().convert()["results"]["bindings"]
    else:
        q = u"DESCRIBE <{}>".format(url)
        sparql.setQuery(q)

        if format == 'jsonld':
            sparql.setReturnFormat(XML)
            results = sparql.query().convert().serialize(format='json-ld')
        elif format == 'rdfxml':
            sparql.setReturnFormat(XML)
            results = sparql.query().convert().serialize(format='pretty-xml')
        elif format == 'turtle':
            sparql.setReturnFormat(XML)
            results = sparql.query().convert().serialize(format='turtle')
        else:
            results = 'Nothing'

    log.debug("Received results")

    return results


def visit_local(url, format='html'):
    if format == 'html':
        q = u"""SELECT DISTINCT ?s ?p ?o ?g WHERE {{
            {{
            GRAPH ?g {{
                {{
                    <{url}> ?p ?o .
                    BIND(<{url}> as ?s)
                }} UNION {{
                    ?s ?p <{url}>.
                    BIND(<{url}> as ?o)
                }} UNION {{
                    ?s <{url}> ?o.
                    BIND(<{url}> as ?p)
                }}
            }}
            }} UNION {{
                {{
                    <{url}> ?p ?o .
                    BIND(<{url}> as ?s)
                }} UNION {{
                    ?s ?p <{url}>.
                    BIND(<{url}> as ?o)
                }} UNION {{
                    ?s <{url}> ?o.
                    BIND(<{url}> as ?p)
                }}
            }}
        }} LIMIT {limit}""".format(url=url, limit=QUERY_RESULTS_LIMIT)

        log.debug(q)

        results = g.query(q)
    else:
        q = u"DESCRIBE <{}>".format(url)

        if format == 'jsonld':
            results = g.query(q).serialize(format='json-ld')
        elif format == 'rdfxml':
            results = g.query(q).serialize(format='pretty-xml')
        elif format == 'turtle':
            results = g.query(q).serialize(format='turtle')
        else:
            results = 'Nothing'

    log.debug("Received results")

    return results
