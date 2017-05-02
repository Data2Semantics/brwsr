brwsr
=====

**Lightweight Linked Data Browser**

### Features
* Browse all resources starting with a designated URI prefix in a SPARQL endpoint
* Implements content negotiation to serve representations of these resources both as HTML, and as RDF/XML, Turtle and JSON-LD
* HTML page asynchronously calls <http://preflabel.org> service to retrieve preferred labels for all resources.

In short, it is a very lightweight Python-based alternative to Pubby (with a slightly more attractive interface design)



### Docker-based

#### Prerequisites
* Make sure you have [Docker](https://www.docker.com) and [docker-compose](https://docs.docker.com/compose/install/) installed for your platform

#### Using
* To use the base setup, copy this docker-compose file to a directory: <https://raw.githubusercontent.com/Data2Semantics/brwsr/master/docker-compose.yml>.
* Run `docker-compose up`.
* This will run brwsr at <http://localhost:5000> with the DBPedia SPARQL endpoint.
* To modify the configuration, change the environment variables in the `docker-compose.yml` file.
* For configuration parameters, see below.

### As a Flask application

#### Installation
* Open up a terminal
* In a directory of your choice, run `git clone https://github.com/Data2Semantics/brwsr.git`
* (optional: setup a virtualenv and activate it)
* run `pip install -r requirements.txt`
* Rename `config-template.py` to `config.py`
* Make the appropriate settings in the file (see below)

#### Using

* Start it with `python run.py` if you're playing around, otherwise
* Adjust the `gunicorn_config.py` for your system, and start brwsr with `gunicorn -c gunicorn_config.py app:app` to run in daemon mode on port 5000 (behind e.g. an Apache or Nginx proxy)


### Configuration Parameters


| Parameter | Allowed Values | Default | Description | `docker-compose.yml` or `config.py` |
| :--------- | :-------------- | :------- | :----------- | :----------------------- |
| `LOCAL_STORE` | `True`, `False` | `False` | Set `LOCAL_STORE` to `True` if you want brwsr to just load a (smallish) RDF file into server memory rather than operate on an external SPARQL store | both |
| `LOCAL_FILE` | File path | `None` | Set `LOCAL_FILE` to the relative or absolute path of the file you want brwsr to load when `LOCAL_STORE` is True. The brwsr application will just use RDFLib to guess the file format based on the extension. You can use UNIX file masks such as * and ? to load multiple files. When using Docker, make sure the files are on a filesystem that is accessible to Docker | both |
| `SPARQL_ENDPOINT` | URL | `http://your.sparql.endpoint.here/sparql` | Set this to the SPARQL endpoint uri of your triplestore e.g. `http://dbpedia.org/sparql` | both |
| `SPARQL_ENDPOINT_MAPPING` | Dictionary | `None` | If brwsr is backed by multiple separate triple stores, use `SPARQL_ENDPOINT_MAPPING` to make sure that each URI for which the `LOCAL_NAME` (i.e. the URI with the `DEFAULT_BASE` removed, if present) starts with a key of the `SPARQL_ENDPOINT_MAPPING` dictionary, the proper SPARQL endpoint is used.  You can also use Python-style regular expressions in the prefix description (the keys of this dictionary)  Note that brwsr will allways *also* query the default `SPARQL_ENDPOINT` (see example in `config-template.py`). | only `config.py` |
| `DEFAULT_BASE` | URI | `http://your.base.uri.here` | The DEFAULT_BASE is the prefix of the URI's in the triple store that can be browsed by brwsr. Requests to brwsr only include the local name (i.e. the the part after the third slash '/'), the `DEFAULT_BASE` is *always* prepended to this local name to make up the URI that's used to query the triple store: e.g. `http://dbpedia.org` (without the last slash!)| both |
| `LOCAL_DOCUMENT_INFIX` | String | `doc` | The `LOCAL_DOCUMENT_INFIX` is the infix used between the `DEFAULT_BASE` and the local name of the URI to denote the HTML representation of the RDF resource (see the Cool URI's specification) | both |
| `LOCAL_SERVER_NAME` | URI | `http://your.server.name.here` | The LOCAL_SERVER_NAME is the address brwsr listens to. It needs to know this to build proper requests when you click a URI in the brwsr page of a resource: e.g. "http://localhost:5000" if running Flask. | both |
| `BEHIND_PROXY` | `True`, `False` | `False` | By default brwsr assumes it is running at the root of the server. If you want to run brwsr under a directory (e.g. http://example.com/brwsr rather than http://example.com), you need to do this via a reverse proxy, and tell brwsr about it (set `BEHIND_PROXY` to True, and configure the proxy, see below) | both |
| `START_LOCAL_NAME` | String | `some/local/name` | The START_LOCAL_NAME is the local name of the first URI shown in brwsr if no URI is specified, e.g. "`resource/Amsterdam`" when using the DBPedia settings | both |
| `START_URI` | URI | `DEFAULT_BASE + "/" + START_LOCAL_NAME` | The `START_URI` is the URI that is shown when browsing to the `SERVER_NAME` URL. It is simply the combination of the `DEFAULT_BASE` and the `START_LOCAL_NAME` (i.e. there is no need to change this, usually) e.g. this will become "`http://dbpedia.org/resource/Amsterdam`" | both |
| `QUERY_RESULTS_LIMIT` | Integer | `5000` |  Set query results limit because otherwise your browser might crash. | both |
| `BROWSE_EXTERNAL_URIS` | `True`, `False` | `True` | Browse URIs that do not match the `DEFAULT_BASE`. This allows for browsing resources from different namespaces within the same endpoint store. | both |
|  `DEREFERENCE_EXTERNAL_URIS` | `True`, `False` | `False` | Dereference external URIs (i.e. retrieve RDF served at that location, and display the resource). This may be slow, depending on the responsiveness of the server at hand. Also, the resulting RDF is stored locally (in memory) which means that this is a potential memory hog for servers that are visited frequently. | both |
| `PORT` | Integer | `5000` | The port via which to run brwsr | both (but needs care when using Docker) |
| `DEBUG` | `True`, `False` | `False` | Switch on debug logging | both |
| `SPARQL_METHOD` | `GET`, `POST` | `GET` | Set the HTTP method to use for communicating with SPARQL endpoint. | both
| `CUSTOM_PARAMETERS` | Dictionary | `{'reasoning': True}` | Set any custom parameters to be sent to the SPARQL endpoint, e.g. `CUSTOM_PARAMETERS = {'reasoning': 'true'}` for Stardog | only `config.py` |



#### Example Nginx Reverse Proxy configuration for use with Gunicorn:

```
server {
    listen 80;
    server_name your.server.name.here;
    access_log /var/log/nginx/brwsr_access.log;
    error_log /var/log/nginx/brswr_error.log;


    location /socket.io {
        proxy_pass http://127.0.0.1:5000/socket.io;
        proxy_redirect off;
        proxy_buffering off;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }

    location / {
        add_header Access-Control-Allow-Origin *;

        proxy_pass http://127.0.0.1:5000;
        proxy_redirect off;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}

```

#### Running `brwsr` at a relative location other than '/'
If for some reason you want or need to run brwsr at a relative path other than '/', you should do two things:

1. Set the `BEHIND_PROXY` parameter in your `config.py` or `docker-compose.yaml` to `True`
2. Setup a Nginx proxy along the lines of the below example (adapted from <http://flask.pocoo.org/snippets/35/>):

```
location /myprefix {
  proxy_pass http://localhost:5000;
  proxy_set_header Host $host;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Scheme $scheme;
  proxy_set_header X-Script-Name /myprefix;
}
```

Where `myprefix` should be set to the location you want to be running brwsr under

The `proxy_pass` setting should point to the address and port you are running brwsr at (default is localhost port 5000).


### Acknowledgements
This work was funded by the Dutch national programme COMMIT/ and the NWO-funded CLARIAH project.
