brwsr
=====

Lightweight Linked Data Browser

To install:
* Setup a virtualenv and activate it
* run `pip install -r requirements.txt`

To use:
* Rename `config-template.py` to `config.py`
* Make the appropriate settings in the file (documentation is inline)
* Start it with `python run.py` if you're playing around, otherwise
* Adjust the `gunicorn_config.py` for your system, and start brwsr with `gunicorn -c gunicorn_config.py app:app` to run in daemon mode on port 5400 (behind e.g. an Apache or Nginx proxy)