brwsr
=====

**Lightweight Linked Data Browser**

#### Features
* Browse all resources starting with a designated URI prefix in a SPARQL endpoint
* Implements content negotiation to serve representations of these resources both as HTML, and as RDF/XML, Turtle and JSON-LD
* HTML page asynchronously calls <http://preflabel.org> service to retrieve preferred labels for all resources.

In short, it is a very lightweight Python-based alternative to Pubby (with a slightly more attractive interface design)

#### To install:
* Setup a virtualenv and activate it
* run `pip install -r requirements.txt`

#### To use:
* Rename `config-template.py` to `config.py`
* Make the appropriate settings in the file (documentation is inline)
* Start it with `python run.py` if you're playing around, otherwise
* Adjust the `gunicorn_config.py` for your system, and start brwsr with `gunicorn -c gunicorn_config.py app:app` to run in daemon mode on port 5000 (behind e.g. an Apache or Nginx proxy)


#### Example Nginx configuration for use with Gunicorn:

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

1. Set the `BEHIND_PROXY` parameter in your `config.py` to `True`
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
This work was funded by the Dutch national programme COMMIT/
