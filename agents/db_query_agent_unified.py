#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author : renjiajia

"""
统一数据库查询代理模块
整合了原有的querydbagent.py、main.py和querydb_grap.py的核心功能
提供基于自然语言的数据库查询能力，支持相似问题匹配、用户意图分析和SQL生成执行
"""

import json
import re
from typing import Dict, Any, Sequence, Optional, TypedDict, List, Union
from functools import lru_cache

# LangChain依赖
from langchain_core.prompts import PromptTemplate
from langchain.agents import create_react_agent
from langchain.agents.agent import AgentExecutor, RunnableAgent
from langchain.schema import AIMessage, Document
from langchain.tools import tool
from sqlalchemy import Result
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langgraph.graph import Graph, StateGraph

# 项目内部依赖
from database.manager import DatabaseManager
from utils.cache import CacheManager
from utils.logger import logger
from utils.qapair import QAPairManager
from llm.client import LLMClient
from llm.templateprompt import SQL_PREFIX, SQL_SUFFIX, FORMAT_INSTRUCTIONS

# 初始化基础组件
data_cache = CacheManager()
db_manager = DatabaseManager()


class WorkflowState(TypedDict):
    """图工作流状态定义"""
    input: str          # 初始用户问题
    question: str       # 来自起始节点的已处理问题
    result: Any         # 中间结果的灵活类型（例如，带有 'answer'、'sql' 等的 dict）
    answer: str         # 返回的最终答案
    error: bool         # 错误标志


class DBQueryTools:
    """数据库查询工具集合"""
    
    def __init__(self):
        """初始化数据库查询工具"""
        pass
    
    @staticmethod
    @tool
    def get_all_tables(input: str = "") -> Dict[str, Any]:
        """从数据库中检索所有表及其描述"""
        if data_cache.exists("all_tables"):
            all_tables = data_cache.get("all_tables")
        else:
            all_tables = db_manager.get_all_tables()
            data_cache.set("all_tables", all_tables)
        logger.info("检索到所有可用表: %s", all_tables)
        return all_tables

    @staticmethod
    @tool
    def get_table_info(table_names: str) -> Dict[str, Any]:
        """检索指定MySQL表的结构和示例数据"""
        logger.info("获取表结构: %s", table_names)
        tables = [table.strip() for table in table_names.split(",")]
        results = {}
        for table in tables:
            if data_cache.exists(table):
                table_info = data_cache.get(table)
            else:
                table_info = db_manager.get_table_info(table)
                data_cache.set(table, table_info)
            logger.info("成功获取表 %s 的结构", table)
            results[table] = table_info
        return results

    @staticmethod
    @tool
    def query_database(query: str) -> Union[str, Sequence[Dict[str, Any]], Result]:
        """在数据库上执行SQL查询"""
        logger.info("执行查询: %s", query)
        query_result = db_manager.sql_execute(query)
        logger.info("查询结果已获取")
        return query_result

    @staticmethod
    @tool
    def query_checker(query: str) -> str:
        """检查SQL查询是否有效，在执行查询前必须使用此工具"""
        logger.info("验证SQL查询: %s", query)
        from security.validator import SQLValidator
        is_valid, message = SQLValidator().validate(query)
        return f"Valid: {is_valid}, Message: {message}"


class QuestionSimilaritySearcher:
    """问题相似度搜索器"""
    
    def __init__(self, embeddings_provider=None, qa_manager=None):
        """初始化相似度搜索器"""
        self.vector_store = None
        self.processed_questions = set()
        self._embeddings = embeddings_provider or OpenAIEmbeddings()
        self.qa_manager = qa_manager or QAPairManager(file_path='data/qa_pairs.xlsx')

    def _initialize_vector_store(self, docs):
        """初始化向量存储"""
        if not docs:
            return
        self.vector_store = FAISS.from_documents(docs, self._embeddings)
        self.processed_questions = {doc.page_content for doc in docs}

    def _update_vector_store(self, new_docs):
        """增量更新向量存储"""
        if not new_docs:
            return
        new_docs_to_add = [doc for doc in new_docs
                           if doc.page_content not in self.processed_questions]
        if new_docs_to_add:
            if self.vector_store is None:
                self.vector_store = FAISS.from_documents(new_docs_to_add, self._embeddings)
            else:
                self.vector_store.add_documents(new_docs_to_add)
            self.processed_questions.update(doc.page_content for doc in new_docs_to_add)

    def find_similar_question(self, user_question: str, similarity_threshold: float = 0.95) -> Dict[str, Any]:
        """
        根据输入问题查找相似的问题
        
        Args:
            user_question: 用户问题
            similarity_threshold: 相似度阈值，超过此值认为找到相似问题
            
        Returns:
            Dict: 包含匹配到的SQL和答案，如果未找到则返回空答案
        """
        logger.info("开始查找相似问题")
        
        # 从QA管理器获取问答对
        docs = [Document(page_content=q, metadata=info)
                for q, info in self.qa_manager.qa_pairs.items()]

        if not docs:
            logger.info("问答库为空，无法找到相似问题")
            return {"question": user_question, "answer": ""}

        # 初始化或更新向量存储
        if self.vector_store is None:
            self._initialize_vector_store(docs)
        else:
            self._update_vector_store(docs)

        # 执行相似度搜索
        results = self.vector_store.similarity_search_with_score(user_question, k=1)
        
        if not results:
            logger.info("搜索结果为空")
            return {"question": user_question, "answer": ""}
            
        similar_score = 1 - results[0][1]

        # 如果找到相似问题且相似度超过阈值
        if similar_score > similarity_threshold:
            logger.info("找到相似问题: %s", results[0][0].page_content)
            logger.info("相似度分数: %s", similar_score)
            return {
                "sql": results[0][0].metadata.get('sql', ''),
                "answer": results[0][0].metadata.get('answer', ''),
                "question": user_question
            }

        logger.info("未找到达到阈值的相似问题")
        return {"question": user_question, "answer": ""}

    @staticmethod
    @lru_cache(maxsize=1)
    def get_instance(embeddings_provider=None, qa_manager=None):
        """获取单例实例"""
        return QuestionSimilaritySearcher(embeddings_provider, qa_manager)


class DBQueryAgent:
    """基于React框架的数据库查询代理"""
    
    def __init__(self, model_type: str = "tongyi", model_name: Optional[str] = None):
        """
        初始化查询代理
        
        Args:
            model_type: LLM模型类型 ("tongyi", "openai", "deepseek")
            model_name: 模型名称，如果为None则使用默认模型
        """
        self.llm = LLMClient(model_type, model_name).get_model()
        self.tools = DBQueryTools()
        
        # 定义工具集合
        self.available_tools = [
            DuckDuckGoSearchRun(
                name="DuckDuckGoSearch",
                description="用于与数据库无关的一般查询，如地理或历史"
            ),
            self.tools.get_all_tables,
            self.tools.get_table_info,
            self.tools.query_database,
            self.tools.query_checker
        ]
    
    def create_agent(self) -> RunnableAgent:
        """创建基于React框架的代理"""
        template = "\n\n".join([
            SQL_PREFIX,
            "{tools}",
            FORMAT_INSTRUCTIONS,
            SQL_SUFFIX,
        ])
        prompt = PromptTemplate.from_template(template)
        agent = RunnableAgent(
            runnable=create_react_agent(llm=self.llm, tools=self.available_tools, prompt=prompt),
            input_keys_arg=["input"],
            return_keys_arg=["output"]
        )
        return agent
    
    def create_executor(self) -> AgentExecutor:
        """创建代理执行器"""
        return AgentExecutor(
            agent=self.create_agent(),
            return_intermediate_steps=True,
            callback_manager=None,
            name='db_query_agent',
            tools=self.available_tools,
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
        logger.info("收到查询: %s", message)
        executor = self.create_executor()
        response = executor.invoke({"input": message})
        logger.info("查询处理成功")
        return response


class WorkflowEngine:
    """工作流引擎，使用LangGraph构建数据库查询流程"""
    
    def __init__(self, model_type: str = "openai", model_name: str = "o3-mini"):
        """初始化工作流引擎"""
        self.llm = LLMClient(model_type, model_name).get_model()
        self.embeddings = OpenAIEmbeddings()
        self.qa_manager = QAPairManager()
        self.tools = DBQueryTools()
    
    def parse_llm_response(self, response: Any) -> Dict[str, Any]:
        """解析LLM响应为结构化格式"""
        if isinstance(response, AIMessage):
            response_content = response.content
        else:
            response_content = str(response)
        try:
            return json.loads(response_content)
        except json.JSONDecodeError as e:
            logger.info(f"JSON解析失败: {e}")
            logger.info(f"原始内容: {response_content}")
            return {"error": "无法解析LLM响应"}
    
    def analyze_user_intent(self, user_question: str) -> Dict[str, Any]:
        """分析用户问题意图"""
        logger.info("开始分析用户意图")
        table_description = self.tools.get_all_tables("")
        prompt = (
            f"请分析用户的自然语言问题，分析用户问题意图。问题如下：\n{user_question}\n\n"
            f"可用表信息：\n{table_description}\n\n"
            f"返回JSON：{{'intent': '意图', 'tables': ['表1', '表2']}}"
        )
        response = self.llm.invoke(prompt)
        result = self.parse_llm_response(response)
        result["original_input"] = user_question
        logger.info("用户意图分析结果: %s", result)
        return result
    
    def generate_sql(self, intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """根据用户意图生成SQL查询"""
        logger.info("开始生成SQL")
        intent = intent_analysis.get("intent", "")
        tables = intent_analysis.get("tables", [])
        
        if not tables:
            return {"error": "未找到相关表"}
            
        table_info = self.tools.get_table_info(",".join(tables))
        prompt = (
            f"您是旨在与TiDB（兼容 MySQL 5.7 的分布式数据库）数据库交互的代理。给定一个输入问题，创建一个语法正确的 MySQL 查询。\n"
            f"除非用户指定了他们希望获取的特定数量的示例，否则请始终将查询限制为最多 5 个结果。\n"
            f"您可以按相关列对结果进行排序，以返回数据库中最相关示例。\n"
            f"永远不要查询特定表中的所有列，只询问给定问题的相关列。不要对数据库进行任何 DML 语句（INSERT、UPDATE、DELETE、DROP 等）。\n"
            f"如果问题似乎与数据库无关，只需返回 I don't know作为答案。\n"
            f"特别注意：对于涉及多个表的问题，请使用 JOIN 语句来连接相关表，并确保查询语句包含所有必要的表和字段。\n"
            f"用户意图：{intent}\n"
            f"可能相关的业务表信息如下：\n{table_info}\n\n"
            f"请生成一个 SQL 查询，以回答用户的问题。"
            f"返回JSON：{{'sql': 'SELECT * FROM table WHERE column = value'}}"
        )
        response = self.llm.invoke(prompt)
        sql_obj = self.parse_llm_response(response)
        user_question = intent_analysis.get("original_input", "")
        
        result = {
            "original_input": user_question,
            "tables": tables,
            "sql": sql_obj.get("sql", "")
        }
        logger.info("生成的SQL: %s", result)
        return result
    
    def execute_sql(self, sql_info: Dict[str, Any]) -> Dict[str, Any]:
        """执行SQL查询"""
        logger.info("开始执行SQL")
        sql = sql_info.get("sql", "")
        
        if not sql:
            return {"error": "无有效的SQL语句"}
            
        try:
            sql_results = self.tools.query_database(sql)
            user_question = sql_info.get("original_input", "")
            result = {
                "original_input": user_question,
                "sql": sql,
                "query_result": sql_results
            }
            logger.info("SQL执行成功")
            return result
        except Exception as e:
            logger.error("SQL执行错误: %s", str(e))
            return {
                "error": f"SQL执行错误: {str(e)}",
                "original_input": sql_info.get("original_input", ""),
                "sql": sql
            }
    
    def summarize_result(self, execution_result: Dict[str, Any]) -> str:
        """总结SQL执行结果"""
        logger.info("开始总结结果")
        if "error" in execution_result:
            return f"执行过程中遇到错误: {execution_result['error']}"
            
        query_result = execution_result.get("query_result", [])
        user_question = execution_result.get("original_input", "未提供用户问题")
        
        prompt = (
            f"您是一个数据库查询结果解释器。用户的问题是：{user_question}\n\n"
            f"执行的SQL查询是：{execution_result.get('sql', '')}\n\n"
            f"查询结果为：\n{query_result}\n\n"
            f"请用简洁明了的中文总结这些结果，以回答用户的问题。"
        )
        
        response = self.llm.invoke(prompt)
        
        if isinstance(response, AIMessage):
            summary = response.content
        else:
            summary = str(response)
            
        logger.info("结果总结完成")
        # 更新问答对
        self.qa_manager.update_qa_pairs(
            user_question,
            execution_result.get("sql", ""),
            summary
        )
        
        return summary
    
    def create_workflow_graph(self) -> Graph:
        """创建工作流程图"""
        # 定义节点
        def find_similar_question_node(state):
            question = state["input"]
            searcher = QuestionSimilaritySearcher.get_instance(self.embeddings, self.qa_manager)
            result = searcher.find_similar_question(question)
            return {"question": question, "result": result}
            
        def analyze_intent_node(state):
            question = state["question"]
            intent_analysis = self.analyze_user_intent(question)
            return {"result": intent_analysis}
            
        def generate_sql_node(state):
            intent_data = state["result"]
            sql_info = self.generate_sql(intent_data)
            return {"result": sql_info}
            
        def execute_sql_node(state):
            sql_info = state["result"]
            execution_result = self.execute_sql(sql_info)
            return {"result": execution_result}
            
        def summarize_node(state):
            execution_result = state["result"]
            summary = self.summarize_result(execution_result)
            return {"answer": summary}
        
        # 构建工作流程图
        workflow = StateGraph(WorkflowState)
        
        # 添加节点
        workflow.add_node("find_similar", find_similar_question_node)
        workflow.add_node("analyze_intent", analyze_intent_node)
        workflow.add_node("generate_sql", generate_sql_node)
        workflow.add_node("execute_sql", execute_sql_node)
        workflow.add_node("summarize", summarize_node)
        
        # 定义工作流程路由
        def route_after_similar(state: WorkflowState) -> str:
            result = state["result"]
            if result.get("answer"):  # 如果找到了相似问题
                logger.info("找到相似问题，直接返回结果")
                return "summarize"
            logger.info("未找到相似问题，开始分析用户意图")
            return "analyze_intent"
        
        # 连接节点
        workflow.set_entry_point("find_similar")
        workflow.add_conditional_edges(
            "find_similar",
            route_after_similar,
            {
                "summarize": "summarize",
                "analyze_intent": "analyze_intent"
            }
        )
        workflow.add_edge("analyze_intent", "generate_sql")
        workflow.add_edge("generate_sql", "execute_sql")
        workflow.add_edge("execute_sql", "summarize")
        workflow.set_finish_point("summarize")
        
        return workflow.compile()
    
    def query(self, question: str) -> str:
        """执行完整的查询流程"""
        logger.info("开始处理用户问题: %s", question)
        workflow = self.create_workflow_graph()
        result = workflow.invoke({"input": question, "question": question})
        logger.info("问题处理完成")
        return result["answer"]


# 便捷函数
def direct_query_database(message: str, model_type: str = "tongyi", model_name: str = None) -> Dict[str, Any]:
    """使用React代理直接查询数据库（使用原始querydbagent.py的方式）"""
    agent = DBQueryAgent(model_type, model_name)
    return agent.query(message)


def workflow_query_database(message: str, model_type: str = "openai", model_name: str = "o3-mini") -> str:
    """使用工作流引擎查询数据库（使用querydb_grap.py的方式）"""
    engine = WorkflowEngine(model_type, model_name)
    return engine.query(message)


if __name__ == "__main__":
    # 示例查询
    query_message = '帮我统计下生物类似药最多的原研药物，返回原研药物ID，还有生物类似药个数'
    
    # 方法1：使用React代理
    # result = direct_query_database(query_message)
    # print("查询结果:", result["output"])
    # print("中间步骤:", result["intermediate_steps"])
    
    # 方法2：使用工作流引擎
    result = workflow_query_database(query_message)
    print("查询结果:", result) 