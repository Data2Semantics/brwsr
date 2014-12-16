from urlparse import urljoin

# Set this to the SPARQL endpoint uri of your triplestore
# e.g. "http://dbpedia.org/sparql"
SPARQL_ENDPOINT = "http://your.sparql.endpoint.here/sparql"

# The DEFAULT_BASE is the prefix of the URI's in the triple store that can be browsed by brwsr
# Requests to brwsr only include the local name (i.e. the the part after the third slash '/'), 
# the DEFAULT_BASE is *always* prepended to this local name to make up the URI that's used to 
# query the triple store
# e.g. "http://dbpedia.org/"
DEFAULT_BASE = "http://your.base.uri.here"

# The LOCAL_DOCUMENT_INFIX is the infix used between the DEFAULT_BASE and the local name of the URI 
# to denote the HTML representation of the RDF resource (see the Cool URI's specification)
LOCAL_DOCUMENT_INFIX = 'doc'

# The LOCAL_SERVER_NAME is the address brwsr listens to. It needs to know this to build proper
# requests when you click a URI in the brwsr page of a resource.
# e.g. "http://localhost:5000" if running flask.
LOCAL_SERVER_NAME = "http://your.server.name.here"

# The START_LOCAL_NAME is the local name of the first URI shown in brwsr if no URI is specified
# e.g. "resource/Amsterdam" when using the DBPedia settings
START_LOCAL_NAME = "some/local/name"

# The START_URI is simply the combination of the DEFAULT_BASE and the START_LOCAL_NAME
# (i.e. there is no need to change this, usually)
# e.g. this will become "http://dbpedia.org/resource/Amsterdam"
START_URI = urljoin(DEFAULT_BASE,START_LOCAL_NAME)