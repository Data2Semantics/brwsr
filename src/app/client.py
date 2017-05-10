from SPARQLWrapper import SPARQLWrapper, JSON, XML
from threading import Thread
import logging
import requests
import config
import rdfextras
import traceback
import glob
import re
rdfextras.registerplugins()
import rdflib
from rdflib import Dataset, URIRef, RDFS

# from app import app

from datetime import datetime
print "client", datetime.now().isoformat()

# log = app.logger
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

LOCAL_STORE = config.LOCAL_STORE
LOCAL_FILE = config.LOCAL_FILE

SPARQL_ENDPOINT_MAPPING = config.SPARQL_ENDPOINT_MAPPING
SPARQL_ENDPOINT = config.SPARQL_ENDPOINT

DRUID_STATEMENTS_URL = config.DRUID_STATEMENTS_URL

# For backwards compatibility: some configurations do not specify the
# SPARQL_METHOD parameter
try:
    SPARQL_METHOD = config.SPARQL_METHOD
except:
    SPARQL_METHOD = 'GET'

DEFAULT_BASE = config.DEFAULT_BASE

QUERY_RESULTS_LIMIT = config.QUERY_RESULTS_LIMIT
CUSTOM_PARAMETERS = config.CUSTOM_PARAMETERS
DEREFERENCE_EXTERNAL_URIS = config.DEREFERENCE_EXTERNAL_URIS

label_properties = ['http://www.w3.org/2004/02/skos/core#prefLabel',
                    'http://www.w3.org/2004/02/skos/core#altLabel',
                    str(RDFS['label']),
                    'http://xmlns.com/foaf/0.1/name',
                    'http://purl.org/dc/elements/1.1/title',
                    'http://purl.org/dc/terms/title']


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
            files = glob.glob(LOCAL_FILE)
            if len(files) == 0:
                log.error("No files match the UNIX file pattern specified in {}, or the pattern is invalid.".format(LOCAL_FILE))
                return
            for filename in files:
                log.info("Trying to load file: {}".format(filename))
                t = Thread(target=load_file, args=(filename,))
                t.start()
        except:
            log.error(traceback.format_exc())
            raise Exception(
                "Cannot guess file format for {} or could not load file".format(LOCAL_FILE))


def get_predicates(sparqls, url):
    predicate_query = u"""
        SELECT DISTINCT ?p WHERE {{
            {{ <{url}> ?p [] . }}
            UNION
            {{ [] ?p <{url}> . }}
        }}
    """.format(url=url)

    predicates = []
    for s in sparqls:
        s.setQuery(predicate_query)
        log.debug(predicate_query)

        try:
            sparql_results = list(s.query().convert()["results"]["bindings"])

            predicates.extend([r['p']['value'] for r in sparql_results])

            # log.debug(predicates)
        except:
            log.warning(
                "Could not determine related predicates, because there were no triples where {} occurs als subject or object".format(url))

    return predicates


def visit(url, format='html', external=False):
    log.debug("Starting query")

    # If this uri is not in our namespace, and DEREFERENCE_EXTERNAL_URIS is true
    # We go out, and add the retrieved RDF to our local store
    if external and DEREFERENCE_EXTERNAL_URIS:
        log.debug("Dereferencing external uri")
        dereference(url)

    if LOCAL_STORE:
        return visit_local(url, format=format)
    else:
        return visit_sparql(url, format=format)


def get_sparql_endpoints(url):
    sparql = None
    sparqls = []
    for prefix, endpoint in SPARQL_ENDPOINT_MAPPING.items():
        # If the URL starts with the default base + the prefix, or
        # If the URL starts with the prefix itself, or
        # If the URL matches the regular expression in the prefix,
        # AND if the endpoint is not already in the list...
        if (url.startswith(DEFAULT_BASE + prefix + '/') or url.startswith(prefix) or re.match(prefix, url) is not None) and endpoint not in sparqls:
            s = SPARQLWrapper(endpoint)
            sparqls.append(s)

    # Also add the default endpoint
    if SPARQL_ENDPOINT is not None:
        sparql = SPARQLWrapper(SPARQL_ENDPOINT)
        sparqls.append(sparql)

    log.debug("Will be using the following endpoints: {}".format(
        [s.endpoint for s in sparqls]))

    for s in sparqls:
        s.setReturnFormat(JSON)
        s.setMethod(SPARQL_METHOD)
        for key, value in CUSTOM_PARAMETERS.items():
            sparql.addParameter(key, value)

    return sparqls


def druid_to_sparql_results(druid_results):
    sparql_results = []
    for triple in druid_results:
        print triple
        ds, dp, do = tuple(triple)

        if ds['termType'] == u'NamedNode':
            s = {'value': ds['value'], 'type': 'uri'}
        elif ds['termType'] == u'BlankNode':
            s = {'value': ds['value'], 'type': 'bnode'}

        p = {'value': dp['value'], 'type': 'uri'}

        if do['termType'] == u'NamedNode':
            o = {'value': do['value'], 'type': 'uri'}
        elif do['termType'] == u'BlankNode':
            o = {'value': do['value'], 'type': 'bnode'}
        elif do['termType'] == u'Literal':
            o = {'value': do['value'], 'type': 'literal'}
            if 'datatype' in do:
                o['datatype'] = do['datatype']
            if 'language' in do:
                o['lang'] = do['language']

        sparql_results.append({'s': s, 'p': p, 'o': o})

    return sparql_results


def visit_druid(url, format='html'):
    log.debug("Visiting druid at {}".format(DRUID_STATEMENTS_URL))
    po = requests.get(DRUID_STATEMENTS_URL, headers={'Accept': 'text/json'}, params={'subject': url} ).json()
    sp = requests.get(DRUID_STATEMENTS_URL, headers={'Accept': 'text/json'}, params={'object': url} ).json()
    so = requests.get(DRUID_STATEMENTS_URL, headers={'Accept': 'text/json'}, params={'predicate': url} ).json()

    druid_results = []
    druid_results.extend(po)
    druid_results.extend(sp)
    druid_results.extend(so)

    sparql_results = druid_to_sparql_results(druid_results)

    if format == 'html':
        return sparql_results
    else:
        return 'Not supported'


def visit_sparql(url, format='html'):
    sparqls = get_sparql_endpoints(url)
    predicates = get_predicates(sparqls, url)

    if format == 'html':
        limit_fraction = QUERY_RESULTS_LIMIT / 3
        if len(predicates) > 1:
            predicate_query_limit_fraction = (
                limit_fraction * 2) / len(predicates)
        else:
            predicate_query_limit_fraction = limit_fraction * 2

        results = []

        def predicate_specific_sparql(sparql, query):
            log.debug(query)

            sparql.setQuery(query)
            res = sparql.query().convert()
            results.extend(
                list(res["results"]["bindings"]))

        threads = []
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

            for s in sparqls:
                # Start processes for each endpoint, for each predicate query
                process = Thread(target=predicate_specific_sparql, args=[s, q])
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

        for s in sparqls:
            process = Thread(target=predicate_specific_sparql,
                             args=[s, url_is_predicate_query])
            process.start()
            threads.append(process)

        # We now pause execution on the main thread by 'joining' all of our started threads.
        # This ensures that each has finished processing the urls.
        for process in threads:
            process.join()

        # We also add local results (result of dereferencing)
        local_results = list(visit_local(url, format))

        results.extend(local_results)

        # If a Druid statements URL is specified, we'll try to receive it as well
        if DRUID_STATEMENTS_URL is not None:
            results.extend(visit_druid(url, format))

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

        result_dataset = Dataset()

        for s in sparqls:
            s.setQuery(q)
            s.setReturnFormat(XML)

            result_dataset += s.query().convert()

        if format == 'jsonld':
            results = result_dataset.serialize(format='json-ld')
        elif format == 'rdfxml':
            s.setReturnFormat(XML)
            results = result_dataset.serialize(format='pretty-xml')
        elif format == 'turtle':
            s.setReturnFormat(XML)
            results = result_dataset.serialize(format='turtle')
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

        try:
            response = requests.get(uri, headers=headers, timeout=2)
        except:
            log.error(traceback.format_exc())
            return

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
                print "Format {} not recognised as valid RDF serialization format".format(content_type)

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

    labels = set()
    for r in results:
        log.debug(r['p']['value'])
        if r['s']['value'] == uri and r['p']['value'] in label_properties:
            labels.add(r['o']['value'])

        if r['s']['value'] == uri and r['o']['type'] not in ['literal', 'typed-literal']:
            # print "outgoing", r['s']['value'], r['p']['value'],
            # r['o']['value']
            outgoing.setdefault(r['p']['value'], {}).setdefault('children', {})[r['o']['value']] = {
                "name": r['o']['value'],
                "size": 1000
            }
        elif r['o']['value'] == uri:
            # print "incoming", r['s']['value'], r['p']['value'],
            # r['o']['value']
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

    return list(labels), {'name': uri, 'children': incoming_array}, {'name': uri, 'children': outgoing_array}
