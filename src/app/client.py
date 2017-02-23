from SPARQLWrapper import SPARQLWrapper, JSON, XML, TURTLE
import json
import logging
import requests
import config
import rdfextras
import traceback
import glob
import string
rdfextras.registerplugins()
from rdflib import Dataset, URIRef
import rdflib.util
from threading import Thread

# from app import app
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

LOCAL_STORE = config.LOCAL_STORE
LOCAL_FILE = config.LOCAL_FILE

SPARQL_ENDPOINT_MAPPING = config.SPARQL_ENDPOINT_MAPPING

SPARQL_ENDPOINT = config.SPARQL_ENDPOINT
SPARQL_METHOD = config.SPARQL_METHOD

DEFAULT_BASE = config.DEFAULT_BASE

QUERY_RESULTS_LIMIT = config.QUERY_RESULTS_LIMIT
CUSTOM_PARAMETERS = config.CUSTOM_PARAMETERS
DEREFERENCE_EXTERNAL_URIS = config.DEREFERENCE_EXTERNAL_URIS

labels = {}

g = Dataset()


def load_file(filename):
    log.info("Loading {}...".format(filename))
    format = rdflib.util.guess_format(filename)
    g.load(filename, format=format)
    log.info("... done loading {}".format(filename))


def init():
    if LOCAL_STORE:
        log.info("Loading local file(s): {}".format(LOCAL_FILE))
        try:
            for filename in glob.glob(LOCAL_FILE):
                t = Thread(target=load_file, args=(filename,))
                t.start()
        except:
            log.error(traceback.format_exc())
            raise Exception(
                "Cannot guess file format for {} or could not load file".format(LOCAL_FILE))


def get_predicates(sparql, url):
    predicate_query = u"""
        SELECT DISTINCT ?p WHERE {{
            {{ <{url}> ?p [] . }}
            UNION
            {{ [] ?p <{url}> . }}
        }}
    """.format(url=url)

    sparql.setQuery(predicate_query)

    log.debug(predicate_query)

    try:
        sparql_results = list(sparql.query().convert()["results"]["bindings"])

        predicates = [r['p']['value'] for r in sparql_results]

        log.debug(predicates)
    except:
        log.warning("Could not determine related predicates, because there were no triples where {} occurs als subject or object".format(url))

        predicates = []

    return predicates


def visit(url, format='html', external=False):
    log.debug("Starting query")

    # If this uri is not in our namespace, and DEREFERENCE_EXTERNAL_URIS is true
    # We go out, and add the retrieved RDF to our local store
    if external and DEREFERENCE_EXTERNAL_URIS:
        dereference(url)

    if LOCAL_STORE:
        return visit_local(url, format=format)
    else:
        return visit_sparql(url, format=format)


# At this point, results for each URL are now neatly stored in order in
# 'results'

def get_sparql_endpoint(url):
    sparql = None
    for prefix, endpoint in SPARQL_ENDPOINT_MAPPING.items():
        if url.startswith(DEFAULT_BASE + prefix + '/') or url.startswith(prefix):
            sparql = SPARQLWrapper(endpoint)
            break
    if not sparql:
        sparql = SPARQLWrapper(SPARQL_ENDPOINT)
        log.debug("Will be using {}".format(SPARQL_ENDPOINT))

    sparql.setReturnFormat(JSON)
    sparql.setMethod(SPARQL_METHOD)
    log.debug("Using method {} for accessing the SPARQL endpoint".format(SPARQL_METHOD))

    for key, value in CUSTOM_PARAMETERS.items():
        sparql.addParameter(key, value)

    log.debug("Using endpoint URL: {}".format(sparql.endpoint))
    return sparql


def visit_sparql(url, format='html'):
    sparql = get_sparql_endpoint(url)
    predicates = get_predicates(sparql, url)

    if format == 'html':
        limit_fraction = QUERY_RESULTS_LIMIT / 3
        if len(predicates) > 1:
            predicate_query_limit_fraction = (
                limit_fraction * 2) / len(predicates)
        else:
            predicate_query_limit_fraction = limit_fraction * 2

        results = []

        def predicate_specific_sparql(query):
            sparql_endpoint = get_sparql_endpoint(url)
            log.debug(query)
            sparql_endpoint.setQuery(query)

            res = sparql_endpoint.query().convert()
            log.debug(res)

            results.extend(
                list(res["results"]["bindings"]))

        threads = []
        queries = []
        local_results = []
        for p in predicates:
            q = u"""SELECT DISTINCT ?s ?p ?o ?g WHERE {{
                {{
                GRAPH ?g {{
                    {{
                        <{url}> <{predicate}> ?o .
                        BIND(<{url}> as ?s)
                        BIND(<{predicate}> as ?p)
                    }} UNION {{
                        ?s <{predicate}> <{url}>.
                        BIND(<{url}> as ?o)
                        BIND(<{predicate}> as ?p)
                    }}
                }}
                }} UNION {{
                    {{
                        <{url}> <{predicate}> ?o .
                        BIND(<{url}> as ?s)
                        BIND(<{predicate}> as ?p)
                    }} UNION {{
                        ?s <{predicate}> <{url}>.
                        BIND(<{url}> as ?o)
                        BIND(<{predicate}> as ?p)
                    }}
                }}
            }} LIMIT {limit}""".format(url=url, predicate=p, limit=predicate_query_limit_fraction)

            process = Thread(target=predicate_specific_sparql, args=[q])
            process.start()
            threads.append(process)

        url_is_predicate_query = u"""SELECT DISTINCT ?s ?p ?o ?g WHERE {{
            {{
            GRAPH ?g {{
                ?s <{url}> ?o.
                BIND(<{url}> as ?p)
            }}
            }} UNION {{
                ?s <{url}> ?o.
                BIND(<{url}> as ?p)
            }}
        }} LIMIT {limit}""".format(url=url, limit=limit_fraction)

        process = Thread(target=predicate_specific_sparql,
                         args=[url_is_predicate_query])
        process.start()
        threads.append(process)

        # We now pause execution on the main thread by 'joining' all of our started threads.
        # This ensures that each has finished processing the urls.
        for process in threads:
            process.join()

        local_results = list(visit_local(url, format))
        results.extend(local_results)

    else:
        q = u"""
        CONSTRUCT {{
            ?s ?p ?o .
        }} WHERE {{
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
        }} LIMIT {limit} """.format(url=url, limit=QUERY_RESULTS_LIMIT)

        results = g.query(q)
    else:
        # q = u"DESCRIBE <{}>".format(url)

        q = u"""
        CONSTRUCT {{
            ?s ?p ?o .
        }} WHERE {{
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


def dereference(uri):
    uriref = URIRef(uri)

    if uriref not in g.graphs():
        resource_graph = g.graph(uriref)

        headers = {
            'Accept': 'text/turtle, application/x-turtle, application/rdf+xml, text/trig'}
        response = requests.get(uri, headers=headers)

        if response.status_code == 200:
            content_type = response.headers['content-type']

            if 'turtle' in content_type:
                f = 'turtle'
            elif 'rdf' in content_type:
                f = 'xml'
            elif 'n3' in content_type:
                f = 'n3'
            elif 'n-quads' in content_type:
                f = 'nquads'
            elif 'trig' in content_type:
                f = 'trig'
            elif 'json' in content_type:
                f = 'jsonld'
            else:
                f = None
                print "Format not recognised"

            if f is not None:
                # Parse the response into the graph with the given URI in our
                # local store Dataset
                resource_graph.parse(data=response.text, format=f)
        else:
            log.warning("URI did not return any recognisable result")


def query(query):
    return g.query(query)


def prepare_sunburst(uri, results):
    log.debug("Preparing sunburst")
    incoming = {}
    outgoing = {}

    for r in results:
        if r['s']['value'] == uri and r['o']['type'] not in ['literal','typed-literal']:
            # print "outgoing", r['s']['value'], r['p']['value'], r['o']['value']
            outgoing.setdefault(r['p']['value'], {}).setdefault('children', {})[r['o']['value']] = {
                "name": r['o']['value'],
                "size": 1000
            }
        elif r['o']['value'] == uri:
            # print "incoming", r['s']['value'], r['p']['value'], r['o']['value']
            incoming.setdefault(r['p']['value'], {}).setdefault('children', {})[r['s']['value']] = {
                "name": r['s']['value'],
                "size": 1000
            }

    incoming_array = []
    for pk, pv in incoming.items():
        edge_array = []
        for sk, sv in pv['children'].items():
             edge_array.append(sv)
        incoming_array.append({
            'name': pk,
            'children': edge_array
        })

    outgoing_array = []
    for pk, pv in outgoing.items():
        edge_array = []
        for ok, ov in pv['children'].items():
             edge_array.append(ov)
        outgoing_array.append({
            'name': pk,
            'children': edge_array
        })

    return {'name': uri, 'children': incoming_array}, {'name': uri, 'children': outgoing_array}
