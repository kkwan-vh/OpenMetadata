/*
 *  Copyright 2021 Collate
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

import { fireEvent, render, screen } from '@testing-library/react';
import React from 'react';
import EditAnnouncementModal from './EditAnnouncementModal';

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

jest.mock('../../../utils/AnnouncementsUtils', () => ({
  validateMessages: {
    title: '',
  },
}));

jest.mock('../../../utils/EntityUtils', () => ({
  getEntityFeedLink: jest.fn(),
}));

jest.mock('../../../utils/TimeUtils', () => ({
  getUTCDateTime: jest.fn(),
  getLocaleDate: jest.fn(),
}));

jest.mock('../../common/rich-text-editor/RichTextEditor', () => {
  return jest.fn().mockReturnValue(<div>RichTextEditor</div>);
});

const onCancel = jest.fn();
const onConfirm = jest.fn();

const mockProps = {
  open: true,
  announcement: {
    description: '',
    startTime: 1678900280,
    endTime: 1678900780,
  },
  announcementTitle: 'title',
  onCancel,
  onConfirm,
};

describe('Test Edit Announcement modal', () => {
  it('Should render the component', async () => {
    render(<EditAnnouncementModal {...mockProps} />);

    const modal = await screen.findByTestId('edit-announcement');

    const form = await screen.findByTestId('announcement-form');

    expect(modal).toBeInTheDocument();

    expect(form).toBeInTheDocument();
  });

  it('Cancel should work', async () => {
    render(<EditAnnouncementModal {...mockProps} />);

    const cancelButton = await screen.findByText('Cancel');

    fireEvent.click(cancelButton);

    expect(onCancel).toBeCalled();
  });
});
