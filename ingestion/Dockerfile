FROM python:3.9-slim as base
ENV AIRFLOW_HOME=/airflow
RUN apt-get update && \
    apt-get install -y gcc libsasl2-modules libxml2 libsasl2-dev build-essential libssl-dev libffi-dev librdkafka-dev unixodbc-dev python3.9-dev openjdk-11-jre unixodbc freetds-dev freetds-bin tdsodbc libevent-dev wget openssl --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Manually fix security vulnerability from curl
#  -  https://security.snyk.io/vuln/SNYK-DEBIAN11-CURL-2936229
# Add it back to the usual apt-get install once a fix for Debian is released
RUN wget https://curl.se/download/curl-7.84.0.tar.gz && \
    tar -xvf curl-7.84.0.tar.gz && cd curl-7.84.0 && \
    ./configure --with-openssl && make && make install


FROM base as airflow
ENV AIRFLOW_VERSION=2.3.3
ENV CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-3.9.txt"
# Add docker provider for the DockerOperator
RUN pip install "apache-airflow[docker]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"


FROM airflow as apis
WORKDIR /openmetadata-airflow-apis
COPY openmetadata-airflow-apis /openmetadata-airflow-apis

RUN pip install "."

FROM apis as ingestion
WORKDIR /ingestion
COPY ingestion /ingestion

ARG INGESTION_DEPENDENCY=all
RUN pip install --upgrade ".[${INGESTION_DEPENDENCY}]"

RUN airflow db init
RUN cp -r /ingestion/airflow.cfg /airflow/airflow.cfg
RUN chmod 755 ingestion_dependency.sh
EXPOSE 8080
CMD [ "./ingestion_dependency.sh" ]
