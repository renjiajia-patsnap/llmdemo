# -*- coding: utf-8 -*-
# @Time : 2025/2/18 下午12:02
# @Author : renjiajia
import os

from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Dict, List
from utils.cache import CacheManager
from requests.exceptions import RequestException
import pandas as pd
import logging
import requests
import json

load_dotenv()

logger = logging.getLogger(__name__)
cache = CacheManager()


class DatabaseConfig(BaseModel):
    """数据库配置模型"""
    base_url: str = "http://data.catalog.patsnap.com/api/catalog"
    phs_ads_db: str = "phs_ads"
    source_id: str = "1721714700074094594"
    request_timeout: int = 30
    max_retries: int = 3


class DatabaseManager:
    """
    数据库工具类
    """

    def __init__(self):
        self.config = DatabaseConfig()
        self._session = requests.Session()
        self._session.verify = False  # 根据实际情况调整SSL验证
        self._init_headers()

    def _init_headers(self) -> None:
        """初始化公共请求头"""
        self._headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-User-ID': 'w-dw-omp-service',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def _get_auth_headers(self) -> Dict:
        """获取带认证的请求头"""
        return {**self._headers, 'X-Authorization': f'Bearer {self._valid_token}'}

    @property
    def _valid_token(self) -> str:
        """获取有效token，自动处理刷新逻辑"""
        token = cache.get('token')
        if not token:
            token = self._refresh_token()
        return token

    def _refresh_token(self) -> str:
        """获取新的访问令牌并更新缓存"""
        url = f"{self.config.base_url}/auth/login"
        payload = json.dumps({
            'username': os.getenv('DB_USERNAME'),
            'password': os.getenv('DB_PASSWORD')
        })

        try:
            response = self._session.post(
                url,
                data=payload,
                headers=self._headers,
                timeout=self.config.request_timeout
            )
            response.raise_for_status()
            token = response.json()['body']['token']
            cache.set('token', token)
            logger.info("Token refreshed successfully")
            return token
        except RequestException as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise

    def get_all_tables(self) -> List:
        """
        获取所有表
        :return:
        """
        table_describe_list = []
        url = f"{self.config.base_url}/query/jdbc/table/list"
        headers = self._get_auth_headers()
        params = {
            'dbName': self.config.phs_ads_db,
            'sourceId': self.config.source_id
        }

        response = requests.get(
            url=url,
            params=params,
            headers=headers,
            verify=False,
        ).json()
        metadata = response['body']['metadata_list']
        # 从metadata 提取表明及注释
        for key, value in metadata.items():
            table_name = key
            table_describe = value['business_description']
            table_describe_list.append((table_name, table_describe))
        # df = pd.DataFrame(table_describe_list, columns=['表名', '注释'])
        # df.to_excel('table_describe2.xlsx', index=False)  # 保存为 Excel 文件
        return table_describe_list

    def get_user_history(self):
        headers = self._get_auth_headers()
        url = f"{self.config.base_url}/query/history/list"
        data = {
            "page_num": 1,
            "page_size": 10000,
            "query": {
                "engine": "jdbc",
                "search": ""
            }
        }

        response = requests.post(
            url=url,
            json=data,
            headers=headers,
            verify=False,
        ).json()
        # response_list = response['body']['list']
        query_list = []
        for item in response['body']['list']:
            # print(item['query_statement'])
            if item['status'] == 'SUCCEEDED':
                query_list.append(item['query_statement'])
        # query_list 存入excel
        df = pd.DataFrame(query_list, columns=['查询语句'])
        df.to_excel('query_list.xlsx', index=False)  # 保存为 Excel 文件

    def sql_execute(self, sql):
        """
        执行sql语句
         :return:
         """
        url = f"{self.config.base_url}/query/jdbc"
        payload = {
            'sql': sql,
            'db_name': self.config.phs_ads_db,
            'source_id': self.config.source_id,
            'export': False
        }
        result = requests.post(url=url, json=payload, headers=self._get_auth_headers()).json()
        return result['body'].get('rows', []) if result else []

    def get_table_ddl(self, table_name):
        # table_ddls = []
        query_table = self.sql_execute(f"show create table {table_name}")
        # table_name = table_name
        table_ddl = query_table[0]['Create Table']
        # print(f"表名：{table_name}，注释：{table_describe}，DDL：{table_ddl}")
        # table_ddls.append((table_name, table_ddl))
        # df = pd.DataFrame(table_ddls, columns=['表名', '表结构'])
        # df.to_excel('table_info.xlsx', index=False)  # 保存为 Excel 文件
        return table_ddl

    def get_sample_table(self, table_name, limit=2):
        # table_data = []
        results = self.sql_execute(f"select * from {table_name} limit {limit}")
        # print(query_table)
        return results

    def get_table_info(self, table_name, limit=2):
        """
        跟怒表名获取表的结构及示例数据
        :param limit:
        :param table_name:
        :return:
        """
        table_ddl = self.get_table_ddl(table_name)
        table_data = self.get_sample_table(table_name, limit)
        # print(f"表名：{table_name}\n表结构：{table_ddl}\n示例数据：{table_data}")
        # 将表结构和示例数据存入组装成str然后返回
        table_info = f"表名：{table_name}\n表结构：{table_ddl}\n示例数据：{table_data}"
        return table_info


if __name__ == '__main__':
    dbtools = DatabaseManager()
    # 获取所有表
    # print(dbtools.get_all_tables())
    # 获取表描述
    # print(dbtools.get_table_describe())
    # 获取用户历史查询
    # dbtools.get_user_history()
    # 获取表结构
    # print(dbtools.get_table_ddl('ads_phs_drug'))
    print(dbtools.get_table_info('ads_phs_drug'))
    # 获取表数据
    # print(dbtools.get_sample_table('ads_phs_drug',limit=3))
