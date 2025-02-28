# -*- coding: utf-8 -*-
# @Time : 2025/1/22 下午7:20
# @Author : renjiajia
from typing import Dict, Any, Sequence
from langchain_core.prompts import PromptTemplate
from langchain.agents import create_react_agent as lang_create_react_agent
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.agents.agent import (
    AgentExecutor,
    RunnableAgent
)
from database.manager import DatabaseManager
from langchain.tools import tool
from sqlalchemy import Result

from utils.cache import CacheManager
from llm.client import LLMClient
from llm.templateprompt import SQL_PREFIX, SQL_SUFFIX, FORMAT_INSTRUCTIONS
from pprint import pprint as pp

# Initialize Data Cache and LLM
data_cache = CacheManager()
llm = LLMClient("tongyi").get_model()
dbmanager = DatabaseManager()

@tool
def get_all_tables(input: str = "") -> dict:
    """Retrieve all tables and their descriptions from the database."""
    if data_cache.exists("all_tables"):
        all_tables = data_cache.get("all_tables")
    else:
        all_tables = dbmanager.get_all_tables()
        data_cache.set("all_tables", all_tables)
    print("Retrieved all available tables:", all_tables)
    return all_tables


@tool
def get_table_info(table_names: str) -> dict:
    """Retrieve the schema and sample data for specified MySQL tables."""
    print("Fetching structure for tables:", table_names)
    tables = [table.strip() for table in table_names.split(",")]
    results = {}
    for table in tables:
        if data_cache.exists(table):
            table_info = data_cache.get(table)
        else:
            table_info = dbmanager.get_table_info(table)
            data_cache.set(table, table_info)
        print(f"Structure for table {table} retrieved:", table_info)
        results[table] = table_info
    return results


@tool
def query_database(query: str) -> str | Sequence[dict[str, Any]] | Result:
    """Execute an SQL query on the database."""
    print("Executing query:", query)
    query_result = dbmanager.sql_execute(query)
    print("Query result:", query_result)
    return query_result


@tool
def query_checker(query: str) -> str:
    """Check if an SQL query is valid. This tool must be used before executing a query."""
    print("Validating SQL query:", query)
    from security.validator import SQLValidator
    is_valid = SQLValidator().validate(query)
    return is_valid


# Add a search tool for non-database queries
search_tool = DuckDuckGoSearchRun(
    name="DuckDuckGoSearch",
    description="For general queries unrelated to biomedicine or the database, such as geography or history."
)

# Define available tools
tools = [search_tool, get_all_tables, get_table_info, query_database, query_checker]


def create_runnable_agent() -> RunnableAgent:
    """Create a RunnableAgent instance with the specified tools and prompt template."""
    template = "\n\n".join([
        SQL_PREFIX,
        "{tools}",
        FORMAT_INSTRUCTIONS,
        SQL_SUFFIX,
    ])
    prompt = PromptTemplate.from_template(template)
    pp(prompt)
    agent = RunnableAgent(
        runnable=lang_create_react_agent(llm=llm, tools=tools, prompt=prompt),
        input_keys_arg=["input"],
        return_keys_arg=["output"]
    )
    return agent


def create_agent_executor() -> AgentExecutor:
    """Create and return an AgentExecutor instance."""
    return AgentExecutor(
        agent=create_runnable_agent(),
        return_intermediate_steps=True,
        callback_manager=None,
        name='mysqlagent',
        tools=tools,
        verbose=True,
        max_iterations=10,
        early_stopping_method='force',
        handle_parsing_errors=True
    )


def natural_language_query_database(message: str):
    """Query the database using natural language."""
    executor_agent = create_agent_executor()
    response = executor_agent.invoke({"input": message})
    return response


if __name__ == "__main__":
    message = '帮我统计下生物类似药最多的原研药物，返回原研药物ID，还有生物类似药个数'
    result = natural_language_query_database(message)
    print("Query Result:", result)
