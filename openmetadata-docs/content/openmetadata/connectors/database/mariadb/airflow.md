---
title: Run MariaDB Connector using Airflow SDK
slug: /openmetadata/connectors/database/mariadb/airflow
---

<ConnectorIntro connector="MariaDB" goal="Airflow" hasProfiler="true" hasDBT="true" />

<Requirements />

<PythonMod connector="MariaDB" module="mariadb" />

<MetadataIngestionServiceDev service="database" connector="MariaDB" goal="Airflow"/>

<h4>Source Configuration - Service Connection</h4>

- **username**: Specify the User to connect to MariaDB. It should have enough privileges to read all the metadata.
- **password**: Password to connect to MariaDB.
- **hostPort**: Enter the fully qualified hostname and port number for your MariaDB deployment in the Host and Port field.
- **Connection Options (Optional)**: Enter the details for any additional connection options that can be sent to MariaDB during the connection. These details must be added as Key-Value pairs.
- **Connection Arguments (Optional)**: Enter the details for any additional connection arguments such as security or protocol configs that can be sent to MariaDB during the connection. These details must be added as Key-Value pairs. 
  - In case you are using Single-Sign-On (SSO) for authentication, add the `authenticator` details in the Connection Arguments as a Key-Value pair as follows: `"authenticator" : "sso_login_url"`
  - In case you authenticate with SSO using an external browser popup, then add the `authenticator` details in the Connection Arguments as a Key-Value pair as follows: `"authenticator" : "externalbrowser"`

<MetadataIngestionConfig service="database" connector="MariaDB" goal="Airflow" hasProfiler="true" hasDBT="true"/>
