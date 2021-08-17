from flask import render_template, request, jsonify, make_response, redirect, url_for, abort
from werkzeug.http import parse_accept_header
import logging
from client import visit, query, init, prepare_sunburst, remote_query
from config import *
import traceback
from rdflib import URIRef, Literal, BNode

from app import app, cache
from datetime import datetime
print "views", datetime.now().isoformat()

log = app.logger
log.setLevel(logging.DEBUG)


def make_cache_key(*args, **kwargs):
    path = request.path
    args = str(hash(frozenset(request.args.items())))
    return (path + args).encode('utf-8')

def localize_rdflib_result(resource):
    resource_result = {}

    resource_string = unicode(resource)

    resource_result['value'] = resource_string
    if isinstance(resource, URIRef) or isinstance(resource, BNode):
        resource_result['type'] = 'uri'

        if resource_string.startswith(DEFAULT_BASE) and '#' not in resource_string:
            resource_result['local'] = resource_string.replace(DEFAULT_BASE, LOCAL_SERVER_NAME)
        elif BROWSE_EXTERNAL_URIS or '#' in resource_string:
            resource_result['local'] = url_for('browse', uri=resource_string, _external=True)
        else:
            resource_result['local'] = resource_string
    elif isinstance(resource, Literal):
        resource_result['type'] = 'literal'

    return resource_result


def localize_results(results):
    log.debug("Localizing results")
    local_results = []

    if LOCAL_STORE:
        log.debug("Transforming RDFLib results")

        for (s, p, o, graph) in results:
            local_result = {}
            local_result['s'] = localize_rdflib_result(s)
            local_result['p'] = localize_rdflib_result(p)
            local_result['o'] = localize_rdflib_result(o)
            local_result['g'] = localize_rdflib_result(graph)
            local_results.append(local_result)
    else:
        for result in results:
            local_result = {}
            for v in ['s', 'p', 'o', 'g']:
                if v not in result:
                    local_uri = "<urn:default>"
                    local_result[v] = {}
                    local_result[v]['type'] = 'uri'
                    local_result[v]['value'] = local_uri
                    local_result[v]['local'] = local_uri
                elif result[v]['type'] == 'uri' and result[v]['value'].startswith(DEFAULT_BASE) and '#' not in result[v]['value']:
                    local_uri = result[v]['value'].replace(DEFAULT_BASE, LOCAL_SERVER_NAME)
                    local_result[v] = result[v]
                    local_result[v]['local'] = local_uri
                elif BROWSE_EXTERNAL_URIS or '#' in result[v]['value']:
                    local_uri = url_for('browse', uri=result[v]['value'], _external=True)
                    local_result[v] = result[v]
                    local_result[v]['local'] = local_uri
                else:
                    local_result[v] = result[v]
                    local_result[v]['local'] = result[v]['value']

            local_results.append(local_result)

    return local_results


def document(resource_suffix=""):
    if resource_suffix:
        uri = u"{}/{}".format(DEFAULT_BASE, resource_suffix)
    else:
        uri = START_URI

    log.debug('The URI we will use is: ' + uri)

    if 'Accept' in request.headers:
        mimetype = parse_accept_header(request.headers['Accept']).best
        log.debug("Looking for mime type '{}'".format(mimetype))
    else:
        log.debug("No accept header, using 'text/html'")
        mimetype = 'text/html'

    try:
        if mimetype in ['text/html', 'application/xhtml_xml','*/*']:
            local_resource_uri = u"{}/{}".format(LOCAL_SERVER_NAME,resource_suffix)
            results = visit(uri, format='html')
            local_results = localize_results(results)

            return render_template('resource.html', local_resource=local_resource_uri, resource=uri, results=local_results, local=LOCAL_STORE, preflabel=PREFLABEL_SERVICE)
        elif mimetype in ['application/json']:
            response = make_response(visit(uri,format='jsonld'),200)
            response.headers['Content-Type'] = 'application/json'
            return response
        elif mimetype in ['application/rdf+xml','application/xml']:
            response = make_response(visit(uri,format='rdfxml'),200)
            response.headers['Content-Type'] = 'application/rdf+xml'
            return response
        elif mimetype in ['application/x-turtle','text/turtle']:
            response = make_response(visit(uri,format='turtle'),200)
            response.headers['Content-Type'] = 'text/turtle'
            return response
    except Exception as e:
        log.error(e)
        log.error(traceback.format_exc())
        return make_response("Incorrect mimetype or other error", 400)



@app.route('/favicon.ico')
@cache.cached(timeout=CACHE_TIMEOUT, key_prefix=make_cache_key)
def icon():
    return jsonify({'error': "no icon"})


@app.route('/graph')
@cache.cached(timeout=CACHE_TIMEOUT, key_prefix=make_cache_key)
def graph():
    uri = request.args.get('uri', None)
    return render_template('graph.html', uri=uri, service_url="{}/graph/json".format(LOCAL_SERVER_NAME), local=LOCAL_STORE)


@app.route('/graph/json')
@cache.cached(timeout=CACHE_TIMEOUT, key_prefix=make_cache_key)
def graph_json():
    uri = request.args.get('uri', None)

    # Visit the selected URI up to a depth of 2
    results = visit(uri, format='html', depth=SUNBURST_DEPTH)
    local_results = localize_results(results)
    # graph = prepare_graph(local_results)
    labels, incoming, outgoing = prepare_sunburst(uri, local_results, SUNBURST_DEPTH)

    return jsonify({'labels': labels, 'incoming': incoming, 'outgoing': outgoing})


@app.route('/browse')
@cache.cached(timeout=CACHE_TIMEOUT, key_prefix=make_cache_key)
def browse():
    uri = request.args.get('uri', None)

    if uri is None:
        return document()
    else:
        if 'Accept' in request.headers:
            mimetype = parse_accept_header(request.headers['Accept']).best
        else:
            log.debug("No accept header, using 'text/html'")
            mimetype = 'text/html'

        try:
            if mimetype in ['text/html', 'application/xhtml_xml', '*/*']:
                try:
                    results = visit(uri, format='html', external=True)
                except: #when the uri is a javascript injection (or any other illegal string) this will fail and the uri shouldn't be send to the response
                    return render_template('resource.html', local_resource='http://bla', resource="error in sparql query", results=[], local=LOCAL_STORE, preflabel=PREFLABEL_SERVICE)
                local_results = localize_results(results)
                if local_results == []: #when there are no results the uri might be a javascript injection and the uri shouldn't be send to the response
                    uri = "unknown uri"
                return render_template('resource.html', local_resource='http://bla', resource=uri, results=local_results, local=LOCAL_STORE, preflabel=PREFLABEL_SERVICE)
            elif mimetype in ['application/json']:
                response = make_response(visit(uri, format='jsonld', external=True), 200)
                response.headers['Content-Type'] = 'application/json'
                return response
            elif mimetype in ['application/rdf+xml', 'application/xml']:
                response = make_response(visit(uri, format='rdfxml', external=True), 200)
                response.headers['Content-Type'] = 'application/rdf+xml'
                return response
            elif mimetype in ['application/x-turtle', 'text/turtle']:
                response = make_response(visit(uri, format='turtle', external=True), 200)
                response.headers['Content-Type'] = 'text/turtle'
                return response
        except Exception as e:
            log.error(e)
            log.error(traceback.format_exc())
            return traceback.format_exc()


@app.route('/<path:resource_suffix>')
@cache.cached(timeout=CACHE_TIMEOUT, key_prefix=make_cache_key)
def redirect(resource_suffix):
    log.debug("Retrieved resource_suffix " + resource_suffix)
    if resource_suffix.startswith('{}/'.format(LOCAL_DOCUMENT_INFIX)):
        log.debug("DOC Retrieved resource_suffix " + resource_suffix)
        return document(resource_suffix[(len(LOCAL_DOCUMENT_INFIX)+1):])
    else:
        log.debug("ID Retrieved resource_suffix " + resource_suffix)
        if resource_suffix.startswith('http'):
            abort(500)

        resource_suffix = u"{}/{}".format(LOCAL_DOCUMENT_INFIX,resource_suffix)

        redirect_url = url_for('redirect',resource_suffix=resource_suffix,_external=True)

        response = make_response('Moved permanently',303)
        response.headers['Location'] = redirect_url
        response.headers['Accept'] = request.headers['Accept']

        return response


@app.route('/sparql')
@cache.cached(timeout=CACHE_TIMEOUT, key_prefix=make_cache_key)
def sparql():
    if config.LOCAL_STORE:
        log.info('Querying local store')
        return render_template('sparql.html', endpoint=url_for('local_sparql'))
    else:
        log.info('Querying remote endpoints')
        return render_template('sparql.html', endpoint=url_for('remote_sparql'))


@cache.cached(timeout=CACHE_TIMEOUT, key_prefix=make_cache_key)
@app.route('/remote/sparql', methods=['POST', 'GET'])
def remote_sparql():
    """This is a wrapper around remote SPARQL endpoints to allow querying from JavaScript (YASQE/YASR)"""
    if request.method == 'POST':
        q = request.form['query']
    else:
        q = request.args.get('query', '')

    log.debug(q)
    results = remote_query(q, accept=request.headers.getlist('accept'))
    log.debug(results)

    if isinstance(results, dict):
        return jsonify(results)
    else:
        return results


@app.route('/local/sparql', methods=['POST'])
@cache.cached(timeout=CACHE_TIMEOUT, key_prefix=make_cache_key)
def local_sparql():
    if config.LOCAL_STORE:
        log.debug("Querying local store")
        q = request.form['query']
        log.debug(q)
        results = query(q).serialize(format='json')
        log.debug(results)
        return results
    else:
        log.warning("No local store configured")


@app.route('/')
@cache.cached(timeout=CACHE_TIMEOUT, key_prefix=make_cache_key)
def index():
    if len(START_LOCAL_NAME) > 0:

        redirect_url = url_for('redirect',resource_suffix=START_LOCAL_NAME,_external=True,_scheme="http")
        log.debug("ROOT Redirecting to "+redirect_url)

        response = make_response('Moved permanently',303)
        response.headers['Location'] = redirect_url
        response.headers['Accept'] = request.headers['Accept']

        return response
    else:
        return document()


@app.route('/reload')
def reload():
    # Refresh the local store by reloading the files
    init()

    # Browse the uri passed in the GET request (if none, just show the START_URI)
    return browse()
