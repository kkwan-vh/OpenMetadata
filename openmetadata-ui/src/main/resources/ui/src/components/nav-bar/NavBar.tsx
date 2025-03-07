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

import { Badge, Dropdown, Input, Space } from 'antd';
import { debounce, toString } from 'lodash';
import React, { useCallback, useEffect, useState } from 'react';
import { Link, NavLink, useHistory } from 'react-router-dom';
import AppState from '../../AppState';
import Logo from '../../assets/svg/logo-monogram.svg';
import {
  NOTIFICATION_READ_TIMER,
  ROUTES,
  SOCKET_EVENTS,
} from '../../constants/constants';
import {
  hasNotificationPermission,
  shouldRequestPermission,
} from '../../utils/BrowserNotificationUtils';
import {
  getEntityFQN,
  getEntityType,
  prepareFeedLink,
} from '../../utils/FeedUtils';
import {
  inPageSearchOptions,
  isInPageSearchAllowed,
} from '../../utils/RouterUtils';
import { activeLink, normalLink } from '../../utils/styleconstant';
import SVGIcons, { Icons } from '../../utils/SvgUtils';
import { getTaskDetailPath } from '../../utils/TasksUtils';
import SearchOptions from '../app-bar/SearchOptions';
import Suggestions from '../app-bar/Suggestions';
import Avatar from '../common/avatar/Avatar';
import CmdKIcon from '../common/CmdKIcon/CmdKIcon.component';
import PopOver from '../common/popover/PopOver';
import DropDown from '../dropdown/DropDown';
import { WhatsNewModal } from '../Modals/WhatsNewModal';
import NotificationBox from '../NotificationBox/NotificationBox.component';
import { useWebSocketConnector } from '../web-scoket/web-scoket.provider';
import { NavBarProps } from './NavBar.interface';

const NavBar = ({
  supportDropdown,
  profileDropdown,
  searchValue,
  isFeatureModalOpen,
  isTourRoute = false,
  pathname,
  username,
  isSearchBoxOpen,
  handleSearchBoxOpen,
  handleFeatureModal,
  handleSearchChange,
  handleKeyDown,
  handleOnClick,
}: NavBarProps) => {
  const history = useHistory();
  const [searchIcon, setSearchIcon] = useState<string>('icon-searchv1');
  const [suggestionSearch, setSuggestionSearch] = useState<string>('');
  const [hasTaskNotification, setHasTaskNotification] =
    useState<boolean>(false);
  const [hasMentionNotification, setHasMentionNotification] =
    useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>('Task');

  const { socket } = useWebSocketConnector();

  const navStyle = (value: boolean) => {
    if (value) return { color: activeLink };

    return { color: normalLink };
  };

  const debouncedOnChange = useCallback(
    (text: string): void => {
      setSuggestionSearch(text);
    },
    [setSuggestionSearch]
  );

  const debounceOnSearch = useCallback(debounce(debouncedOnChange, 400), [
    debouncedOnChange,
  ]);

  const handleTaskNotificationRead = () => {
    setHasTaskNotification(false);
  };

  const handleMentionsNotificationRead = () => {
    setHasMentionNotification(false);
  };

  const handleBellClick = (visible: boolean) => {
    if (visible) {
      switch (activeTab) {
        case 'Task':
          hasTaskNotification &&
            setTimeout(() => {
              handleTaskNotificationRead();
            }, NOTIFICATION_READ_TIMER);

          break;

        case 'Conversation':
          hasMentionNotification &&
            setTimeout(() => {
              handleMentionsNotificationRead();
            }, NOTIFICATION_READ_TIMER);

          break;
      }
    }
  };

  const handleActiveTab = (key: string) => {
    setActiveTab(key);
  };

  const showBrowserNotification = (
    about: string,
    createdBy: string,
    type: string,
    id?: string
  ) => {
    if (!hasNotificationPermission()) {
      return;
    }
    const entityType = getEntityType(about);
    const entityFQN = getEntityFQN(about);
    let body;
    let path: string;
    switch (type) {
      case 'Task':
        body = `${createdBy} assigned you a new task.`;
        path = getTaskDetailPath(toString(id)).pathname;

        break;
      case 'Conversation':
        body = `${createdBy} mentioned you in a comment.`;
        path = prepareFeedLink(entityType as string, entityFQN as string);
    }
    const notification = new Notification('Notification From OpenMetadata', {
      body: body,
      icon: Logo,
    });
    notification.onclick = () => {
      history.push(path);
    };
  };

  useEffect(() => {
    if (shouldRequestPermission()) {
      Notification.requestPermission();
    }
  }, []);

  useEffect(() => {
    if (socket) {
      socket.on(SOCKET_EVENTS.TASK_CHANNEL, (newActivity) => {
        if (newActivity) {
          const activity = JSON.parse(newActivity);
          setHasTaskNotification(true);
          showBrowserNotification(
            activity.about,
            activity.createdBy,
            activity.type,
            activity.task?.id
          );
        }
      });

      socket.on(SOCKET_EVENTS.MENTION_CHANNEL, (newActivity) => {
        if (newActivity) {
          const activity = JSON.parse(newActivity);
          setHasMentionNotification(true);
          showBrowserNotification(
            activity.about,
            activity.createdBy,
            activity.type,
            activity.task?.id
          );
        }
      });
    }

    return () => {
      socket && socket.off(SOCKET_EVENTS.TASK_CHANNEL);
      socket && socket.off(SOCKET_EVENTS.MENTION_CHANNEL);
    };
  }, [socket]);

  return (
    <>
      <div className="tw-h-16 tw-py-3 tw-border-b-2 tw-border-separator">
        <div className="tw-flex tw-items-center tw-flex-row tw-justify-between tw-flex-nowrap tw-px-6 centered-layout">
          <div className="tw-flex tw-items-center tw-flex-row tw-justify-between tw-flex-nowrap">
            <NavLink className="tw-flex-shrink-0" id="openmetadata_logo" to="/">
              <SVGIcons alt="OpenMetadata Logo" icon={Icons.LOGO} width="90" />
            </NavLink>
            <Space className="tw-ml-5" size={16}>
              <NavLink
                className="focus:tw-no-underline"
                data-testid="appbar-item-explore"
                style={navStyle(pathname.startsWith('/explore'))}
                to={{
                  pathname: '/explore/tables',
                }}>
                Explore
              </NavLink>

              <NavLink
                className="focus:tw-no-underline"
                data-testid="appbar-item-glossary"
                style={navStyle(pathname.startsWith('/glossary'))}
                to={{
                  pathname: ROUTES.GLOSSARY,
                }}>
                Glossary
              </NavLink>

              <NavLink
                className="focus:tw-no-underline"
                data-testid="appbar-item-tags"
                style={navStyle(pathname.startsWith('/tags'))}
                to={{
                  pathname: ROUTES.TAGS,
                }}>
                Tags
              </NavLink>

              <NavLink
                className="focus:tw-no-underline"
                data-testid="appbar-item-settings"
                style={navStyle(pathname.startsWith('/settings'))}
                to={{
                  pathname: ROUTES.SETTINGS,
                }}>
                Settings
              </NavLink>
            </Space>
          </div>
          <div
            className="tw-flex-none tw-relative tw-justify-items-center tw-ml-16"
            data-testid="appbar-item">
            <Input
              autoComplete="off"
              className="tw-relative search-grey hover:tw-outline-none focus:tw-outline-none tw-pl-2 tw-pt-2 tw-pb-1.5 tw-ml-4 tw-z-41"
              data-testid="searchBox"
              id="searchBox"
              placeholder="Search for Table, Topics, Dashboards,Pipeline and ML Models"
              style={{
                borderRadius: '0.24rem',
                boxShadow: 'none',
                height: '37px',
              }}
              suffix={
                <span
                  className="tw-flex tw-items-center"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleOnClick();
                  }}>
                  <CmdKIcon />
                  <span className="tw-cursor-pointer tw-mb-2 tw-ml-3 tw-w-4 tw-h-4 tw-text-center">
                    <SVGIcons alt="icon-search" icon={searchIcon} />
                  </span>
                </span>
              }
              type="text"
              value={searchValue}
              onBlur={() => setSearchIcon('icon-searchv1')}
              onChange={(e) => {
                const { value } = e.target;
                debounceOnSearch(value);
                handleSearchChange(value);
              }}
              onFocus={() => setSearchIcon('icon-searchv1color')}
              onKeyDown={handleKeyDown}
            />
            {!isTourRoute &&
              searchValue &&
              (isInPageSearchAllowed(pathname) ? (
                <SearchOptions
                  isOpen={isSearchBoxOpen}
                  options={inPageSearchOptions(pathname)}
                  searchText={searchValue}
                  selectOption={(text) => {
                    AppState.inPageSearchText = text;
                  }}
                  setIsOpen={handleSearchBoxOpen}
                />
              ) : (
                <Suggestions
                  isOpen={isSearchBoxOpen}
                  searchText={suggestionSearch}
                  setIsOpen={handleSearchBoxOpen}
                />
              ))}
          </div>
          <div className="tw-flex tw-ml-auto tw-pl-36">
            <Space size={24}>
              <button className="focus:tw-no-underline hover:tw-underline tw-flex-shrink-0 ">
                <Dropdown
                  destroyPopupOnHide
                  overlay={
                    <NotificationBox
                      hasMentionNotification={hasMentionNotification}
                      hasTaskNotification={hasTaskNotification}
                      onMarkMentionsNotificationRead={
                        handleMentionsNotificationRead
                      }
                      onMarkTaskNotificationRead={handleTaskNotificationRead}
                      onTabChange={handleActiveTab}
                    />
                  }
                  overlayStyle={{
                    zIndex: 9999,
                    width: '425px',
                    minHeight: '375px',
                  }}
                  placement="bottomRight"
                  trigger={['click']}
                  onVisibleChange={handleBellClick}>
                  <Badge dot={hasTaskNotification || hasMentionNotification}>
                    <SVGIcons
                      alt="Alert bell icon"
                      icon={Icons.ALERT_BELL}
                      width="20"
                    />
                  </Badge>
                </Dropdown>
              </button>
              <button
                className="focus:tw-no-underline hover:tw-underline tw-flex-shrink-0"
                data-testid="whatsnew-modal"
                onClick={() => handleFeatureModal(true)}>
                <SVGIcons alt="Doc icon" icon={Icons.WHATS_NEW} width="20" />
              </button>
              <button
                className="focus:tw-no-underline hover:tw-underline tw-flex-shrink-0"
                data-testid="tour">
                <Link to={ROUTES.TOUR}>
                  <SVGIcons alt="tour icon" icon={Icons.TOUR} width="20" />
                </Link>
              </button>
              <div className="tw-flex tw-flex-shrink-0 tw--ml-2 tw-items-center ">
                <DropDown
                  dropDownList={supportDropdown}
                  icon={
                    <SVGIcons
                      alt="Doc icon"
                      className="tw-align-middle tw-mt-0.5 tw-mr-1"
                      icon={Icons.HELP_CIRCLE}
                      width="20"
                    />
                  }
                  isDropDownIconVisible={false}
                  isLableVisible={false}
                  label="Need Help"
                  type="link"
                />
              </div>
            </Space>
            <div data-testid="dropdown-profile">
              <DropDown
                dropDownList={profileDropdown}
                icon={
                  <>
                    <PopOver
                      position="bottom"
                      title="Profile"
                      trigger="mouseenter">
                      {AppState?.userDetails?.profile?.images?.image512 ? (
                        <div className="profile-image square tw--mr-2">
                          <img
                            alt="user"
                            referrerPolicy="no-referrer"
                            src={AppState.userDetails.profile.images.image512}
                          />
                        </div>
                      ) : (
                        <Avatar name={username} width="30" />
                      )}
                    </PopOver>
                  </>
                }
                isDropDownIconVisible={false}
                type="link"
              />
            </div>
          </div>
        </div>
        {isFeatureModalOpen && (
          <WhatsNewModal
            header="What’s new!"
            onCancel={() => handleFeatureModal(false)}
          />
        )}
      </div>
    </>
  );
};

export default NavBar;
