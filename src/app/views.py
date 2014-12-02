from flask import render_template, g, request, jsonify, make_response
import logging
from client import visit
from app import app

log = app.logger
log.setLevel(logging.DEBUG)



START_URI = "http://dbpedia.org/resource/Amsterdam"

@app.route('/',methods=['GET'])
def index():
    uri = request.args.get('uri', START_URI)
    return render_template('resource.html', resource=uri, results=visit(uri))