# brwsr-stardog Docker container

This will allow you to start a docker container where Stardog and brwsr work together (no need for a separate Stardog instance).

How to use this:

* Add the data you want to host to the `data/` folder (this will be a shared volume with the Stardog docker container)
* Download the latest version of stardog and put the zipfile (e.g. `stardog-5.0-beta.zip`) and the `stardog-license-key.bin` in this directory.
* Make necessary changes to the brwsr configuration in `docker-compose.yml`.
  * You are likely to want to change the `DEFAULT_BASE` and `START_LOCAL_NAME` parameters to suit your data.
* Make necessary changes to the `stardog.properties` file to suit your need.
* By default the `start-stardog-service.sh` script creates a `stardog` database and fills it with all data in the `data/` folder.
* Run `docker-compose build` to build the `stardog` and `brwsr` images (if needed)
* Run `docker-compose up` to start

Stardog will be running at <http://localhost:5820> and brwser will be at <http://localhost:5000>.

### Acknowledgements

The stardog Dockerfile and startup scripts were shamelessly copied and adapted from Rene Pietszch <https://github.com/rpietzsch/stardog-docker>.
