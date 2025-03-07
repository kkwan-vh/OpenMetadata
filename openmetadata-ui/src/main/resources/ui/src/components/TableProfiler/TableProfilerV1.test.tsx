/*
 *  Copyright 2022 Collate
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *  http://www.apache.org/licenses/LICENSE-2.0
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

// Library imports
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from '@testing-library/react';
import React from 'react';
import { MOCK_TABLE } from '../../mocks/TableData.mock';
import { getCurrentDatasetTab } from '../../utils/DatasetDetailsUtils';
import { TableProfilerProps } from './TableProfiler.interface';
// internal imports
import TableProfilerV1 from './TableProfilerV1';

// mock library imports
jest.mock('react-router-dom', () => ({
  Link: jest
    .fn()
    .mockImplementation(({ children }) => <a href="#">{children}</a>),
}));
jest.mock('antd', () => ({
  Button: jest
    .fn()
    .mockImplementation(({ children, ...props }) => (
      <button {...props}>{children}</button>
    )),

  Col: jest
    .fn()
    .mockImplementation(({ children, ...props }) => (
      <div {...props}>{children}</div>
    )),
  Row: jest
    .fn()
    .mockImplementation(({ children, ...props }) => (
      <div {...props}>{children}</div>
    )),
}));

// mock internel imports
jest.mock('./Component/ProfilerSettingsModal', () => {
  return jest.fn().mockImplementation(() => {
    return <div>ProfilerSettingsModal.component</div>;
  });
});
jest.mock('./Component/ColumnProfileTable', () => {
  return jest.fn().mockImplementation(() => {
    return <div>ColumnProfileTable.component</div>;
  });
});
jest.mock('../../utils/DatasetDetailsUtils');
jest.mock('../../utils/CommonUtils', () => ({
  formatNumberWithComma: jest.fn(),
  formTwoDigitNmber: jest.fn(),
}));
const mockGetCurrentDatasetTab = getCurrentDatasetTab as jest.Mock;

const mockProps: TableProfilerProps = {
  table: MOCK_TABLE,
  onAddTestClick: jest.fn(),
};

describe('Test TableProfiler component', () => {
  beforeEach(() => {
    cleanup();
  });

  it('should render without crashing', async () => {
    render(<TableProfilerV1 {...mockProps} />);

    const profileContainer = await screen.findByTestId(
      'table-profiler-container'
    );
    const settingBtn = await screen.findByTestId('profiler-setting-btn');
    const addTableTest = await screen.findByTestId(
      'profiler-add-table-test-btn'
    );

    expect(profileContainer).toBeInTheDocument();
    expect(settingBtn).toBeInTheDocument();
    expect(addTableTest).toBeInTheDocument();
  });

  it('No data placeholder should be visible where there is no profiler', async () => {
    render(
      <TableProfilerV1
        {...mockProps}
        table={{ ...mockProps.table, profile: undefined }}
      />
    );

    const noProfiler = await screen.findByTestId(
      'no-profiler-placeholder-container'
    );

    expect(noProfiler).toBeInTheDocument();
  });

  it('CTA: Add table test should work properly', async () => {
    render(<TableProfilerV1 {...mockProps} />);

    const addTableTest = await screen.findByTestId(
      'profiler-add-table-test-btn'
    );

    expect(addTableTest).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(addTableTest);
    });

    expect(mockProps.onAddTestClick).toHaveBeenCalledTimes(1);
    expect(mockGetCurrentDatasetTab).toHaveBeenCalledTimes(1);
  });

  it('CTA: Setting button should work properly', async () => {
    const setSettingModalVisible = jest.fn();
    const handleClick = jest.spyOn(React, 'useState');
    handleClick.mockImplementation(() => [false, setSettingModalVisible]);
    render(<TableProfilerV1 {...mockProps} />);

    const settingBtn = await screen.findByTestId('profiler-setting-btn');

    expect(settingBtn).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(settingBtn);
    });

    expect(setSettingModalVisible).toHaveBeenCalledTimes(1);
  });
});
