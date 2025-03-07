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
Test ORM Profiler workflow

To run this we need OpenMetadata server up and running.

No sample data is required beforehand
"""
from copy import deepcopy
from unittest import TestCase

import pytest
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base

from metadata.generated.schema.entity.data.table import Table
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import (
    OpenMetadataConnection,
)
from metadata.generated.schema.entity.services.databaseService import DatabaseService
from metadata.ingestion.api.workflow import Workflow
from metadata.ingestion.ometa.ometa_api import OpenMetadata
from metadata.orm_profiler.api.workflow import ProfilerWorkflow
from metadata.utils.connections import create_and_bind_session

sqlite_shared = "file:cachedb?mode=memory&cache=shared&check_same_thread=False"

ingestion_config = {
    "source": {
        "type": "sqlite",
        "serviceName": "test_sqlite",
        "serviceConnection": {
            "config": {
                "type": "SQLite",
                "databaseMode": sqlite_shared,
                "database": "main",
            }
        },
        "sourceConfig": {"config": {"type": "DatabaseMetadata"}},
    },
    "sink": {"type": "metadata-rest", "config": {}},
    "workflowConfig": {
        "openMetadataServerConfig": {
            "hostPort": "http://localhost:8585/api",
        }
    },
}

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(256))
    fullname = Column(String(256))
    nickname = Column(String(256))
    age = Column(Integer)


class NewUser(Base):
    __tablename__ = "new_users"
    id = Column(Integer, primary_key=True)
    name = Column(String(256))
    fullname = Column(String(256))
    nickname = Column(String(256))
    age = Column(Integer)


class ProfilerWorkflowTest(TestCase):
    """
    Run the end to end workflow and validate
    """

    engine = create_engine(
        f"sqlite+pysqlite:///{sqlite_shared}",
    )
    session = create_and_bind_session(engine)

    server_config = OpenMetadataConnection(hostPort="http://localhost:8585/api")
    metadata = OpenMetadata(server_config)

    @classmethod
    def setUpClass(cls) -> None:
        """
        Prepare Ingredients
        """
        User.__table__.create(bind=cls.engine)
        NewUser.__table__.create(bind=cls.engine)

        data = [
            User(name="John", fullname="John Doe", nickname="johnny b goode", age=30),
            User(name="Jane", fullname="Jone Doe", nickname=None, age=31),
        ]
        cls.session.add_all(data)
        cls.session.commit()

        new_user = [
            NewUser(
                name="John", fullname="John Doe", nickname="johnny b goode", age=30
            ),
            NewUser(name="Jane", fullname="Jone Doe", nickname=None, age=31),
        ]
        cls.session.add_all(new_user)
        cls.session.commit()

        ingestion_workflow = Workflow.create(ingestion_config)
        ingestion_workflow.execute()
        ingestion_workflow.raise_from_status()
        ingestion_workflow.print_status()
        ingestion_workflow.stop()

    @classmethod
    def tearDownClass(cls) -> None:
        """
        Clean up
        """

        service_id = str(
            cls.metadata.get_by_name(
                entity=DatabaseService, fqn="test_sqlite"
            ).id.__root__
        )

        cls.metadata.delete(
            entity=DatabaseService,
            entity_id=service_id,
            recursive=True,
            hard_delete=True,
        )

        NewUser.__table__.drop(bind=cls.engine)
        User.__table__.drop(bind=cls.engine)

    def test_ingestion(self):
        """
        Validate that the ingestion ran correctly
        """

        table_entity: Table = self.metadata.get_by_name(
            entity=Table, fqn="test_sqlite.main.main.users"
        )
        assert table_entity.fullyQualifiedName.__root__ == "test_sqlite.main.main.users"

    def test_profiler_workflow(self):
        """
        Prepare and execute the profiler workflow
        on top of the Users table
        """
        workflow_config = deepcopy(ingestion_config)
        workflow_config["source"]["sourceConfig"]["config"].update(
            {
                "type": "Profiler",
                "tableFilterPattern": {"includes": ["users"]},
            }
        )
        workflow_config["processor"] = {
            "type": "orm-profiler",
            "config": {
                "profiler": {
                    "name": "my_profiler",
                    "timeout_seconds": 60,
                    "metrics": ["row_count", "min", "max", "COUNT", "null_count"],
                },
                "tableConfig": [
                    {
                        "fullyQualifiedName": "test_sqlite.main.main.users",
                        "profileSample": 75,
                    }
                ],
            },
        }

        profiler_workflow = ProfilerWorkflow.create(workflow_config)
        profiler_workflow.execute()
        status = profiler_workflow.print_status()
        profiler_workflow.stop()

        assert status == 0

        table = self.metadata.get_by_name(
            entity=Table,
            fqn="test_sqlite.main.main.users",
            fields=["tableProfilerConfig", "profile"],
        )
        assert table.profile.profileSample == 75.0

    def test_worflow_sample_profile(self):
        """Test the worflow sample profile gets propagated down to the table profileSample"""
        workflow_config = deepcopy(ingestion_config)
        workflow_config["source"]["sourceConfig"]["config"].update(
            {
                "type": "Profiler",
                "profileSample": 50,
                "tableFilterPattern": {"includes": ["new_users"]},
            }
        )
        workflow_config["processor"] = {"type": "orm-profiler", "config": {}}

        profiler_workflow = ProfilerWorkflow.create(workflow_config)
        profiler_workflow.execute()
        profiler_workflow.print_status()
        profiler_workflow.stop()

        table = self.metadata.get_by_name(
            entity=Table,
            fqn="test_sqlite.main.main.new_users",
            fields=["tableProfilerConfig"],
        )
        # setting sampleProfile from config has been temporarly removed
        # up until we split tests and profiling
        assert table.tableProfilerConfig is None
