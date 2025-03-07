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
Workflow definition for the ORM Profiler.

- How to specify the source
- How to specify the entities to run
- How to define metrics & tests
"""
import traceback
from copy import deepcopy
from typing import Iterable, List, Optional

import click
from pydantic import ValidationError

from metadata.config.common import WorkflowExecutionError
from metadata.config.workflow import get_sink
from metadata.generated.schema.entity.data.database import Database
from metadata.generated.schema.entity.data.table import (
    ColumnProfilerConfig,
    Table,
    TableProfile,
)
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import (
    OpenMetadataConnection,
)
from metadata.generated.schema.entity.services.databaseService import DatabaseService
from metadata.generated.schema.entity.services.serviceType import ServiceType
from metadata.generated.schema.metadataIngestion.databaseServiceProfilerPipeline import (
    DatabaseServiceProfilerPipeline,
)
from metadata.generated.schema.metadataIngestion.workflow import (
    OpenMetadataWorkflowConfig,
)
from metadata.ingestion.api.parser import parse_workflow_config_gracefully
from metadata.ingestion.api.processor import ProcessorStatus
from metadata.ingestion.api.sink import Sink
from metadata.ingestion.ometa.ometa_api import OpenMetadata
from metadata.ingestion.source.database.common_db_source import SQLSourceStatus
from metadata.orm_profiler.api.models import ProfilerProcessorConfig
from metadata.orm_profiler.interfaces.sqa_profiler_interface import SQAProfilerInterface
from metadata.orm_profiler.metrics.registry import Metrics
from metadata.orm_profiler.profiler.core import Profiler
from metadata.orm_profiler.profiler.default import DefaultProfiler, get_default_metrics
from metadata.orm_profiler.validations.models import TableConfig, TablePartitionConfig
from metadata.utils import fqn
from metadata.utils.class_helper import (
    get_service_class_from_service_type,
    get_service_type_from_source_type,
)
from metadata.utils.filters import filter_by_database, filter_by_schema, filter_by_table
from metadata.utils.logger import profiler_logger

logger = profiler_logger()


class ProfilerWorkflow:
    """
    Configure and run the ORM profiler
    """

    config: OpenMetadataWorkflowConfig
    sink: Sink
    metadata: OpenMetadata

    def __init__(self, config: OpenMetadataWorkflowConfig):
        self.config = config
        self.metadata_config: OpenMetadataConnection = (
            self.config.workflowConfig.openMetadataServerConfig
        )
        self.profiler_config = ProfilerProcessorConfig.parse_obj(
            self.config.processor.dict().get("config")
        )

        self.metadata = OpenMetadata(self.metadata_config)

        self._retrieve_service_connection_if_needed()

        # Init and type the source config
        self.source_config: DatabaseServiceProfilerPipeline = (
            self.config.source.sourceConfig.config
        )
        self.source_status = SQLSourceStatus()
        self.status = ProcessorStatus()

        if self.config.sink:
            self.sink = get_sink(
                sink_type=self.config.sink.type,
                sink_config=self.config.sink,
                metadata_config=self.metadata_config,
                _from="orm_profiler",
            )

        if not self._validate_service_name():
            raise ValueError(
                f"Service name `{self.config.source.serviceName}` does not exist. "
                "Make sure you have run the ingestion for the service specified in the profiler workflow. "
                "If so, make sure the profiler service name matches the service name specified during ingestion."
            )

    @classmethod
    def create(cls, config_dict: dict) -> "ProfilerWorkflow":
        """
        Parse a JSON (dict) and create the workflow
        """
        try:
            config = parse_workflow_config_gracefully(config_dict)
            return cls(config)
        except ValidationError as err:
            logger.error("Error trying to parse the Profiler Workflow configuration")
            raise err

    def get_config_for_entity(self, entity: Table) -> Optional[TableConfig]:
        """Get config for a specific entity

        Args:
            entity: table entity
        """

        if not self.profiler_config.tableConfig:
            return None
        return next(
            (
                table_config
                for table_config in self.profiler_config.tableConfig
                if table_config.fullyQualifiedName.__root__
                == entity.fullyQualifiedName.__root__
            ),
            None,
        )

    def get_include_columns(self, entity) -> Optional[List[ColumnProfilerConfig]]:
        """get included columns"""
        entity_config: TableConfig = self.get_config_for_entity(entity)
        if entity_config and entity_config.columnConfig:
            return entity_config.columnConfig.includeColumns

        if entity.tableProfilerConfig:
            return entity.tableProfilerConfig.includeColumns

        return None

    def get_exclude_columns(self, entity) -> Optional[List[str]]:
        """get included columns"""
        entity_config: TableConfig = self.get_config_for_entity(entity)
        if entity_config and entity_config.columnConfig:
            return entity_config.columnConfig.excludeColumns

        if entity.tableProfilerConfig:
            return entity.tableProfilerConfig.excludeColumns

        return None

    def get_profile_sample(self, entity: Table) -> Optional[float]:
        """Get profile sample

        Args:
            entity: table entity
        """
        entity_config: TableConfig = self.get_config_for_entity(entity)
        if entity_config:
            return entity_config.profileSample

        if entity.tableProfilerConfig:
            return entity.tableProfilerConfig.profileSample

        if self.source_config.profileSample:
            return self.source_config.profileSample

        return None

    def get_profile_query(self, entity: Table) -> Optional[float]:
        """Get profile sample

        Args:
            entity: table entity
        """
        entity_config: TableConfig = self.get_config_for_entity(entity)
        if entity_config:
            return entity_config.profileQuery

        if entity.tableProfilerConfig:
            return entity.tableProfilerConfig.profileQuery

        return None

    def get_partition_details(self, entity: Table) -> Optional[TablePartitionConfig]:
        """Get partition details

        Args:
            entity: table entity
        """
        entity_config: TableConfig = self.get_config_for_entity(entity)
        if entity_config:
            return entity_config.partitionConfig

        return None

    def create_profiler_interface(self, service_connection_config, table_entity: Table):
        """Creates a profiler interface object"""
        return SQAProfilerInterface(
            service_connection_config,
            metadata_config=self.metadata_config,
            thread_count=self.source_config.threadCount,
            table_entity=table_entity,
            profile_sample=self.get_profile_sample(table_entity)
            if not self.get_profile_query(table_entity)
            else None,
            profile_query=self.get_profile_query(table_entity)
            if not self.get_profile_sample(table_entity)
            else None,
            partition_config=self.get_partition_details(table_entity)
            if not self.get_profile_query(table_entity)
            else None,
        )

    def create_profiler_obj(
        self, table_entity: Table, profiler_interface: SQAProfilerInterface
    ):
        """Profile a single entity"""
        if not self.profiler_config.profiler:
            self.profiler_obj = DefaultProfiler(
                profiler_interface=profiler_interface,
                include_columns=self.get_include_columns(table_entity),
                exclude_columns=self.get_exclude_columns(table_entity),
            )
        else:
            metrics = (
                [Metrics.get(name) for name in self.profiler_config.profiler.metrics]
                if self.profiler_config.profiler.metrics
                else get_default_metrics(profiler_interface.table)
            )

            self.profiler_obj = Profiler(
                *metrics,
                profiler_interface=profiler_interface,
                include_columns=self.get_include_columns(table_entity),
                exclude_columns=self.get_exclude_columns(table_entity),
            )

    def filter_databases(self, database: Database) -> Optional[Database]:
        """Returns filtered database entities"""
        if filter_by_database(
            self.source_config.databaseFilterPattern,
            database.name.__root__,
        ):
            self.source_status.filter(
                database.name.__root__, "Database pattern not allowed"
            )
            return None
        else:
            return database

    def filter_entities(self, tables: List[Table]) -> Iterable[Table]:
        """
        From a list of tables, apply the SQLSourceConfig
        filter patterns.

        We will update the status on the SQLSource Status.
        """
        for table in tables:
            try:
                if filter_by_schema(
                    self.source_config.schemaFilterPattern,
                    table.databaseSchema.name,
                ):
                    self.source_status.filter(
                        table.databaseSchema.fullyQualifiedName,
                        "Schema pattern not allowed",
                    )
                    continue
                if filter_by_table(
                    self.source_config.tableFilterPattern,
                    table.name.__root__,
                ):
                    self.source_status.filter(
                        table.fullyQualifiedName.__root__, "Table pattern not allowed"
                    )
                    continue

                self.source_status.scanned(table.fullyQualifiedName.__root__)
                yield table
            except Exception as err:  # pylint: disable=broad-except
                self.source_status.filter(table.fullyQualifiedName.__root__, f"{err}")
                logger.error(err)
                logger.debug(traceback.format_exc())

    def get_database_entities(self):
        """List all databases in service"""

        return [
            self.filter_databases(database)
            for database in self.metadata.list_all_entities(
                entity=Database,
                params={"service": self.config.source.serviceName},
            )
            if self.filter_databases(database)
        ]

    def get_table_entities(self, database):
        """
        List and filter OpenMetadata tables based on the
        source configuration.

        The listing will be based on the entities from the
        informed service name in the source configuration.

        Note that users can specify `table_filter_pattern` to
        either be `includes` or `excludes`. This means
        that we will either what is specified in `includes`
        or we will use everything but the tables excluded.

        Same with `schema_filter_pattern`.
        """
        all_tables = self.metadata.list_all_entities(
            entity=Table,
            fields=[
                "tableProfilerConfig",
                "tests",
            ],
            params={
                "service": self.config.source.serviceName,
                "database": fqn.build(
                    self.metadata,
                    entity_type=Database,
                    service_name=self.config.source.serviceName,
                    database_name=database.name.__root__,
                ),
            },
        )

        yield from self.filter_entities(all_tables)

    def copy_service_config(self, database) -> None:
        copy_service_connection_config = deepcopy(
            self.config.source.serviceConnection.__root__.config
        )
        if hasattr(
            self.config.source.serviceConnection.__root__.config,
            "supportsDatabase",
        ):
            if hasattr(
                self.config.source.serviceConnection.__root__.config, "database"
            ):
                copy_service_connection_config.database = database.name.__root__
            if hasattr(self.config.source.serviceConnection.__root__.config, "catalog"):
                copy_service_connection_config.catalog = database.name.__root__

        return copy_service_connection_config

    def execute(self):
        """
        Run the profiling and tests
        """

        databases = self.get_database_entities()

        if not databases:
            raise ValueError(
                "databaseFilterPattern returned 0 result. At least 1 database must be returned by the filter pattern."
                f"\n\t- includes: {self.source_config.databaseFilterPattern.includes}\n\t- excludes: {self.source_config.databaseFilterPattern.excludes}"
            )

        for database in databases:
            copied_service_config = self.copy_service_config(database)
            try:
                for entity in self.get_table_entities(database=database):
                    try:
                        profiler_interface = self.create_profiler_interface(
                            copied_service_config, entity
                        )
                        self.create_profiler_obj(entity, profiler_interface)
                        profile: TableProfile = self.profiler_obj.process(
                            self.source_config.generateSampleData
                        )
                        profiler_interface.close()
                        if hasattr(self, "sink"):
                            self.sink.write_record(profile)
                        self.status.processed(entity.fullyQualifiedName.__root__)
                    except Exception as err:  # pylint: disable=broad-except
                        logger.error(err)
                        logger.error(traceback.format_exc())
            except Exception as err:  # pylint: disable=broad-except
                logger.error(err)
                logger.debug(traceback.format_exc())

    def print_status(self) -> int:
        """
        Runs click echo to print the
        workflow results
        """
        click.echo()
        click.secho("Source Status:", bold=True)
        click.echo(self.source_status.as_string())
        click.secho("Processor Status:", bold=True)
        click.echo(self.status.as_string())
        if hasattr(self, "sink"):
            click.secho("Sink Status:", bold=True)
            click.echo(self.sink.get_status().as_string())
            click.echo()

        if (
            self.source_status.failures
            or self.status.failures
            or (hasattr(self, "sink") and self.sink.get_status().failures)
        ):
            click.secho("Workflow finished with failures", fg="bright_red", bold=True)
            return 1
        if (
            self.source_status.warnings
            or self.status.failures
            or (hasattr(self, "sink") and self.sink.get_status().warnings)
        ):
            click.secho("Workflow finished with warnings", fg="yellow", bold=True)
            return 0

        click.secho("Workflow finished successfully", fg="green", bold=True)
        return 0

    def raise_from_status(self, raise_warnings=False):
        """
        Check source, processor and sink status and raise if needed

        Our profiler source will never log any failure, only filters,
        as we are just picking up data from OM.
        """

        if self.status.failures:
            raise WorkflowExecutionError("Processor reported errors", self.status)
        if hasattr(self, "sink") and self.sink.get_status().failures:
            raise WorkflowExecutionError("Sink reported errors", self.sink.get_status())

        if raise_warnings:
            if self.source_status.warnings:
                raise WorkflowExecutionError(
                    "Source reported warnings", self.source_status
                )
            if self.status.warnings:
                raise WorkflowExecutionError("Processor reported warnings", self.status)
            if hasattr(self, "sink") and self.sink.get_status().warnings:
                raise WorkflowExecutionError(
                    "Sink reported warnings", self.sink.get_status()
                )

    def _validate_service_name(self):
        """Validate service name exists in OpenMetadata"""
        return self.metadata.get_by_name(
            entity=DatabaseService, fqn=self.config.source.serviceName
        )

    def stop(self):
        """
        Close all connections
        """
        self.metadata.close()

    def _retrieve_service_connection_if_needed(self) -> None:
        """
        We override the current `serviceConnection` source config object if source workflow service already exists
        in OM. When it is configured, we retrieve the service connection from the secrets' manager. Otherwise, we get it
        from the service object itself through the default `SecretsManager`.

        :return:
        """
        if not self._is_sample_source(self.config.source.type):
            service_type: ServiceType = get_service_type_from_source_type(
                self.config.source.type
            )
            service = self.metadata.get_by_name(
                get_service_class_from_service_type(service_type),
                self.config.source.serviceName,
            )
            if service:
                self.config.source.serviceConnection = (
                    self.metadata.secrets_manager_client.retrieve_service_connection(
                        service, service_type.name.lower()
                    )
                )

    @staticmethod
    def _is_sample_source(service_type):
        return service_type == "sample-data" or service_type == "sample-usage"
