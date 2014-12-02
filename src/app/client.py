from SPARQLWrapper import SPARQLWrapper2, JSON
import json
import logging
import requests
from app import app

log = app.logger
log.setLevel(logging.DEBUG)

SPARQL_ENDPOINT = "http://live.dbpedia.org/sparql"

sparql = SPARQLWrapper2(SPARQL_ENDPOINT)
# sparql.setReturnFormat(JSON)

labels = {}


def visit(url):
    log.debug("Starting query")
    sparql.setQuery("DESCRIBE <{}>".format(url))
    results = sparql.query().convert()
    log.debug("Received results")
    
    return results["results"]["bindings"]
    
    

