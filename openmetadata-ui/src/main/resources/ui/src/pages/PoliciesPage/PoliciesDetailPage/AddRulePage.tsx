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

import { Button, Card, Col, Form, Row, Space, Typography } from 'antd';
import { AxiosError } from 'axios';
import { compare } from 'fast-json-patch';
import React, { useEffect, useMemo, useState } from 'react';
import { useHistory, useParams } from 'react-router-dom';
import { getPolicyByName, patchPolicy } from '../../../axiosAPIs/rolesAPIV1';
import TitleBreadcrumb from '../../../components/common/title-breadcrumb/title-breadcrumb.component';
import Loader from '../../../components/Loader/Loader';
import { GlobalSettingOptions } from '../../../constants/globalSettings.constants';
import { Effect, Rule } from '../../../generated/api/policies/createPolicy';
import { Policy } from '../../../generated/entity/policies/policy';
import { getEntityName } from '../../../utils/CommonUtils';
import {
  getPath,
  getPolicyWithFqnPath,
  getSettingPath,
} from '../../../utils/RouterUtils';
import { showErrorToast } from '../../../utils/ToastUtils';
import RuleForm from '../RuleForm/RuleForm';

const policiesPath = getPath(GlobalSettingOptions.POLICIES);

const AddRulePage = () => {
  const history = useHistory();
  const { fqn } = useParams<{ fqn: string }>();
  const [isLoading, setLoading] = useState<boolean>(false);
  const [policy, setPolicy] = useState<Policy>({} as Policy);
  const [ruleData, setRuleData] = useState<Rule>({
    name: '',
    description: '',
    resources: [],
    operations: [],
    condition: '',
    effect: Effect.Allow,
  });

  const breadcrumb = useMemo(
    () => [
      {
        name: 'Settings',
        url: getSettingPath(),
      },
      {
        name: 'Policies',
        url: policiesPath,
      },
      {
        name: getEntityName(policy),
        url: getPolicyWithFqnPath(fqn),
      },

      {
        name: 'Add New Rule',
        url: '',
      },
    ],
    [fqn, policy]
  );

  const fetchPolicy = async () => {
    setLoading(true);
    try {
      const data = await getPolicyByName(fqn, 'owner,location,teams,roles');
      setPolicy(data ?? ({} as Policy));
    } catch (error) {
      showErrorToast(error as AxiosError);
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    history.push(getPolicyWithFqnPath(fqn));
  };

  const handleSubmit = async () => {
    const patch = compare(policy, {
      ...policy,
      rules: [...policy.rules, ruleData],
    });
    try {
      const data = await patchPolicy(patch, policy.id);
      if (data) {
        handleBack();
      }
    } catch (error) {
      showErrorToast(error as AxiosError);
    }
  };

  useEffect(() => {
    fetchPolicy();
  }, [fqn]);

  if (isLoading) {
    return <Loader />;
  }

  return (
    <Row className="tw-bg-body-main tw-h-auto" gutter={[16, 16]}>
      <Col offset={5} span={14}>
        <TitleBreadcrumb titleLinks={breadcrumb} />
        <Card>
          <Typography.Paragraph className="tw-text-base">
            Add New Rule
          </Typography.Paragraph>
          <Form
            data-testid="rule-form"
            id="rule-form"
            initialValues={{
              ruleEffect: ruleData.effect,
            }}
            layout="vertical"
            onFinish={handleSubmit}>
            <RuleForm ruleData={ruleData} setRuleData={setRuleData} />
            <Space align="center" className="tw-w-full tw-justify-end">
              <Button type="link" onClick={handleBack}>
                Cancel
              </Button>
              <Button form="rule-form" htmlType="submit" type="primary">
                Submit
              </Button>
            </Space>
          </Form>
        </Card>
      </Col>
    </Row>
  );
};

export default AddRulePage;
