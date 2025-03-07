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
ColumnValuesToBeBetween validation implementation
"""
# pylint: disable=duplicate-code

from datetime import datetime

from metadata.generated.schema.entity.data.table import ColumnProfile
from metadata.generated.schema.tests.basic import TestCaseResult, TestCaseStatus
from metadata.generated.schema.tests.column.columnValueMinToBeBetween import (
    ColumnValueMinToBeBetween,
)
from metadata.utils.logger import profiler_logger

logger = profiler_logger()


def column_value_min_to_be_between(
    test_case: ColumnValueMinToBeBetween,
    col_profile: ColumnProfile,
    execution_date: datetime,
    **__,
) -> TestCaseResult:
    """
    Validate Column Values metric
    :param test_case: ColumnValuesToBeBetween
    :param col_profile: should contain MIN & MAX metrics
    :param execution_date: Datetime when the tests ran
    :return: TestCaseResult with status and results
    """

    if col_profile.min is None:
        msg = (
            "We expect `min` to be informed on the profiler for ColumnValueMinToBeBetween"
            + f" min={col_profile.min}."
        )
        logger.error(msg)
        return TestCaseResult(
            timestamp=execution_date.timestamp(),
            testCaseStatus=TestCaseStatus.Aborted,
            result=msg,
        )

    status = (
        TestCaseStatus.Success
        if test_case.minValueForMinInCol
        <= col_profile.min
        <= test_case.maxValueForMinInCol
        else TestCaseStatus.Failed
    )
    result = (
        f"Found min={col_profile.min} vs."
        + f" the expected min={test_case.minValueForMinInCol}, max={test_case.maxValueForMinInCol}."
    )

    return TestCaseResult(
        timestamp=execution_date.timestamp(), testCaseStatus=status, result=result
    )
