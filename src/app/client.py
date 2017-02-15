from SPARQLWrapper import SPARQLWrapper, JSON, XML, TURTLE
import json
import logging
import requests
import config
import rdfextras
import traceback
import glob
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
            raise Exception("Cannot guess file format for {} or could not load file".format(LOCAL_FILE))


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




# At this point, results for each URL are now neatly stored in order in 'results'

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
        # q = u"""SELECT DISTINCT ?s ?p ?o ?g WHERE {{
        #     {{
        #     GRAPH ?g {{
        #         {{
        #             <{url}> ?p ?o .
        #             BIND(<{url}> as ?s)
        #         }} UNION {{
        #             ?s ?p <{url}>.
        #             BIND(<{url}> as ?o)
        #         }} UNION {{
        #             ?s <{url}> ?o.
        #             BIND(<{url}> as ?p)
        #         }}
        #     }}
        #     }} UNION {{
        #         {{
        #             <{url}> ?p ?o .
        #             BIND(<{url}> as ?s)
        #         }} UNION {{
        #             ?s ?p <{url}>.
        #             BIND(<{url}> as ?o)
        #         }} UNION {{
        #             ?s <{url}> ?o.
        #             BIND(<{url}> as ?p)
        #         }}
        #     }}
        # }} LIMIT {limit}""".format(url=url, limit=QUERY_RESULTS_LIMIT)

        limit_fraction = QUERY_RESULTS_LIMIT/3
        if len(predicates) > 1:
            predicate_query_limit_fraction = (limit_fraction*2)/len(predicates)
        else:
            predicate_query_limit_fraction = limit_fraction*2

        results = []

        def predicate_specific_sparql(query):
            sparql_endpoint = get_sparql_endpoint()
            log.debug(query)
            sparql_endpoint.setQuery(query)
            results.extend(list(sparql_endpoint.query().convert()["results"]["bindings"]))


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

        process = Thread(target=predicate_specific_sparql, args=[url_is_predicate_query])
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

        headers = {'Accept': 'text/turtle, application/x-turtle, application/rdf+xml, text/trig'}
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
                # Parse the response into the graph with the given URI in our local store Dataset
                resource_graph.parse(data=response.text, format=f)
        else:
            log.warning("URI did not return any recognisable result")


def query(query):
    return g.query(query)


def prepare_graph(concept_uri):

    query = """SELECT ?c1 ?c2 WHERE {
        {
            <{{concept_uri}}> ?p1 ?c1 .
        } UNION {
            ?c1 ?p2 ?c2 .
        }
        FILTER (?c1 != ?c2)
    }""".format(concept_uri)


    results = query(q)

    concept_mapping = {}

    concept_set = set()

    concept_uris = {}
    concept_types = {}

    for result in results:
        c1 = uri_to_label(result['c1']['value'])
        c1t = uri_to_label(result['c1t']['value'])
        c2 = uri_to_label(result['c2']['value'])
        c2t = uri_to_label(result['c2t']['value'])


        # Add the mapping between c1 and c2 in both directions
        concept_mapping.setdefault(c1,{}).setdefault(c2,0)
        concept_mapping.setdefault(c2,{}).setdefault(c1,0)

        concept_mapping[c1][c2] += 1
        concept_mapping[c2][c1] += 1

        concept_set.add(c1)
        concept_set.add(c2)

        concept_types[c1] = c1t
        concept_types[c2] = c2t

        concept_uris[c1] = result['c1']['value'];
        concept_uris[c2] = result['c2']['value'];





    concepts = list(concept_set)

    concept_matrix = range(0,len(concepts))

    total = 0
    for c1 in concepts:
        concept_row = range(0,len(concepts))

        for c2 in concepts:
            if c2 in concept_mapping[c1]:
                concept_row[concepts.index(c2)] = concept_mapping[c1][c2]
                total += concept_mapping[c1][c2]
            else :
                concept_row[concepts.index(c2)] = 0

        concept_matrix[concepts.index(c1)] = concept_row

    percent_concept_matrix = range(0, len(concepts))

    i = 0
    for row in concept_matrix :

        percent_concept_row = range(0, len(concepts))

        j = 0
        for cell in row :
            percent_concept_row[j] = float(cell)/float(total)

            j += 1

        percent_concept_matrix[i] = percent_concept_row

        i += 1


    concept_dictionary = {}

    concept_list = []

    for c in concepts :
        c_dict = {'name': c.replace("'",""), 'type': concept_types[c].lower(), 'color': concept_type_color_dict[concept_types[c].lower()], 'uri' : concept_uris[c] }
        concept_list.append(c_dict)


    return percent_concept_matrix, concept_list
