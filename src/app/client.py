from SPARQLWrapper import SPARQLWrapper, JSON, XML, TURTLE
import json
import logging
import requests
from app import app
import rdfextras
rdfextras.registerplugins()

log = app.logger
log.setLevel(logging.DEBUG)

SPARQL_ENDPOINT = "http://live.dbpedia.org/sparql"

sparql = SPARQLWrapper(SPARQL_ENDPOINT)


labels = {}


def visit(url, format='html'):
    log.debug("Starting query")
    
    sparql.setQuery(u"DESCRIBE <{}>".format(url))
    
    print u"Format: " + format
    
    
    if format == 'html': 
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
    elif format == 'jsonld':
        sparql.setReturnFormat(XML)
        results = sparql.query().convert().serialize(format='json-ld')
    elif format == 'rdfxml':
        sparql.setReturnFormat(XML)
        results = sparql.query().convert().serialize(format='pretty-xml')
    elif format == 'turtle':
        sparql.setReturnFormat(XML)
        results = sparql.query().convert().serialize(format='turtle')
    
    log.debug("Received results")
    
    return results
    
    

