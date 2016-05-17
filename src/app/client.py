from SPARQLWrapper import SPARQLWrapper, JSON, XML, TURTLE
import json
import logging
import requests
import config
from app import app
import rdfextras
rdfextras.registerplugins()

log = app.logger
log.setLevel(logging.DEBUG)

SPARQL_ENDPOINT_MAPPING = config.SPARQL_ENDPOINT_MAPPING

SPARQL_ENDPOINT = config.SPARQL_ENDPOINT

DEFAULT_BASE = config.DEFAULT_BASE

QUERY_RESULTS_LIMIT = config.QUERY_RESULTS_LIMIT
CUSTOM_PARAMETERS = config.CUSTOM_PARAMETERS

labels = {}


def visit(url, format='html'):
    log.debug("Starting query")

    sparql = None
    for prefix, endpoint in SPARQL_ENDPOINT_MAPPING.items():
        if url.startswith(DEFAULT_BASE + prefix + '/'):
            sparql = SPARQLWrapper(endpoint)
            break
    if not sparql:
        sparql = SPARQLWrapper(SPARQL_ENDPOINT)
        log.debug("Will be using {}".format(SPARQL_ENDPOINT))

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

        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        log.debug(results)
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
        else :
            results = 'Nothing'

    log.debug("Received results")

    return results
