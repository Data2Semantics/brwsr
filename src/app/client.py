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
    predicate_query = """
        SELECT DISTINCT ?p WHERE {{
            {{ <{url}> ?p [] . }}
            UNION
            {{ [] ?p <{url}> . }}
        }}
    """.format(url=url)

    sparql.setQuery(predicate_query)

    sparql_results = list(sparql.query().convert()["results"]["bindings"])

    predicates = [r['p']['value'] for r in sparql_results]

    log.debug(predicates)

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

def get_sparql_endpoint():
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

    return sparql


def visit_sparql(url, format='html'):
    sparql = get_sparql_endpoint()
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
            sparql_endpoint = get_sparql_endpoint()
            log.debug(query)
            sparql_endpoint.setQuery(query)
            results.extend(
                list(sparql_endpoint.query().convert()["results"]["bindings"]))

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
        }} LIMIT {limit}""".format(url=url, limit=QUERY_RESULTS_LIMIT)

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


def prepare_graph(results):
    color_array = ['#9edae5', '#ffbb78', '#dbdb8d', '#9edae5', '#2ca02c', '#9467bd', '#c5b0d5', '#c5b0d5', '#98df8a', '#c7c7c7', '#f7b6d2', '#d62728', '#e377c2', '#ff9896', '#bcbd22', '#ffbb78', '#2ca02c', '#98df8a', '#c7c7c7', '#17becf', '#17becf', '#7f7f7f', '#dbdb8d', '#bcbd22', '#c49c94', '#f7b6d2', '#aec7e8', '#2ca02c', '#e377c2', '#ffbb78', '#c5b0d5', '#98df8a', '#9467bd', '#bcbd22', '#ff7f0e', '#ff9896', '#ff9896', '#aec7e8', '#1f77b4', '#aec7e8', '#8c564b', '#ff7f0e', '#9467bd', '#ffbb78', '#d62728',
                               '#9467bd', '#e377c2', '#c7c7c7', '#d62728', '#8c564b', '#7f7f7f', '#7f7f7f', '#f7b6d2', '#9edae5', '#dbdb8d', '#d62728', '#1f77b4', '#7f7f7f', '#1f77b4', '#c5b0d5', '#9467bd', '#c49c94', '#8c564b', '#8c564b', '#ff9896', '#c5b0d5', '#e377c2', '#1f77b4', '#c7c7c7', '#d62728', '#aec7e8', '#f7b6d2', '#17becf', '#98df8a', '#17becf', '#c49c94', '#98df8a', '#2ca02c', '#ff7f0e', '#bcbd22', '#9edae5', '#ffbb78', '#2ca02c', '#dbdb8d', '#aec7e8', '#ff9896', '#c49c94', '#ff7f0e', '#1f77b4', '#ff7f0e', '#8c564b']

    concept_mapping = {}

    concept_set = set()

    concept_uris = {}
    concept_types = {}

    namespaces = set()
    uri_ns_map = {}

    for result in results:
        if result['o']['type'] == 'literal':
            log.debug('Skipping literal objects')
            continue

        s = result['s']['value']
        o = result['o']['value']

        s_base = string.join(s.split('/')[:6], '/')
        uri_ns_map[s] = s_base
        o_base = string.join(o.split('/')[:6], '/')
        uri_ns_map[o] = o_base
        namespaces.add(s_base)
        namespaces.add(o_base)

        concept_mapping.setdefault(s, {}).setdefault(o, 0)
        concept_mapping.setdefault(o, {}).setdefault(s, 0)

        concept_mapping[s][o] += 1
        concept_mapping[o][s] += 1

        concept_set.add(s)
        concept_set.add(o)

    namespaces = list(namespaces)
    ns_color_map = {}
    for ns in namespaces:
        i = namespaces.index(ns)
        ns_color_map[ns] = color_array[i]

    concepts = list(concept_set)

    concept_matrix = range(0, len(concepts))
    log.debug(concept_matrix)

    total = 0
    for c1 in concepts:
        log.debug(c1)
        if c1 not in concept_mapping:
            log.debug("{} not in concept mapping as origin".format(c1))
            continue

        concept_row = range(0, len(concepts))

        for c2 in concepts:
            if c2 in concept_mapping[c1]:
                concept_row[concepts.index(c2)] = concept_mapping[c1][c2]
                total += concept_mapping[c1][c2]
            else:
                concept_row[concepts.index(c2)] = 0

        concept_matrix[concepts.index(c1)] = concept_row

    percent_concept_matrix = range(0, len(concepts))

    i = 0
    for row in concept_matrix:
        log.debug(row)
        percent_concept_row = range(0, len(concepts))

        j = 0
        for cell in row:
            percent_concept_row[j] = float(cell) / float(total)

            j += 1

        percent_concept_matrix[i] = percent_concept_row

        i += 1

    concept_list = []

    for c in concepts:
        c_dict = {'name': c, 'type': 'uri', 'color': ns_color_map[uri_ns_map[c]], 'uri': c}
        concept_list.append(c_dict)

    return percent_concept_matrix, concept_list
