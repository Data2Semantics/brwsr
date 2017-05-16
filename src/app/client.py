from SPARQLWrapper import SPARQLWrapper, JSON, XML
from threading import Thread
import logging
import requests
from config import *
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

# For backwards compatibility: some configurations do not specify the
# SPARQL_METHOD parameter
try:
    if SPARQL_METHOD is not None:
        pass
except:
    SPARQL_METHOD = 'GET'


# Properties that are typically used to give the label for a resource
# Used to render the sunburst
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


def load_data(data, format="json-ld"):
    g.parse(data=data, format=format)


def init():
    if LOCAL_STORE:
        log.info("Loading local file(s): {}".format(LOCAL_FILE))
        try:
            files = glob.glob(LOCAL_FILE)
            if len(files) == 0:
                log.error(
                    "No files match the UNIX file pattern specified in {}, or the pattern is invalid.".format(LOCAL_FILE))
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


def visit(url, format='html', external=False, depth=1):
    log.debug("Starting query")

    # If this uri is not in our namespace, and DEREFERENCE_EXTERNAL_URIS is true
    # We go out, and add the retrieved RDF to our local store
    if external and DEREFERENCE_EXTERNAL_URIS:
        log.debug("Dereferencing external uri")
        dereference(url)

    if LOCAL_STORE:
        return visit_local(url, format=format, depth=depth)
    else:
        return visit_sparql(url, format=format, depth=depth)


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
    po = requests.get(DRUID_STATEMENTS_URL, headers={
                      'Accept': 'text/json'}, params={'subject': url}).json()
    sp = requests.get(DRUID_STATEMENTS_URL, headers={
                      'Accept': 'text/json'}, params={'object': url}).json()
    so = requests.get(DRUID_STATEMENTS_URL, headers={
                      'Accept': 'text/json'}, params={'predicate': url}).json()

    druid_results = []
    druid_results.extend(po)
    druid_results.extend(sp)
    druid_results.extend(so)

    sparql_results = druid_to_sparql_results(druid_results)

    if format == 'html':
        return sparql_results
    else:
        return 'Not supported'


def retrieve_ldf_results(url):
    log.debug("Visiting Linked Data Fragments at {}".format(LDF_STATEMENTS_URL))
    po = requests.get(LDF_STATEMENTS_URL, headers={
                      'Accept': 'application/json'}, params={'subject': url}).content
    sp = requests.get(LDF_STATEMENTS_URL, headers={
                      'Accept': 'application/json'}, params={'object': url}).content
    so = requests.get(LDF_STATEMENTS_URL, headers={
                      'Accept': 'application/json'}, params={'predicate': url}).content

    load_data(po)
    load_data(sp)
    load_data(so)


def visit_sparql(url, format='html', depth=1):
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

        if LDF_STATEMENTS_URL is not None:
            retrieve_ldf_results(url)

        # We also add local results (result of dereferencing)
        local_results = list(visit_local(url, format))

        results.extend(local_results)

        # If a Druid statements URL is specified, we'll try to receive it as
        # well
        if DRUID_STATEMENTS_URL is not None:
            results.extend(visit_druid(url, format))

        if depth > 1:
            # If depth is larger than 1, we proceed to extend the results with the results of
            # visiting all object resources for every triple in the resultset.
            newresults = []

            objects = set([r['o']['value'] for r in results if r['o']['value'] != url and r['o']['type']=='uri'])

            for o in objects:
                newresults.extend(
                    visit(o, format=format, depth=depth - 1))

            results.extend(newresults)

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


def visit_local(url, format='html', depth=1):
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


def remote_query(query, accept=['application/sparql-results+json', 'text/json', 'application/json']):
    endpoints = SPARQL_ENDPOINT_MAPPING.values()
    if SPARQL_ENDPOINT is not None:
        endpoints.append(SPARQL_ENDPOINT)

    log.debug(endpoints)

    header = {'Accept': ', '.join(accept)}
    params = {'query': query}

    log.debug(header)

    results = None
    for endpoint in endpoints:
        response = requests.get(endpoint, headers=header, params=params)

        try:
            # The response is a JSON SPARQL result
            response_json = response.json()
            log.debug(response_json)
            if 'results' in response_json:
                # Add provenance information to the bindings
                bindings = []
                for b in response_json['results']['bindings']:
                    b['endpoint'] = {'value': endpoint, 'type': 'uri'}
                    bindings.append(b)

                if results is None:
                    results = response_json
                    results['head']['vars'].append('endpoint')
                    results['results']['bindings'] = bindings
                else:
                    results['results']['bindings'].extend(bindings)
            else:
                raise Exception("JSON but not SPARQL results")
        except:
            # The response is the result of a CONSTRUCT or DESCRIBE or ASK
            # query
            if results is None:
                results = '\n# ===\n# Result from {}\n# ===\n'.format(
                    endpoint) + response.content
            else:
                results += '\n# ===\n# Result from {}\n# ===\n'.format(
                    endpoint) + response.content

    return results


def traverse(uri, results, source='s', target='o', visited={}, depth=0, maxdepth=2):
    """Traverse the results and build a sunburst JSON graph in the direction indicated by source/target

    i.e. to build all outgoing edges, specify 's' and 'o', respectively
    otherwise, specify 'o' and 's'.
    """

    log.info("{} Traversing from {} to {}".format(" "*depth*10, source, target))
#     log.debug(visited)
    if uri in visited.keys():
        log.debug(u"{} Already visited {}".format(" "*depth*10, uri))
        return visited[uri], visited
    elif depth >= maxdepth:
        log.debug(u"Maximum depth exceeded")
        return [], visited

    log.debug(u"{} Visiting {}".format(" "*depth*10, uri))


    edges = {}
    edge_array = []

    for r in results:
        if r[source]['value'] != uri:
            # Continue to next result if this result does not apply to the current node
            continue

        children = []
        if r[target]['type'] not in ['literal', 'typed-literal']:
            log.debug(u"{} Found child {}".format(" "*depth*10, r[target]['value']))

            children, visited = traverse(r[target]['value'], results, source=source, target=target, visited=visited, depth=depth+1)

            node = {
                "name": r[target]['value'],
                "size": 1000,
            }

            if len(children) > 0:
                node["children"] = children

            edges.setdefault(r['p']['value'], {}).setdefault('children', {})[r[target]['value']] = node

    # Iterate over the edges, to rewrite to arrays of dictionaries
    log.debug(u"{} Rewriting children dictionary to array for {}".format(" "*depth*10, uri))
    for pk, pv in edges.items():
        child_array = []
        for sk, sv in pv['children'].items():
            child_array.append(sv)
        edge_array.append({
            'name': pk,
            'children': child_array
        })

    visited[uri] = edge_array
    return edge_array, visited


def prepare_sunburst(uri, results, maxdepth=1):
    log.debug(u"Preparing sunburst for {}".format(uri))

    # Traverse outgoing edges
    outgoing_array, v = traverse(uri, results, source='s', target='o', visited={}, maxdepth=maxdepth)
    # Traverse incoming edges
    incoming_array, v = traverse(uri, results, source='o', target='s', visited={}, maxdepth=maxdepth)

    labels = set()
    # Find the labels for this resource
    for r in results:
        if r['s']['value'] == uri and r['p']['value'] in label_properties:
            labels.add(r['o']['value'])

    return list(labels), {'name': uri, 'children': incoming_array}, {'name': uri, 'children': outgoing_array}

    
