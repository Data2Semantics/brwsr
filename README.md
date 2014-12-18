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
* Adjust the `gunicorn_config.py` for your system, and start brwsr with `gunicorn -c gunicorn_config.py app:app` to run in daemon mode on port 5400 (behind e.g. an Apache or Nginx proxy)


#### Example Nginx configuration for use with Gunicorn:

```
server {
    listen 80;
    server_name your.server.name.here;
    access_log /var/log/nginx/brwsr_access.log;
    error_log /var/log/nginx/brswr_error.log;


    location /socket.io {
        proxy_pass http://127.0.0.1:5400/socket.io;
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

        proxy_pass http://127.0.0.1:5400;
        proxy_redirect off;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}

```
