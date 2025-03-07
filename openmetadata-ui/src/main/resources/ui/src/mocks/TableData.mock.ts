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

import { Table } from '../generated/entity/data/table';

export const MOCK_TABLE = {
  id: 'cb726d24-774b-4603-8ec8-1975760ac2f8',
  name: 'dim_address',
  fullyQualifiedName: 'sample_data.ecommerce_db.shopify.dim_address',
  description:
    // eslint-disable-next-line max-len
    'This dimension table contains the billing and shipping addresses of customers. You can join this table with the sales table to generate lists of the billing and shipping addresses. Customers can enter their addresses more than once, so the same address can appear in more than one row in this table. This table contains one row per customer address.',
  version: 0.1,
  updatedAt: 1659764891329,
  updatedBy: 'anonymous',
  href: 'http://localhost:8585/api/v1/tables/cb726d24-774b-4603-8ec8-1975760ac2f8',
  tableType: 'Regular',
  columns: [
    {
      name: 'address_id',
      dataType: 'NUMERIC',
      dataTypeDisplay: 'numeric',
      description: 'Unique identifier for the address.',
      fullyQualifiedName:
        'sample_data.ecommerce_db.shopify.dim_address.address_id',
      tags: [],
      ordinalPosition: 1,
      profile: {
        name: 'shop_id',
        valuesCount: 14567,
        nullCount: 0,
        nullProportion: 0,
        uniqueCount: 14567,
        uniqueProportion: 1,
        distinctCount: 14509,
        distinctProportion: 1,
        min: 1,
        max: 587,
        mean: 45,
        sum: 1367,
        stddev: 35,
        median: 7654,
      },
    },
    {
      name: 'shop_id',
      dataType: 'NUMERIC',
      dataTypeDisplay: 'numeric',
      description:
        'The ID of the store. This column is a foreign key reference to the shop_id column in the dim_shop table.',
      fullyQualifiedName:
        'sample_data.ecommerce_db.shopify.dim_address.shop_id',
      tags: [],
      ordinalPosition: 2,
      profile: {
        name: 'address_id',
        valuesCount: 14567,
        nullCount: 0,
        nullProportion: 0,
        uniqueCount: 14567,
        uniqueProportion: 1,
        distinctCount: 14509,
        distinctProportion: 1,
        min: 1,
        max: 14509,
        mean: 567,
        sum: 34526,
        stddev: 190,
        median: 7654,
      },
    },
    {
      name: 'first_name',
      dataType: 'VARCHAR',
      dataLength: 100,
      dataTypeDisplay: 'varchar',
      description: 'First name of the customer.',
      fullyQualifiedName:
        'sample_data.ecommerce_db.shopify.dim_address.first_name',
      tags: [],
      ordinalPosition: 3,
      profile: {
        name: 'first_name',
        valuesCount: 14509,
        nullCount: 25,
        nullProportion: 0.001,
        uniqueCount: 0,
        uniqueProportion: 0,
        distinctCount: 5,
        distinctProportion: 0.050505050505050504,
        minLength: 6,
        maxLength: 14,
        mean: 8,
      },
    },
    {
      name: 'last_name',
      dataType: 'VARCHAR',
      dataLength: 100,
      dataTypeDisplay: 'varchar',
      description: 'Last name of the customer.',
      fullyQualifiedName:
        'sample_data.ecommerce_db.shopify.dim_address.last_name',
      tags: [],
      ordinalPosition: 4,
      profile: {
        name: 'last_name',
        valuesCount: 14509,
        nullCount: 167,
        nullProportion: 0.01,
        uniqueCount: 1398,
        uniqueProportion: 0.7976,
        distinctCount: 5,
        distinctProportion: 0.050505050505050504,
        minLength: 6,
        maxLength: 15,
        mean: 8,
      },
    },
  ],
  tableConstraints: [
    {
      constraintType: 'PRIMARY_KEY',
      columns: ['address_id', 'shop_id'],
    },
  ],
  databaseSchema: {
    id: '0106638e-cadf-43a3-885d-cd2fd4b53df9',
    type: 'databaseSchema',
    name: 'shopify',
    fullyQualifiedName: 'sample_data.ecommerce_db.shopify',
    description:
      'This **mock** database contains schema related to shopify sales and orders with related dimension tables.',
    deleted: false,
    href: 'http://localhost:8585/api/v1/databaseSchemas/0106638e-cadf-43a3-885d-cd2fd4b53df9',
  },
  database: {
    id: '27960526-0b15-4794-b3ff-1162da9b070d',
    type: 'database',
    name: 'ecommerce_db',
    fullyQualifiedName: 'sample_data.ecommerce_db',
    description:
      'This **mock** database contains schemas related to shopify sales and orders with related dimension tables.',
    deleted: false,
    href: 'http://localhost:8585/api/v1/databases/27960526-0b15-4794-b3ff-1162da9b070d',
  },
  service: {
    id: '0c1dac5d-f802-454d-a1dc-e219f4fcc60c',
    type: 'databaseService',
    name: 'sample_data',
    fullyQualifiedName: 'sample_data',
    deleted: false,
    href: 'http://localhost:8585/api/v1/services/databaseServices/0c1dac5d-f802-454d-a1dc-e219f4fcc60c',
  },
  serviceType: 'BigQuery',
  tags: [],
  usageSummary: {
    dailyStats: {
      count: 1,
      percentileRank: 0,
    },
    weeklyStats: {
      count: 1,
      percentileRank: 0,
    },
    monthlyStats: {
      count: 1,
      percentileRank: 0,
    },
    date: '2022-08-06',
  },
  followers: [],
  joins: {
    startDate: '2022-07-09',
    dayCount: 30,
    columnJoins: [],
    directTableJoins: [],
  },
  profile: {
    timestamp: 1659764894,
    columnCount: 12,
    rowCount: 14567,
  },
  tableQueries: [
    {
      query:
        'create table shopify.dim_address_clean as select address_id, shop_id, first_name, last_name, address1 as address, company, city, region, zip, country, phone from shopify.dim_address',
      vote: 1,
      checksum: 'cd59a9d0d0b8a245f7382264afac8bdc',
    },
  ],
  deleted: false,
} as unknown as Table;
