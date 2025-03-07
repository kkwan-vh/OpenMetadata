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

import { Button, Empty, Modal, Table, Tabs, Typography } from 'antd';
import { ColumnsType } from 'antd/lib/table';
import { AxiosError } from 'axios';
import { compare } from 'fast-json-patch';
import { isEmpty, isUndefined } from 'lodash';
import { EntityReference } from 'Models';
import React, { useEffect, useMemo, useState } from 'react';
import { Link, useHistory, useParams } from 'react-router-dom';
import { getRoleByName, patchRole } from '../../../axiosAPIs/rolesAPIV1';
import Description from '../../../components/common/description/Description';
import RichTextEditorPreviewer from '../../../components/common/rich-text-editor/RichTextEditorPreviewer';
import TitleBreadcrumb from '../../../components/common/title-breadcrumb/title-breadcrumb.component';
import Loader from '../../../components/Loader/Loader';
import { getUserPath } from '../../../constants/constants';
import {
  GlobalSettingOptions,
  GlobalSettingsMenuCategory,
} from '../../../constants/globalSettings.constants';
import { EntityType } from '../../../enums/entity.enum';
import { Role } from '../../../generated/entity/teams/role';
import { getEntityName } from '../../../utils/CommonUtils';
import {
  getPolicyWithFqnPath,
  getSettingPath,
  getTeamsWithFqnPath,
} from '../../../utils/RouterUtils';
import SVGIcons, { Icons } from '../../../utils/SvgUtils';
import { showErrorToast } from '../../../utils/ToastUtils';
import './RolesDetail.less';

const { TabPane } = Tabs;

type Attribute = 'policies' | 'teams' | 'users';

const List = ({
  list,
  type,
  onDelete,
}: {
  list: EntityReference[];
  type: 'policy' | 'team' | 'user';
  onDelete: (record: EntityReference) => void;
}) => {
  const columns: ColumnsType<EntityReference> = useMemo(() => {
    return [
      {
        title: 'Name',
        dataIndex: 'name',
        width: '200px',
        key: 'name',
        render: (_, record) => {
          let link = '';
          switch (type) {
            case 'policy':
              link = getPolicyWithFqnPath(record.fullyQualifiedName || '');

              break;
            case 'team':
              link = getTeamsWithFqnPath(record.fullyQualifiedName || '');

              break;
            case 'user':
              link = getUserPath(record.fullyQualifiedName || '');

              break;

            default:
              break;
          }

          return (
            <Link className="hover:tw-underline tw-cursor-pointer" to={link}>
              {getEntityName(record)}
            </Link>
          );
        },
      },
      {
        title: 'Description',
        dataIndex: 'description',
        key: 'description',
        render: (_, record) => (
          <RichTextEditorPreviewer markdown={record?.description || ''} />
        ),
      },
      {
        title: 'Actions',
        dataIndex: 'actions',
        width: '80px',
        key: 'actions',
        render: (_, record) => {
          return (
            <Button type="text" onClick={() => onDelete(record)}>
              <SVGIcons alt="remove" icon={Icons.ICON_REMOVE} title="Remove" />
            </Button>
          );
        },
      },
    ];
  }, []);

  return (
    <Table
      className="list-table"
      columns={columns}
      dataSource={list}
      pagination={false}
      size="middle"
    />
  );
};

const RolesDetailPage = () => {
  const history = useHistory();
  const { fqn } = useParams<{ fqn: string }>();

  const [role, setRole] = useState<Role>({} as Role);
  const [isLoading, setLoading] = useState<boolean>(false);
  const [editDescription, setEditDescription] = useState<boolean>(false);
  const [selectedEntity, setEntity] =
    useState<{ attribute: Attribute; record: EntityReference }>();

  const rolesPath = getSettingPath(
    GlobalSettingsMenuCategory.ACCESS,
    GlobalSettingOptions.ROLES
  );

  const breadcrumb = useMemo(
    () => [
      {
        name: 'Roles',
        url: rolesPath,
      },
      {
        name: fqn,
        url: '',
      },
    ],
    [fqn]
  );

  const fetchRole = async () => {
    setLoading(true);
    try {
      const data = await getRoleByName(fqn, 'policies,teams,users');
      setRole(data ?? ({} as Role));
    } catch (error) {
      showErrorToast(error as AxiosError);
    } finally {
      setLoading(false);
    }
  };

  const handleDescriptionUpdate = async (description: string) => {
    const patch = compare(role, { ...role, description });
    try {
      const data = await patchRole(patch, role.id);
      setRole({ ...role, description: data.description });
    } catch (error) {
      showErrorToast(error as AxiosError);
    } finally {
      setEditDescription(false);
    }
  };

  const handleDelete = async (data: EntityReference, attribute: Attribute) => {
    const attributeData =
      (role[attribute as keyof Role] as EntityReference[]) ?? [];
    const updatedAttributeData = attributeData.filter(
      (attrData) => attrData.id !== data.id
    );

    const patch = compare(role, {
      ...role,
      [attribute as keyof Role]: updatedAttributeData,
    });
    try {
      const data = await patchRole(patch, role.id);
      setRole(data);
    } catch (error) {
      showErrorToast(error as AxiosError);
    }
  };

  useEffect(() => {
    fetchRole();
  }, [fqn]);

  if (isLoading) {
    return <Loader />;
  }

  return (
    <div data-testid="role-details-container">
      <TitleBreadcrumb titleLinks={breadcrumb} />
      {isEmpty(role) ? (
        <Empty description={`No roles found for ${fqn}`}>
          <Button
            size="small"
            type="primary"
            onClick={() => history.push(rolesPath)}>
            Go Back
          </Button>
        </Empty>
      ) : (
        <div className="roles-detail" data-testid="role-details">
          <div className="tw--ml-5">
            <Description
              description={role.description || ''}
              entityFqn={role.fullyQualifiedName}
              entityName={getEntityName(role)}
              entityType={EntityType.ROLE}
              isEdit={editDescription}
              onCancel={() => setEditDescription(false)}
              onDescriptionEdit={() => setEditDescription(true)}
              onDescriptionUpdate={handleDescriptionUpdate}
            />
          </div>
          <Tabs defaultActiveKey="policies">
            <TabPane key="policies" tab="Policies">
              <List
                list={role.policies ?? []}
                type="policy"
                onDelete={(record) =>
                  setEntity({ record, attribute: 'policies' })
                }
              />
            </TabPane>
            <TabPane key="teams" tab="Teams">
              <List
                list={role.teams ?? []}
                type="team"
                onDelete={(record) => setEntity({ record, attribute: 'teams' })}
              />
            </TabPane>
            <TabPane key="users" tab="Users">
              <List
                list={role.users ?? []}
                type="user"
                onDelete={(record) => setEntity({ record, attribute: 'users' })}
              />
            </TabPane>
          </Tabs>
        </div>
      )}
      {selectedEntity && (
        <Modal
          centered
          okText="Confirm"
          title={`Remove ${getEntityName(
            selectedEntity.record
          )} from ${getEntityName(role)}`}
          visible={!isUndefined(selectedEntity.record)}
          onCancel={() => setEntity(undefined)}
          onOk={() => {
            handleDelete(selectedEntity.record, selectedEntity.attribute);
            setEntity(undefined);
          }}>
          <Typography.Text>
            Are you sure you want to remove the{' '}
            {`${getEntityName(selectedEntity.record)} from ${getEntityName(
              role
            )}?`}
          </Typography.Text>
        </Modal>
      )}
    </div>
  );
};

export default RolesDetailPage;
