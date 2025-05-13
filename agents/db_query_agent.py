# -*- coding: utf-8 -*-
# @Time : 2025/1/22 下午7:20
# @Author : renjiajia

"""
数据库查询代理，提供基于自然语言的数据库查询能力
结合LLM模型和数据库工具，将自然语言转换为SQL查询
"""

from typing import Dict, Any, Sequence, Optional, Union
from langchain_core.prompts import PromptTemplate
from langchain.agents import create_react_agent as lang_create_react_agent
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.agents.agent import (
    AgentExecutor,
    RunnableAgent
)
from langchain.schema import AIMessage
from langchain.tools import tool
from sqlalchemy import Result
import json
import re

from database.manager import DatabaseManager
from utils.cache import CacheManager
from utils.logger import logger
from llm.client import LLMClient
from llm.templateprompt import SQL_PREFIX, SQL_SUFFIX, FORMAT_INSTRUCTIONS

# 初始化依赖组件
data_cache = CacheManager()
db_manager = DatabaseManager()

class DBQueryAgent:
    """数据库查询代理，将自然语言转换为SQL查询"""
    
    def __init__(self, model_type: str = "tongyi", model_name: str = None):
        """
        初始化查询代理
        
        Args:
            model_type: LLM模型类型 ("tongyi", "openai", "deepseek")
            model_name: 模型名称，如果为None则使用默认模型
        """
        self.llm = LLMClient(model_type, model_name).get_model()
        
        # 定义工具集合
        self.tools = [
            DuckDuckGoSearchRun(
                name="DuckDuckGoSearch",
                description="用于与数据库无关的一般查询，如地理或历史"
            ),
            self.get_all_tables,
            self.get_table_info,
            self.query_database,
            self.query_checker
        ]
    
    @tool
    def get_all_tables(self, input: str = "") -> dict:
        """获取数据库中的所有表格及其描述。"""
        if data_cache.exists("all_tables"):
            all_tables = data_cache.get("all_tables")
        else:
            all_tables = db_manager.get_all_tables()
            data_cache.set("all_tables", all_tables)
        logger.info("Retrieved all available tables: %s", all_tables)
        return all_tables

    @tool
    def get_table_info(self, table_names: str) -> dict:
        """获取指定表格的结构和示例数据。"""
        logger.info("Fetching structure for tables: %s", table_names)
        tables = [table.strip() for table in table_names.split(",")]
        results = {}
        for table in tables:
            if data_cache.exists(table):
                table_info = data_cache.get(table)
            else:
                table_info = db_manager.get_table_info(table)
                data_cache.set(table, table_info)
            logger.info("Structure for table %s retrieved", table)
            results[table] = table_info
        return results

    @tool
    def query_database(self, query: str) -> str | Sequence[dict[str, Any]] | Result:
        """执行SQL查询并返回结果。"""
        logger.info("Executing query: %s", query)
        query_result = db_manager.sql_execute(query)
        logger.info("Query result retrieved")
        return query_result

    @tool
    def query_checker(self, query: str) -> str:
        """检查SQL查询是否有效。必须在执行查询前使用该工具。"""
        logger.info("Validating SQL query: %s", query)
        from security.validator import SQLValidator
        is_valid, message = SQLValidator().validate(query)
        return f"Valid: {is_valid}, Message: {message}"
    
    def create_agent(self) -> RunnableAgent:
        """创建基于React框架的代理。"""
        template = "\n\n".join([
            SQL_PREFIX,
            "{tools}",
            FORMAT_INSTRUCTIONS,
            SQL_SUFFIX,
        ])
        prompt = PromptTemplate.from_template(template)
        agent = RunnableAgent(
            runnable=lang_create_react_agent(llm=self.llm, tools=self.tools, prompt=prompt),
            input_keys_arg=["input"],
            return_keys_arg=["output"]
        )
        return agent
    
    def create_executor(self) -> AgentExecutor:
        """创建代理执行器。"""
        return AgentExecutor(
            agent=self.create_agent(),
            return_intermediate_steps=True,
            callback_manager=None,
            name='db_query_agent',
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            early_stopping_method='force',
            handle_parsing_errors=True
        )
    
    def query(self, message: str) -> Dict[str, Any]:
        """
        使用自然语言查询数据库
        
        Args:
            message: 自然语言查询字符串
            
        Returns:
            Dict[str, Any]: 包含查询结果和中间步骤的字典
        """
        logger.info("Received query: %s", message)
        executor = self.create_executor()
        response = executor.invoke({"input": message})
        logger.info("Query processed successfully")
        return response

    @staticmethod
    def parse_response(response: Any) -> Dict[str, Any]:
        """
        解析LLM响应为结构化格式
        
        Args:
            response: LLM响应
            
        Returns:
            Dict[str, Any]: 解析后的结构化响应
        """
        if isinstance(response, AIMessage):
            response_content = response.content
        else:
            response_content = str(response)

        # 尝试提取JSON代码块
        json_block = re.search(r'```json\s*({.*?})\s*```', response_content, re.DOTALL)
        if json_block:
            response_content = json_block.group(1)
        else:
            # 尝试提取最外层大括号内容
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                response_content = response_content[start_idx:end_idx + 1]

        # 处理常见格式问题
        response_content = (
            response_content.strip()
            .replace("'", '"')  # 替换单引号
            .replace(""", '"')  # 替换中文引号
            .replace(""", '"')
        )

        try:
            return json.loads(response_content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.error(f"原始内容: {response_content}")
            return {"error": "无法解析LLM响应"}


def natural_language_query_database(message: str, model_type: str = "tongyi", model_name: str = None) -> Dict[str, Any]:
    """
    使用自然语言查询数据库的便捷函数
    
    Args:
        message: 自然语言查询字符串
        model_type: 使用的模型类型
        model_name: 使用的模型名称
        
    Returns:
        Dict[str, Any]: 查询结果
    """
    agent = DBQueryAgent(model_type, model_name)
    return agent.query(message)


if __name__ == "__main__":
    # 示例查询
    query_message = '帮我统计下生物类似药最多的原研药物，返回原研药物ID，还有生物类似药个数'
    result = natural_language_query_database(query_message)
    print("查询结果:", result["output"])
    print("中间步骤:", result["intermediate_steps"]) 