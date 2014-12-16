from flask import render_template, g, request, jsonify, make_response, redirect, url_for, abort
from werkzeug.http import parse_accept_header
import logging
from urlparse import urljoin, urlsplit
from client import visit
import config
from app import app



log = app.logger
log.setLevel(logging.DEBUG)

DEFAULT_BASE = config.DEFAULT_BASE
LOCAL_DOCUMENT_INFIX = config.LOCAL_DOCUMENT_INFIX
LOCAL_SERVER_NAME = config.LOCAL_SERVER_NAME
START_LOCAL_NAME = config.START_LOCAL_NAME
START_URI = config.START_URI




def localize_results(results):
    log.debug("Localizing results")
    local_results = []
    
    for result in results:
        local_result = {}
        for v in ['s','p','o']:
            if result[v]['type'] == 'uri' and result[v]['value'].startswith(DEFAULT_BASE) :
                local_uri = result[v]['value'].replace(DEFAULT_BASE, LOCAL_SERVER_NAME)
                local_result[v] = result[v]
                local_result[v]['local'] = local_uri
            else :
                local_result[v] = result[v]
                local_result[v]['local'] = result[v]['value']
                
                
        local_results.append(local_result)
    
    return local_results
    


    

def document(resource_suffix):
    if resource_suffix :
        uri = u"{}/{}".format(DEFAULT_BASE,resource_suffix)
    else :
        uri = START_URI
    
    log.debug('The URI we will use is: ' + uri)    
        
    if 'Accept' in request.headers:
        mimetype = parse_accept_header(request.headers['Accept']).best
    else :
        print "No accept header, using 'text/html'"
        mimetype = 'text/html'
    
    if mimetype in ['text/html','application/xhtml_xml','*/*']:
        local_resource_uri = u"{}/{}".format(LOCAL_SERVER_NAME,resource_suffix)
        print local_resource_uri
        results = visit(uri,format='html')["results"]["bindings"]
        local_results = localize_results(results)
        
        return render_template('resource.html', local_resource=local_resource_uri, resource=uri, results=local_results)
    elif mimetype in ['application/json']:
        response = make_response(visit(uri,format='jsonld'),200)
        response.headers['Content-Type'] = 'application/json'
        return response
    elif mimetype in ['application/rdf+xml','application/xml']:
        response = make_response(visit(uri,format='rdfxml'),200)
        response.headers['Content-Type'] = 'application/rdf+xml'
        return response
    elif mimetype in ['application/x-turtle']:
        response = make_response(visit(uri,format='turtle'),200)
        response.headers['Content-Type'] = 'application/x-turtle'
        return response

@app.route('/<path:resource_suffix>')
def redirect(resource_suffix):
    
    if resource_suffix.startswith('doc/'):
        print "DOC Retrieved resource_suffix " + resource_suffix
        return document(resource_suffix[4:])
    else :
        print "ID Retrieved resource_suffix " + resource_suffix
        if resource_suffix.startswith('http'):
            abort(500)
        
        resource_suffix = u"doc/{}".format(resource_suffix)
        
        redirect_url = url_for('redirect',resource_suffix=resource_suffix,_external=True)
    
        response = make_response('Moved permanently',303)
        response.headers['Location'] = redirect_url
        response.headers['Accept'] = request.headers['Accept']
    
        return response

    
@app.route('/')
def index():
    redirect_url = url_for('redirect',resource_suffix=START_LOCAL_NAME,_external=True,_scheme="http")
    print "ROOT Redirecting to "+redirect_url
    
    response = make_response('Moved permanently',303)
    response.headers['Location'] = redirect_url
    response.headers['Accept'] = request.headers['Accept']
    
    return response
    

    
    
