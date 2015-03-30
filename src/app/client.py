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

SPARQL_ENDPOINT = config.SPARQL_ENDPOINT
QUERY_RESULTS_LIMIT = config.QUERY_RESULTS_LIMIT

sparql = SPARQLWrapper(SPARQL_ENDPOINT)


labels = {}


def visit(url, format='html'):
    log.debug("Starting query")
    
    
    if format == 'html': 
        q = u"""SELECT DISTINCT ?s ?p ?o WHERE {{
            {{
                <{url}> ?p ?o .
                BIND(<{url}> as ?s)
            }} UNION {{
                ?s ?p <{url}>.
                BIND(<{url}> as ?o)
            }}
        }} LIMIT {limit}""".format(url=url, limit=QUERY_RESULTS_LIMIT)

        log.debug(q)

        sparql.setQuery(q)
        
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        
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
    
    

