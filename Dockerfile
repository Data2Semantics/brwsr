FROM python:2.7.13-wheezy

MAINTAINER laurens.rietveld@vu.nl

ENV BRWSR_APP="/usr/local/brwsr"

COPY ./requirements.txt /requirements.txt
RUN pip install -r requirements.txt

COPY ./src ${BRWSR_APP}
ENV CONFIG_FILE=${BRWSR_APP}/app/config.py
RUN cp ${BRWSR_APP}/app/config-template.py ${CONFIG_FILE}


COPY entrypoint.sh /sbin/entrypoint.sh
RUN chmod 755 /sbin/entrypoint.sh

WORKDIR ${BRWSR_APP}
ENTRYPOINT ["/sbin/entrypoint.sh"]
CMD ["app:start"]
EXPOSE 5000
