#!/bin/bash

rm -f ${STARDOG_HOME}/*.lock
rm -f ${STARDOG_HOME}/*.log

# copy license from install dir if not already in STARDOG_HOME
if [ ! -f ${STARDOG_HOME}/stardog-license-key.bin ]; then
  cp ${STARDOG_INSTALL_DIR}/stardog-license-key.bin ${STARDOG_HOME}/stardog-license-key.bin
fi

# copy server properties from install dir if not already in STARDOG_HOME
if [ ! -f ${STARDOG_HOME}/stardog.properties ]; then
  cp ${STARDOG_INSTALL_DIR}/stardog.properties ${STARDOG_HOME}/stardog.properties
fi

echo "starting stardog with the following environment:"
echo "STARDOG_START_PARAMS: ${STARDOG_START_PARAMS}"
echo "STARDOG_CREATE_PARAMS: ${STARDOG_CREATE_PARAMS}"
echo "STARDOG_DB_NAME: ${STARDOG_DB_NAME}"

${STARDOG_INSTALL_DIR}/bin/stardog-admin server start ${STARDOG_START_PARAMS}
${STARDOG_INSTALL_DIR}/bin/stardog-admin db create ${STARDOG_CREATE_PARAMS}
${STARDOG_INSTALL_DIR}/bin/stardog data add ${STARDOG_DB_NAME} /var/data/*.nq
${STARDOG_INSTALL_DIR}/bin/stardog data add ${STARDOG_DB_NAME} /var/data/*.ttl
${STARDOG_INSTALL_DIR}/bin/stardog data add ${STARDOG_DB_NAME} /var/data/*.rdf
${STARDOG_INSTALL_DIR}/bin/stardog data add ${STARDOG_DB_NAME} /var/data/*.trig
${STARDOG_INSTALL_DIR}/bin/stardog data add ${STARDOG_DB_NAME} /var/data/*.nt

${STARDOG_INSTALL_DIR}/bin/stardog-admin server stop
${STARDOG_INSTALL_DIR}/bin/stardog-admin server start --foreground --disable-security ${STARDOG_START_PARAMS}
