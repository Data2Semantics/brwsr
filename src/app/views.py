from flask import render_template, g, request, jsonify, make_response, redirect, url_for, abort
import logging
from client import visit
from app import app

log = app.logger
log.setLevel(logging.DEBUG)


DEFAULT_BASE = "http://dbpedia.org/resource/"
START_LOCAL_NAME = "Amsterdam"
START_URI = DEFAULT_BASE + START_LOCAL_NAME

@app.route('/id/<resource_suffix>')
def redirect(resource_suffix):
    print "ID Retrieved resource_suffix " + resource_suffix
    if resource_suffix.startswith('http'):
        abort(500)
    redirect_url = url_for('document',resource_suffix=resource_suffix,_external=True)
    
    print "ID Redirecting to "+redirect_url
    return redirect(redirect_url)
    

@app.route('/doc/<resource_suffix>')
def document(resource_suffix):
    if resource_suffix :
        uri = u"{}/{}".format(DEFAULT_BASE,resource_suffix)
    else :
        uri = START_URI
        
    return render_template('resource.html', resource=uri, results=visit(uri))
    

    
@app.route('/')
def index():
    redirect_url = url_for('document',resource_suffix=START_LOCAL_NAME,_external=True)
    print "ROOT Redirecting to "+redirect_url
    return redirect(redirect_url)