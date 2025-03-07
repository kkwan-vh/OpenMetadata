#  Copyright 2021 Collate
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""
Credentials helper module
"""
import json
import os
import tempfile
from typing import Dict

from cryptography.hazmat.primitives import serialization

from metadata.generated.schema.security.credentials.gcsCredentials import (
    GCSCredentials,
    GCSCredentialsPath,
    GCSValues,
)
from metadata.utils.logger import utils_logger

logger = utils_logger()

GOOGLE_CREDENTIALS = "GOOGLE_APPLICATION_CREDENTIALS"


class InvalidGcsConfigException(Exception):
    """
    Raised when we have errors trying to set GCS credentials
    """


class InvalidPrivateKeyException(Exception):
    """
    If the key cannot be serialised
    """


def validate_private_key(private_key: str) -> None:
    """
    Make sure that a private key can be properly parsed
    by cryptography backends
    :param private_key: key to validate
    """
    try:
        serialization.load_pem_private_key(private_key.encode(), password=None)
    except ValueError as err:
        raise InvalidPrivateKeyException(f"Cannot serialise key - {err}")


def create_credential_tmp_file(credentials: dict) -> str:
    """
    Given a credentials' dict, store it in a tmp file
    :param credentials: dictionary to store
    :return: path to find the file
    """
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        cred_json = json.dumps(credentials, indent=4, separators=(",", ": "))
        fp.write(cred_json.encode())

        return fp.name


def build_google_credentials_dict(gcs_values: GCSValues) -> Dict[str, str]:
    """
    Given GCSValues, build a dictionary as the JSON file
    downloaded from GCS with the service_account
    :param gcs_values: GCS credentials
    :return: Dictionary with credentials
    """

    private_key_str = gcs_values.privateKey.get_secret_value()
    validate_private_key(private_key_str)

    return {
        "type": gcs_values.type,
        "project_id": gcs_values.projectId,
        "private_key_id": gcs_values.privateKeyId,
        "private_key": private_key_str,
        "client_email": gcs_values.clientEmail,
        "client_id": gcs_values.clientId,
        "auth_uri": str(gcs_values.authUri),
        "token_uri": str(gcs_values.tokenUri),
        "auth_provider_x509_cert_url": str(gcs_values.authProviderX509CertUrl),
        "client_x509_cert_url": str(gcs_values.clientX509CertUrl),
    }


def set_google_credentials(gcs_credentials: GCSCredentials) -> None:
    """
    Set GCS credentials environment variable
    :param gcs_credentials: GCSCredentials
    """
    if os.environ.get(GOOGLE_CREDENTIALS):
        return

    if isinstance(gcs_credentials.gcsConfig, GCSCredentialsPath):
        os.environ[GOOGLE_CREDENTIALS] = str(gcs_credentials.gcsConfig.__root__)
        return

    if gcs_credentials.gcsConfig.projectId is None:
        logger.info(
            "No credentials available, using the current environment permissions authenticated via gcloud SDK."
        )
        return

    if isinstance(gcs_credentials.gcsConfig, GCSValues):
        credentials_dict = build_google_credentials_dict(gcs_credentials.gcsConfig)

        tmp_credentials_file = create_credential_tmp_file(credentials=credentials_dict)
        os.environ[GOOGLE_CREDENTIALS] = tmp_credentials_file
        return

    raise InvalidGcsConfigException(
        f"Error trying to set GCS credentials with {gcs_credentials}."
        " Check https://docs.open-metadata.org/connectors/bigquery"
    )
