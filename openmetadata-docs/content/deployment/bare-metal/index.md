---
title: Bare Metal Deployment
slug: /deployment/bare-metal
---

# Deploy on Bare Metal

Requirements This guide assumes you have access to a command-line environment or shell such as bash, zsh, etc. or Linux
or Mac OS X or PowerShell on Microsoft Windows. This guide also assumes that your command-line environment has access to
the tar utility. Please review additional requirements listed in the subsections below.

## Java (version 11.0.0 or greater)

OpenMetadata is built using Java, DropWizard, and Jetty.

Type the following command to verify that you have a supported version of the Java runtime installed.

```commandline
java --version
```

To install Java or upgrade to Java 11 or greater, see the instructions for your operating system at [How do I install
Java?](https://java.com/en/download/help/download_options.html#mac).

## MySQL (version 8.0.0 or greater)

To install MySQL see the instructions for your operating system (OS) at [Installing and Upgrading MySQL](https://dev.mysql.com/doc/mysql-installation-excerpt/8.0/en/installing.html) 
or visit one of the following OS-specific guides.

- [Installing MySQL on Linux](https://dev.mysql.com/doc/mysql-installation-excerpt/8.0/en/linux-installation.html)
- [Installing MySQL on Windows](https://dev.mysql.com/doc/mysql-installation-excerpt/8.0/en/windows-installation.html)
- [Installing MySQL on MacOS](https://dev.mysql.com/doc/mysql-installation-excerpt/8.0/en/macos-installation.html)

<Note>

Make sure to configure required databases and users for OpenMetadata. 

You can refer a sample script [here](https://github.com/open-metadata/OpenMetadata/blob/main/docker/local-metadata/mysql-script.sql).

</Note>


## Elasticsearch (version 7.X)

To install or upgrade Elasticsearch to a supported version please see the instructions for your operating system at 
[Installing ElasticSearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/install-elasticsearch.html).

We do not support ElasticSearch 8.x yet.

Please follow the instructions here to [install ElasticSearch](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/setup.html).

## Airflow (version 2.0.0 or greater) or other workflow schedulers

OpenMetadata performs metadata ingestion using ingestion

connectors designed to run in Airflow or another workflow scheduler. To install Airflow, please see the
[Airflow Installation guide](/deployment/airflow).

# Procedure

## 1. Download the distribution

Visit the [releases page](https://github.com/open-metadata/OpenMetadata/releases) and download the latest binary release.

Release binaries follow the naming convention of `openmetadata-x.y.z.tar.gz`. Where `x`, `y`, and `z` represent the 
major, minor, and patch release numbers.

## 2. Untar the release download

Once the tar file has downloaded, run the following command, updated if necessary for the version of OpenMetadata that you downloaded.

```commandline
tar -zxvf openmetadata-*.tar.gz
```

## 3. Navigate to the directory created

```commandline
cd openmetadata-*
```

Review and update the `openmetadata.yaml` configurations to match your environment. Specifically, consider aspects such
as the connection to the MySQL database or ElasticSearch. You can find more information about these configurations
[here](/deployment/configuration).

## 4. Prepare the OpenMetadata Database and Indexes

The command below will generate all the necessary tables and indexes in ElasticSearch.

<Note>

Note that if there's any data in that database, this command will drop it!

</Note>

```commandline
./bootstrap/bootstrap_storage.sh drop-create-all
```

## 5. Start OpenMetadata

```commandline
./bin/openmetadata.sh start
```

We recommend configuring `serviced` to monitor the OpenMetadata command to restart in case of any failures.

## Run OpenMetadata with a load balancer

You may put one or more OpenMetadata instances behind a load balancer for reverse proxying.
To do this you will need to add one or more entries to the configuration file for your reverse proxy.

### Apache mod_proxy

To use the Apache mod_proxy module as a reverse proxy for load balancing, update the VirtualHost tag in your
Apache config file to resemble the following.

```xml
<VirtualHost *:80>
    <Proxy balancer://mycluster>
        BalancerMember http://127.0.0.1:8585 <!-- First OpenMetadata server -->
        BalancerMember http://127.0.0.2:8686 <!-- Second OpenMetadata server -->
    </Proxy>

    ProxyPreserveHost On

    ProxyPass / balancer://mycluster/
    ProxyPassReverse / balancer://mycluster/
</VirtualHost>
```

### Nginx

To use OpenMetadata behind an Nginx reverse proxy, add an entry resembling the following the http context of your Nginx
configuration file for each OpenMetadata instance.

```commandline
server {
    access_log /var/log/nginx/stage-reverse-access.log;
    error_log /var/log/nginx/stage-reverse-error.log;         
    server_name stage.open-metadata.org;
    location / {
        proxy_pass http://127.0.0.1:8585;
    }
}
```

## Run OpenMetadata with AWS Services

If you are running OpenMetadata in AWS, it is recommended to use [Amazon RDS](https://docs.aws.amazon.com/rds/index.html) and [Amazon OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/?id=docs_gateway).

We support 

- Amazon RDS (MySQL) engine version upto 8.0.29
- Amazon OpenSearch (ElasticSearch) engine version upto 7.1
- Amazon RDS (PostgreSQL) engine version upto 14.2-R1

For Production Systems, we recommend Amazon RDS to be in Multiple Availibility Zones. For Amazon OpenSearch (ElasticSearch) Service, we recommend Multiple Availibility Zones with minimum 3 Master Nodes.

Once you have the RDS and OpenSearch Services Setup, you can update the environment variables below for OpenMetadata bare metal systems to connect with Database and ElasticSearch.

```
# MySQL Environment Variables
DB_DRIVER_CLASS='com.mysql.cj.jdbc.Driver'
DB_SCHEME='mysql'
DB_USE_SSL='true'
MYSQL_USER_PASSWORD='<YOUR_RDS_USER_PASSWORD>'
DB_SCHEME='mysql'
MYSQL_HOST='<YOUR_RDS_HOST_NAME>'
MYSQL_USER='<YOUR_RDS_USER_NAME>'
MYSQL_DATABASE='<YOUR_RDS_DATABASE_NAME>'
MYSQL_PORT='<YOUR_RDS_PORT>'
# ElasticSearch Environment Variables
ELASTICSEARCH_SOCKET_TIMEOUT_SECS='60'
ELASTICSEARCH_USER='<ES_USERNAME>'
ELASTICSEARCH_CONNECTION_TIMEOUT_SECS='5'
ELASTICSEARCH_PORT='443'
ELASTICSEARCH_SCHEME='https'
ELASTICSEARCH_BATCH_SIZE='10'
ELASTICSEARCH_HOST='vpc-<random_characters>.<aws_region>.es.amazonaws.com'
ELASTICSEARCH_PASSWORD='<ES_PASSWORD>'
```


## Enable Security

Please follow our [Enable Security Guide](/deployment/bare-metal/security) to configure security for your OpenMetadata
installation.
