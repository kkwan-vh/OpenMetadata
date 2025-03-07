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
Interfaces with database for all database engine
supporting sqlalchemy abstraction layer
"""

import concurrent.futures
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

from sqlalchemy import Column, inspect
from sqlalchemy.engine.row import Row
from sqlalchemy.orm import DeclarativeMeta, Session

from metadata.generated.schema.entity.data.table import Table, TableProfile
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import (
    OpenMetadataConnection,
)
from metadata.generated.schema.entity.services.databaseService import (
    DatabaseServiceType,
)
from metadata.generated.schema.tests.basic import TestCaseResult
from metadata.generated.schema.tests.testCase import TestCase
from metadata.generated.schema.tests.testDefinition import TestDefinition
from metadata.ingestion.ometa.ometa_api import OpenMetadata
from metadata.orm_profiler.interfaces.interface_protocol import InterfaceProtocol
from metadata.orm_profiler.metrics.registry import Metrics
from metadata.orm_profiler.orm.converter import ometa_to_orm
from metadata.orm_profiler.profiler.handle_partition import (
    get_partition_cols,
    is_partitioned,
)
from metadata.orm_profiler.profiler.runner import QueryRunner
from metadata.orm_profiler.profiler.sampler import Sampler
from metadata.orm_profiler.validations.core import validation_enum_registry
from metadata.orm_profiler.validations.models import TablePartitionConfig
from metadata.utils.connections import (
    create_and_bind_thread_safe_session,
    get_connection,
    test_connection,
)
from metadata.utils.constants import TEN_MIN
from metadata.utils.dispatch import enum_register
from metadata.utils.helpers import get_start_and_end
from metadata.utils.logger import sqa_interface_registry_logger
from metadata.utils.timeout import cls_timeout

logger = sqa_interface_registry_logger()

thread_local = threading.local()


class SQAProfilerInterface(InterfaceProtocol):
    """
    Interface to interact with registry supporting
    sqlalchemy.
    """

    def __init__(
        self,
        service_connection_config,
        metadata_config: Optional[OpenMetadataConnection] = None,
        thread_count: Optional[int] = 5,
        table_entity: Optional[Table] = None,
        table: Optional[DeclarativeMeta] = None,
        profile_sample: Optional[float] = None,
        profile_query: Optional[str] = None,
        partition_config: Optional[TablePartitionConfig] = None,
    ):
        """Instantiate SQA Interface object"""
        self._thread_count = thread_count
        self.table_entity = table_entity
        self._create_ometa_obj(metadata_config)

        # Allows SQA Interface to be used without OM server config
        self.table = table or self._convert_table_to_orm_object()

        self.session_factory = self._session_factory(service_connection_config)
        self.session: Session = self.session_factory()

        self.profile_sample = profile_sample
        self.profile_query = profile_query
        self.partition_details = (
            self._get_partition_details(partition_config)
            if not self.profile_query
            else None
        )

        self._sampler = self.create_sampler()
        self._runner = self.create_runner()

    @property
    def sample(self):
        """Getter method for sample attribute"""
        if not self.sampler:
            raise RuntimeError(
                "You must create a sampler first `<instance>.create_sampler(...)`."
            )

        return self.sampler.random_sample()

    @property
    def runner(self):
        """Getter method for runner attribute"""
        return self._runner

    @property
    def sampler(self):
        """Getter methid for sampler attribute"""
        return self._sampler

    @staticmethod
    def _session_factory(service_connection_config):
        """Create thread safe session that will be automatically
        garbage collected once the application thread ends
        """
        engine = get_connection(service_connection_config)
        return create_and_bind_thread_safe_session(engine)

    def _get_engine(self, service_connection_config):
        """Get engine for database

        Args:
            service_connection_config: connection details for the specific service
        Returns:
            sqlalchemy engine
        """
        engine = get_connection(service_connection_config)
        test_connection(engine)

        return engine

    def _get_partition_details(
        self, partition_config: TablePartitionConfig
    ) -> Optional[Dict]:
        """From partition config, get the partition table for a table entity"""
        if self.table_entity.serviceType == DatabaseServiceType.BigQuery:
            if is_partitioned(self.session, self.table):
                start, end = get_start_and_end(partition_config.partitionQueryDuration)
                partition_details = {
                    "partition_field": partition_config.partitionField
                    or get_partition_cols(self.session, self.table),
                    "partition_start": start,
                    "partition_end": end,
                    "partition_values": partition_config.partitionValues,
                }

                return partition_details

        return None

    def _create_ometa_obj(self, metadata_config):
        try:
            self._metadata = OpenMetadata(metadata_config)
            self._metadata.health_check()
        except Exception:
            logger.warning(
                "No OpenMetadata server configuration found. Running profiler interface without OM server connection"
            )
            self._metadata = None

    def _create_thread_safe_sampler(
        self,
        session,
        table,
    ):
        """Create thread safe runner"""
        if not hasattr(thread_local, "sampler"):
            thread_local.sampler = Sampler(
                session=session,
                table=table,
                profile_sample=self.profile_sample,
                partition_details=self.partition_details,
                profile_sample_query=self.profile_query,
            )
        return thread_local.sampler

    def _create_thread_safe_runner(
        self,
        session,
        table,
        sample,
    ):
        """Create thread safe runner"""
        if not hasattr(thread_local, "runner"):
            thread_local.runner = QueryRunner(
                session=session,
                table=table,
                sample=sample,
                partition_details=self.partition_details,
                profile_sample_query=self.profile_query,
            )
        return thread_local.runner

    def _convert_table_to_orm_object(self) -> DeclarativeMeta:
        """Given a table entity return a SQA ORM object"""
        return ometa_to_orm(self.table_entity, self._metadata)

    def get_columns(self) -> Column:
        """get columns from an orm object"""
        return inspect(self.table).c

    def compute_metrics_in_thread(
        self,
        metric_funcs,
    ):
        """Run metrics in processor worker"""
        (
            metrics,
            metric_type,
            column,
            table,
        ) = metric_funcs
        logger.debug(
            f"Running profiler for {table.__tablename__} on thread {threading.current_thread()}"
        )
        Session = self.session_factory
        session = Session()
        sampler = self._create_thread_safe_sampler(
            session,
            table,
        )
        sample = sampler.random_sample()
        runner = self._create_thread_safe_runner(
            session,
            table,
            sample,
        )

        row = compute_metrics_registry.registry[metric_type.value](
            metrics,
            runner=runner,
            session=session,
            column=column,
            sample=sample,
        )

        try:
            column = column.name
        except Exception as err:
            logger.debug(err)

        return row, column

    def get_all_metrics(
        self,
        metric_funcs: list,
    ):
        """get all profiler metrics"""
        logger.info(f"Computing metrics with {self._thread_count} threads.")
        profile_results = {"table": dict(), "columns": defaultdict(dict)}
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self._thread_count
        ) as executor:
            futures = [
                executor.submit(
                    self.compute_metrics_in_thread,
                    metric_func,
                )
                for metric_func in metric_funcs
            ]

        for future in concurrent.futures.as_completed(futures):
            profile, column = future.result()
            if not isinstance(profile, dict):
                profile = dict()
            if not column:
                profile_results["table"].update(profile)
            else:
                profile_results["columns"][column].update(
                    {
                        "name": column,
                        "timestamp": datetime.now(tz=timezone.utc).timestamp(),
                        **profile,
                    }
                )
        return profile_results

    def fetch_sample_data(self):
        if not self.sampler:
            raise RuntimeError(
                "You must create a sampler first `<instance>.create_sampler(...)`."
            )
        return self.sampler.fetch_sample_data()

    def create_sampler(self) -> Sampler:
        """Create sampler instance"""
        return Sampler(
            session=self.session,
            table=self.table,
            profile_sample=self.profile_sample,
            partition_details=self.partition_details,
            profile_sample_query=self.profile_query,
        )

    def create_runner(self) -> None:
        """Create a QueryRunner Instance"""

        return cls_timeout(TEN_MIN)(
            QueryRunner(
                session=self.session,
                table=self.table(),
                sample=self.sample,
                partition_details=self.partition_details,
                profile_sample_query=self.profile_sample,
            )
        )

    def get_composed_metrics(
        self, column: Column, metric: Metrics, column_results: Dict
    ):
        """Given a list of metrics, compute the given results
        and returns the values

        Args:
            column: the column to compute the metrics against
            metrics: list of metrics to compute
        Returns:
            dictionnary of results
        """
        try:
            return metric(column).fn(column_results)
        except Exception as err:
            logger.error(err)
            self.session.rollback()

    def run_test_case(
        self,
        test_case: TestCase,
        test_definition: TestDefinition,
        table_profile: TableProfile,
        profile_sample: float,
    ) -> Optional[TestCaseResult]:
        """Run table tests where platformsTest=OpenMetadata

        Args:
            table_test_type: test type to be ran
            table_profile: table profile
            table: SQA table,
            profile_sample: sample for the profile
        """

        return validation_enum_registry.registry[test_definition.name.__root__](
            test_case,
            test_definition,
            table_profile=table_profile,
            execution_date=datetime.now(),
            session=self.session,
            table=self.table,
            profile_sample=profile_sample,
        )

    def close(self):
        """close session"""
        self.session.close()


def get_table_metrics(
    metrics: List[Metrics],
    runner: QueryRunner,
    session: Session,
    *args,
    **kwargs,
):
    """Given a list of metrics, compute the given results
    and returns the values

    Args:
        metrics: list of metrics to compute
    Returns:
        dictionnary of results
    """
    try:
        row = runner.select_first_from_table(*[metric().fn() for metric in metrics])

        if row:
            return dict(row)

    except Exception as err:
        logger.error(
            f"Error trying to compute profile for {runner.table.__tablename__} - {err}"
        )
        session.rollback()


def get_static_metrics(
    metrics: List[Metrics],
    runner: QueryRunner,
    session: Session,
    column: Column,
    *args,
    **kwargs,
) -> Dict[str, Union[str, int]]:
    """Given a list of metrics, compute the given results
    and returns the values

    Args:
        column: the column to compute the metrics against
        metrics: list of metrics to compute
    Returns:
        dictionnary of results
    """
    try:
        row = runner.select_first_from_sample(
            *[
                metric(column).fn()
                for metric in metrics
                if not metric.is_window_metric()
            ]
        )
        return dict(row)
    except Exception as err:
        logger.error(
            f"Error trying to compute profile for {runner.table.__tablename__}.{column.name} - {err}"
        )
        session.rollback()


def get_query_metrics(
    metric: Metrics,
    runner: QueryRunner,
    session: Session,
    column: Column,
    sample,
    *args,
    **kwargs,
) -> Optional[Dict[str, Union[str, int]]]:
    """Given a list of metrics, compute the given results
    and returns the values

    Args:
        column: the column to compute the metrics against
        metrics: list of metrics to compute
    Returns:
        dictionnary of results
    """
    try:
        col_metric = metric(column)
        metric_query = col_metric.query(sample=sample, session=session)
        if not metric_query:
            return None
        if col_metric.metric_type == dict:
            results = runner.select_all_from_query(metric_query)
            data = {k: [result[k] for result in results] for k in dict(results[0])}
            return {metric.name(): data}

        else:
            row = runner.select_first_from_query(metric_query)
            return dict(row)
    except Exception as err:
        logger.error(
            f"Error trying to compute profile for {runner.table.__tablename__}.{column.name} - {err}"
        )
        session.rollback()


def get_window_metrics(
    metric: Metrics,
    runner: QueryRunner,
    session: Session,
    column: Column,
    *args,
    **kwargs,
) -> Dict[str, Union[str, int]]:
    """Given a list of metrics, compute the given results
    and returns the values

    Args:
        column: the column to compute the metrics against
        metrics: list of metrics to compute
    Returns:
        dictionnary of results
    """
    try:
        row = runner.select_first_from_sample(metric(column).fn())
        if not isinstance(row, Row):
            return {metric.name(): row}
        return dict(row)
    except Exception as err:
        logger.error(
            f"Error trying to compute profile for {runner.table.__tablename__}.{column.name} - {err}"
        )
        session.rollback()


compute_metrics_registry = enum_register()
compute_metrics_registry.add("Static")(get_static_metrics)
compute_metrics_registry.add("Table")(get_table_metrics)
compute_metrics_registry.add("Query")(get_query_metrics)
compute_metrics_registry.add("Window")(get_window_metrics)
