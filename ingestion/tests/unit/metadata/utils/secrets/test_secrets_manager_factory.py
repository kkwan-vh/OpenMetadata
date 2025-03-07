#  Copyright 2022 Collate
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
Test Secrets Manager Factory
"""
from unittest import TestCase
from unittest.mock import patch

from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import (
    OpenMetadataConnection,
)
from metadata.generated.schema.entity.services.connections.metadata.secretsManagerProvider import (
    SecretsManagerProvider,
)
from metadata.utils.secrets.secrets_manager_factory import (
    get_secrets_manager,
    get_secrets_manager_from_om_connection,
)
from metadata.utils.singleton import Singleton

from .test_secrets_manager import TestSecretsManager


class TestSecretsManagerFactory(TestCase):
    @classmethod
    def setUp(cls) -> None:
        Singleton.clear_all()

    def test_get_not_implemented_secret_manager(self):
        with self.assertRaises(NotImplementedError) as not_implemented_error:
            om_connection: OpenMetadataConnection = (
                TestSecretsManager.External.build_open_metadata_connection(
                    SecretsManagerProvider.local
                )
            )
            om_connection.secretsManagerProvider = "aws"
            get_secrets_manager_from_om_connection(om_connection)
            self.assertEqual(
                "[any] is not implemented.", not_implemented_error.exception
            )

    def test_get_none_secret_manager(self):
        om_connection: OpenMetadataConnection = (
            TestSecretsManager.External.build_open_metadata_connection(
                SecretsManagerProvider.local
            )
        )
        om_connection.secretsManagerProvider = None
        assert get_secrets_manager_from_om_connection(om_connection) is not None
        assert (
            get_secrets_manager(
                om_connection.secretsManagerProvider, om_connection.clusterName
            )
            is not None
        )

    @patch("metadata.clients.aws_client.boto3")
    def test_all_providers_has_implementation(self, mocked_boto3):
        mocked_boto3.client.return_value = {}
        secret_manager_providers = [
            secret_manager_provider
            for secret_manager_provider in SecretsManagerProvider
        ]
        for secret_manager_provider in secret_manager_providers:
            open_metadata_connection: OpenMetadataConnection = OpenMetadataConnection(
                secretsManagerProvider=secret_manager_provider,
                hostPort="http://localhost:8585",
            )
            assert (
                get_secrets_manager_from_om_connection(open_metadata_connection)
                is not None
            )
            assert (
                get_secrets_manager(
                    open_metadata_connection.secretsManagerProvider,
                    open_metadata_connection.clusterName,
                )
                is not None
            )
