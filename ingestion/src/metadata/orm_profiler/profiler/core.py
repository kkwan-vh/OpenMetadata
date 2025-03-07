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
Main Profile definition and queries to execute
"""
import warnings
from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Set, Tuple, Type

from pydantic import ValidationError
from sqlalchemy import Column
from sqlalchemy.orm import DeclarativeMeta
from sqlalchemy.orm.session import Session
from typing_extensions import Self

from metadata.generated.schema.api.data.createTableProfile import (
    CreateTableProfileRequest,
)
from metadata.generated.schema.entity.data.table import (
    ColumnProfile,
    ColumnProfilerConfig,
    TableProfile,
)
from metadata.orm_profiler.api.models import ProfilerResponse
from metadata.orm_profiler.interfaces.interface_protocol import InterfaceProtocol
from metadata.orm_profiler.interfaces.sqa_profiler_interface import SQAProfilerInterface
from metadata.orm_profiler.metrics.core import (
    ComposedMetric,
    CustomMetric,
    Metric,
    MetricTypes,
    QueryMetric,
    StaticMetric,
    TMetric,
)
from metadata.orm_profiler.metrics.static.row_count import RowCount
from metadata.orm_profiler.orm.registry import NOT_COMPUTE
from metadata.utils.logger import profiler_logger

logger = profiler_logger()


class MissingMetricException(Exception):
    """
    Raise when building the profiler with Composed Metrics
    and not all the required metrics are present
    """


class Profiler(Generic[TMetric]):
    """
    Core Profiler.

    A profiler is composed of:
    - A profiler_interface, used to run the profiler against a source.
    - An ORM Table. One profiler attacks one table at a time.
    - A tuple of metrics, from which we will construct queries.
    """

    # pylint: disable=too-many-instance-attributes,too-many-public-methods

    def __init__(
        self,
        *metrics: Type[TMetric],
        profiler_interface: InterfaceProtocol,
        profile_date: datetime = datetime.now(tz=timezone.utc).timestamp(),
        include_columns: List[Optional[ColumnProfilerConfig]] = None,
        exclude_columns: List[Optional[str]] = None,
    ):
        """
        :param metrics: Metrics to run. We are receiving the uninitialized classes
        :param profiler_interface: Where to run the queries
        :param table: DeclarativeMeta containing table info
        :param ignore_cols: List of columns to ignore when computing the profile
        :param profile_sample: % of rows to use for sampling column metrics
        """

        self.profiler_interface = profiler_interface
        self.include_columns = include_columns
        self.exclude_columns = exclude_columns
        self._metrics = metrics
        self._profile_date = profile_date

        self.validate_composed_metric()

        # Initialize profiler results
        self._table_results: Dict[str, Any] = {}
        self._column_results: Dict[str, Any] = {}

        # We will get columns from the property
        self._columns: Optional[List[Column]] = None

    @property
    def session(self) -> Session:
        """Kept for backward compatibility"""
        warnings.warn(
            "`<instance>`.session will be retired as platform specific. Instead use"
            "`<instance>.profiler_interface` to see if session is supported by the profiler interface",
            DeprecationWarning,
        )
        if isinstance(self.profiler_interface, SQAProfilerInterface):
            return self.profiler_interface.session

        raise ValueError(
            f"session is not supported for profiler interface {self.profiler_interface.__class__.__name__}"
        )

    @property
    def table(self) -> DeclarativeMeta:
        return self.profiler_interface.table

    @property
    def metrics(self) -> Tuple[Type[TMetric], ...]:
        return self._metrics

    @property
    def ignore_cols(self) -> List[str]:
        return self._get_excluded_columns()

    @property
    def use_cols(self) -> List[Column]:
        """
        Columns to use.

        If it is informed, we'll use them as columns
        instead of picking up all table's columns
        and ignoring the specified ones.
        """
        return self._get_included_columns()

    @property
    def profile_date(self) -> datetime:
        return self._profile_date

    @property
    def columns(self) -> List[Column]:
        """
        Return the list of columns to profile
        by skipping the columns to ignore.
        """

        if self._columns:
            return self._columns

        if self._get_included_columns():
            self._columns = [
                column
                for column in self.profiler_interface.get_columns()
                if column.name in self._get_included_columns()
            ]

        if not self._get_included_columns():
            self._columns = [
                column
                for column in self._columns or self.profiler_interface.get_columns()
                if column.name not in self._get_excluded_columns()
            ]

        return self._columns

    def _get_excluded_columns(self) -> Optional[Set[str]]:
        """Get excluded  columns for table being profiled"""
        if self.exclude_columns:
            return set(self.exclude_columns)
        return {}

    def _get_included_columns(self) -> Optional[Set[str]]:
        """Get include columns for table being profiled"""
        if self.include_columns:
            return {include_col.columnName for include_col in self.include_columns}
        return {}

    def _filter_metrics(self, _type: Type[TMetric]) -> List[Type[TMetric]]:
        """
        Filter metrics by type
        """
        return [metric for metric in self.metrics if issubclass(metric, _type)]

    @property
    def static_metrics(self) -> List[Type[StaticMetric]]:
        return self._filter_metrics(StaticMetric)

    @property
    def composed_metrics(self) -> List[Type[ComposedMetric]]:
        return self._filter_metrics(ComposedMetric)

    @property
    def custom_metrics(self) -> List[Type[CustomMetric]]:
        return self._filter_metrics(CustomMetric)

    @property
    def query_metrics(self) -> List[Type[QueryMetric]]:
        return self._filter_metrics(QueryMetric)

    def get_col_metrics(
        self, metrics: List[Type[TMetric]], column: Optional[Column] = None
    ) -> List[Type[TMetric]]:
        """
        Filter list of metrics for column metrics with allowed types
        """

        if column is None:
            return [metric for metric in metrics if metric.is_col_metric()]

        if (
            self.profiler_interface.table_entity.tableProfilerConfig
            and self.profiler_interface.table_entity.tableProfilerConfig.includeColumns
        ):
            metric_names = (
                metric_array
                for col_name, metric_array in self.profiler_interface.table_entity.tableProfilerConfig.includeColumns
                if col_name == column
            )
            if metric_names:
                metrics = [Metric.get(metric_name) for metric_name in metric_names]

        return [metric for metric in metrics if metric.is_col_metric()]

    @property
    def sample(self):
        """Return the sample used for the profiler"""
        return self.profiler_interface.sample

    def validate_composed_metric(self) -> None:
        """
        Make sure that all composed metrics have
        the necessary ingredients defined in
        `required_metrics` attr
        """
        names = {metric.name() for metric in self.metrics}
        for metric in self.composed_metrics:
            if not set(metric.required_metrics()).issubset(names):
                raise MissingMetricException(
                    f"We need {metric.required_metrics()} for {metric.name}, but only got {names} in the profiler"
                )

    def run_composed_metrics(self, col: Column):
        """
        Run this after the metrics have been computed

        Data should be saved under self.results
        """

        logger.debug("Running post Profiler...")

        current_col_results: Dict[str, Any] = self._column_results.get(col.name)
        if not current_col_results:
            logger.error(
                "We do not have any results to base our Composed Metrics. Stopping!"
            )
            return

        for metric in self.get_col_metrics(self.composed_metrics):
            # Composed metrics require the results as an argument
            logger.debug(f"Running composed metric {metric.name()} for {col.name}")

            self._column_results[col.name][
                metric.name()
            ] = self.profiler_interface.get_composed_metrics(
                col,
                metric,
                current_col_results,
            )

    def _prepare_table_metrics_for_thread_pool(self):
        """prepare table metrics for thread pool"""
        metrics = [
            metric for metric in self.static_metrics if not metric.is_col_metric()
        ]
        if metrics:
            return [
                (
                    metrics,  # metric functions
                    MetricTypes.Table,  # metric type for function mapping
                    None,  # column name
                    self.table,  # table name
                )
            ]
        return []

    def _prepare_column_metrics_for_thread_pool(self):
        """prepare column metrics for thread pool"""
        window_metrics = [
            metric
            for metric in self.get_col_metrics(self.static_metrics)
            if metric.is_window_metric()
        ]
        columns = [
            column
            for column in self.columns
            if column.type.__class__ not in NOT_COMPUTE
        ]

        column_metrics_for_thread_pool = [
            *[
                (
                    self.get_col_metrics(self.static_metrics, column),
                    MetricTypes.Static,
                    column,
                    self.table,
                )
                for column in columns
            ],
            *[
                (
                    metric,
                    MetricTypes.Query,
                    column,
                    self.table,
                )
                for column in self.columns
                for metric in self.get_col_metrics(self.query_metrics, column)
            ],
            *[
                (
                    metric,
                    MetricTypes.Window,
                    column,
                    self.table,
                )
                for column in self.columns
                for metric in [
                    metric
                    for metric in self.get_col_metrics(self.static_metrics, column)
                    if metric.is_window_metric()
                ]
            ],
        ]

        return column_metrics_for_thread_pool

    def profile_entity(self) -> None:
        """Get all the metrics for a given table"""
        table_metrics_for_thread_pool = self._prepare_table_metrics_for_thread_pool()
        column_metrics_for_thread_pool = self._prepare_column_metrics_for_thread_pool()

        all_metrics_for_thread_pool = [
            *table_metrics_for_thread_pool,
            *column_metrics_for_thread_pool,
        ]
        profile_results = self.profiler_interface.get_all_metrics(
            all_metrics_for_thread_pool,
        )

        self._table_results = profile_results["table"]
        self._column_results = profile_results["columns"]

    def compute_metrics(self) -> Self:
        """Run the whole profiling using multithreading"""
        self.profile_entity()
        for column in self.columns:
            self.run_composed_metrics(column)

        return self

    def process(self, generate_sample_data: bool) -> ProfilerResponse:
        """
        Given a table, we will prepare the profiler for
        all its columns and return all the run profilers
        in a Dict in the shape {col_name: Profiler}
        """
        logger.info(
            f"Computing profile metrics for {self.profiler_interface.table_entity.fullyQualifiedName.__root__}..."
        )
        self.compute_metrics()

        if generate_sample_data:
            logger.info(
                f"Fetching sample data for {self.profiler_interface.table_entity.fullyQualifiedName.__root__}..."
            )
            sample_data = self.profiler_interface.fetch_sample_data()
        else:
            sample_data = None

        table_profile = ProfilerResponse(
            table=self.profiler_interface.table_entity,
            profile=self.get_profile(),
            sample_data=sample_data,
        )

        return table_profile

    def get_profile(self) -> CreateTableProfileRequest:
        """
        After executing the profiler, get all results
        and convert them to TableProfile.

        We store the results in the shape:

        _table_results
        {
            "columnCount": ...,
            "rowCount": ...,
        }

        _column_results
        {
            "column_name_A": {
                "metric1": ...,
                "metric2": ...,
            }
        }

        We need to transform it to TableProfile
        """
        try:

            # There are columns that we might have skipped from
            # computing metrics, if the type is not supported.
            # Let's filter those out.
            computed_profiles = [
                ColumnProfile(**self.column_results.get(col.name))
                for col in self.columns
                if self.column_results.get(col.name)
            ]
            table_profile = TableProfile(
                timestamp=self.profile_date,
                columnCount=self._table_results.get("columnCount"),
                rowCount=self._table_results.get(RowCount.name()),
                profileSample=self.profiler_interface.profile_sample,
            )
            return CreateTableProfileRequest(
                tableProfile=table_profile, columnProfile=computed_profiles
            )

        except ValidationError as err:
            logger.error(f"Cannot transform profiler results to TableProfile {err}")
            raise err

    @property
    def column_results(self):
        return self._column_results
