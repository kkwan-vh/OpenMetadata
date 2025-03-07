---
title: Run Redshift Connector using the CLI
slug: /openmetadata/connectors/database/redshift/cli
---

<ConnectorIntro connector="Redshift" goal="CLI" hasUsage="true" hasProfiler="true" hasDBT="true" />

<Requirements />

<PythonMod connector="Redshift" module="redshift" />

If you want to run the Usage Connector, you'll also need to install:

```bash
pip3 install "openmetadata-ingestion[redshift-usage]"
```

<MetadataIngestionServiceDev service="database" connector="Redshift" goal="CLI"/>

<h4>Source Configuration - Service Connection</h4>

- **username**: Specify the User to connect to Snoflake. It should have enough privileges to read all the metadata.
- **password**: Password to connect to Redshift.
- **database**: The database of the data source is an optional parameter, if you would like to restrict the metadata reading to a single database. If left blank, OpenMetadata ingestion attempts to scan all the databases.
- **Connection Options (Optional)**: Enter the details for any additional connection options that can be sent to Redshift during the connection. These details must be added as Key-Value pairs.
- **Connection Arguments (Optional)**: Enter the details for any additional connection arguments such as security or protocol configs that can be sent to Redshift during the connection. These details must be added as Key-Value pairs.
    - In case you are using Single-Sign-On (SSO) for authentication, add the `authenticator` details in the Connection Arguments as a Key-Value pair as follows: `"authenticator" : "sso_login_url"`
    - In case you authenticate with SSO using an external browser popup, then add the `authenticator` details in the Connection Arguments as a Key-Value pair as follows: `"authenticator" : "externalbrowser"`

<MetadataIngestionConfig service="database" connector="Redshift" goal="CLI" hasUsage="true" hasProfiler="true" hasDBT="true"/>
