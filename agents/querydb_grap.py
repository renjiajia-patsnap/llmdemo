from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langgraph.graph import Graph,StateGraph
from database.manager import DatabaseManager
from langchain.schema import AIMessage
from typing import Dict, Any,TypedDict
from langchain.schema import Document
from utils.cache import CacheManager
from utils.qapair import QAPairManager
from llm.client import LLMClient
from langchain.tools import tool
from utils.logger import logger
from langchain.agents import AgentExecutor
import json

# 初始化数据缓存和 LLM
databasemanager = DatabaseManager()
data_cache = CacheManager()

# 加载 OpenAI 的嵌入模型
embeddings = OpenAIEmbeddings()
llm = LLMClient("openai",'o3-mini').get_model()
qa_manager = QAPairManager(file_path='data/qa_pairs2.xlsx')

# llm = LLMClient("tongyi").get_model()


# Supporting Tools
@tool
def get_all_tables(input="") -> Dict[str, Any]:
    """从数据库中检索所有表及其描述。"""
    if data_cache.exists("all_tables"):
        all_tables = data_cache.get("all_tables")
    else:
        all_tables = databasemanager.get_all_tables()
        data_cache.set("all_tables", all_tables)
    logger.info("Retrieved all available tables: %s", all_tables)
    return all_tables


@tool
def get_table_info(table_names: str) -> Dict[str, Any]:
    """检索指定 MySQL 表的架构和示例数据。"""
    tables = [table.strip() for table in table_names.split(",")]
    results = {}
    for table in tables:
        if data_cache.exists(table):
            table_info = data_cache.get(table)
        else:
            table_info = databasemanager.get_table_info(table)
            data_cache.set(table, table_info)
        logger.info("Structure for table %s retrieved: %s", table, table_info)
        results[table] = table_info
    return results


@tool
def query_database(query: str) -> Any:
    """Execute an SQL query on the database."""
    logger.info("Executing query: %s", query)
    query_result = databasemanager.sql_execute(query)
    print("Query result: %s", query_result)
    return query_result


def parse_llm_response(response: Any) -> Dict[str, Any]:
    """
    解析来自 LLM 模型的响应并提取 JSON 内容。
    """
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


class AgentFactory:
    """代理创建工厂，封装代理逻辑"""
    @staticmethod
    def find_similar_question(input:Dict[str, Any]) -> Dict[str, Any]:
        """
        根据输入问题查找相似的问题。
        """
        logger.info("Finding similar question beginning>>>>>>>>>>>>>>>>>>>>>>>>")
        logger.info("find_similar_question input: %s", input)
        user_question = input.get("question", "")
        docs = [Document(page_content=q, metadata=info) for q, info in qa_manager.qa_pairs.items()]
        if not docs:
            return {"question": user_question, "answer": ""}
        vector_store = FAISS.from_documents(docs, embeddings)
        results = vector_store.similarity_search_with_score(user_question, k=1)
        similar_score = 1 - results[0][1] if results else 0
        if results and similar_score > 0.95:
            logger.info("Found similar question: %s", results[0][0].page_content)
            logger.info("Similarity score: %s", similar_score)
            logger.info("Finding similar question end>>>>>>>>>>>>>>>>>>>>>>>>")
            return {"sql": results[0][0].metadata['sql'], "answer": results[0][0].metadata['answer'],
                    "question": user_question}
        result = {"question": user_question, "answer": ""}
        logger.info("No similar question found")
        logger.info("Finding similar question end>>>>>>>>>>>>>>>>>>>>>>>>\n\n")
        return result

    @staticmethod
    def analyze_user_intent(input: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析用户问题意图。
        """
        logger.info("Analyzing user intent beginning>>>>>>>>>>>>>>>>>>>>>>>>")
        logger.info("analyze_user_intent input: %s", input)
        user_question = input.get("question", "")
        table_description = get_all_tables.invoke("")  # 假设已实现
        prompt = (
            f"请分析用户的自然语言问题，分析用户问题意图。问题如下：\n{user_question}\n\n"
            f"可用表信息：\n{table_description}\n\n"
            f"返回JSON：{{'intent': '意图', 'tables': ['表1', '表2']}}"
        )
        response = llm.invoke(prompt)
        result = parse_llm_response(response)
        result["original_input"] = user_question
        logger.info("Analyzed user intent: %s", result)
        logger.info("Analyzing user intent end>>>>>>>>>>>>>>>>>>>>>>>>\n\n")
        return result

    @staticmethod
    def generate_sql(input: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Generating SQL beginning>>>>>>>>>>>>>>>>>>>>>>>>")
        logger.info("generate_sql input: %s", input)
        intent, tables = input.get("intent", ""), input.get("tables", [])
        if not tables:
            return {"error": "未找到相关表"}
        table_info = get_table_info.invoke(",".join(tables))
        prompt = (f"您是旨在与TiDB（兼容 MySQL 5.7 的分布式数据库） 数据库交互的代理。给定一个输入问题，创建一个语法正确的 MySQL 查询。\n"
                  f"除非用户指定了他们希望获取的特定数量的示例，否则请始终将查询限制为最多 5 个结果。\n"
                  f"您可以按相关列对结果进行排序，以返回数据库中最相关示例。\n"
                  f"永远不要查询特定表中的所有列，只询问给定问题的相关列。不要对数据库进行任何 DML 语句（INSERT、UPDATE、DELETE、DROP 等）。\n"
                  f"如果问题似乎与数据库无关，只需返回 “I don't know” 作为答案。\n"
                  f"特别注意：对于涉及多个表的问题，请使用 JOIN 语句来连接相关表，并确保查询语句包含所有必要的表和字段。\n"
                  f"用户意图：{intent}\n"
                  f"可能相关的业务表信息如下：\n{table_info}\n\n"
                  f"请生成一个 SQL 查询，以回答用户的问题。"
                  f"返回JSON：{{'sql': 'SELECT * FROM table WHERE column = value'}}"
        )
        response = llm.invoke(prompt)
        logger.info("Generated SQL Response: %s", response)
        sql = parse_llm_response(response)
        user_question = input.get("original_input", "")
        # result = {"original_input": user_question, "intent": intent, "tables": tables,
        #           "table_info": table_info, "sql": sql}
        result = {"original_input": user_question,  "tables": tables,"sql": sql.get("sql", "")}
        logger.info("Generated SQL: %s", result)
        logger.info("Generating SQL end>>>>>>>>>>>>>>>>>>>>>>>>\n\n")
        return result

    @staticmethod
    def execute_sql(input: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Executing SQL beginning>>>>>>>>>>>>>>>>>>>>>>>>")
        logger.info("execute_sql input: %s", input)
        sql = input.get("sql", "")
        if not sql:
            return {"error": "无有效的SQL语句"}
        try:
            sql_results = query_database.invoke(sql)
            user_question = input.get("original_input", "")
            #intent = input.get("intent", "")
            #tables = input.get("tables", [])
            #table_info = input.get("table_info", {})
            # result={"original_input": user_question, "intent": intent, "tables": tables, "table_info": table_info,
            #         "sql": sql, "query_result": sql_results}
            result = {"original_input": user_question,"sql": sql, "query_result": sql_results}
            logger.info("SQL执行结果: %s", result)
            logger.info("Executing SQL end>>>>>>>>>>>>>>>>>>>>>>>>\n\n")
            return result
        except Exception as e:
            logger.error(f"SQL执行失败: {e}")
            return {"error": f"SQL执行失败: {e}"}

    @staticmethod
    def summarize_sql_result(input: Dict[str, Any]) -> str:
        logger.info("Summarizing SQL result beginning>>>>>>>>>>>>>>>>>>>>>>>>")
        logger.info("summarize_sql_result input: %s", input)
        query_result = input.get("query_result", "无数据")
        prompt = (
            f"您是一个代理，负责将数据库查询结果整理为易于查看的格式。\n\n"
            f"--------------------------------------------------------\n\n"
            f"数据库查询到以下数据符合用户预期：\n\n{query_result}\n\n"

        )
        summarize = llm.invoke(prompt).content
        user_question = input.get("original_input", "")
        #intent = input.get("intent", "")
        #tables = input.get("tables", [])
        #table_info = input.get("table_info", {})
        sql = input.get("sql", "")
        #sql_results = input.get("query_result", [])
        # result = {"original_input": user_question, "intent": intent, "tables": tables, "table_info": table_info,
        #           "sql": sql, "query_result": sql_results, "answer": summarize}
        result = {"original_input": user_question, "sql": sql, "answer": summarize}
        logger.info("Summarized SQL result: %s", result)
        logger.info("Summarizing SQL result end>>>>>>>>>>>>>>>>>>>>>>>>\n\n")
        return result


class Workflow:
    """工作流管理"""

    def __init__(self, agent_factory: AgentFactory):
        self.agent_factory = agent_factory

    def create_graph(self) -> Graph:
        """创建任务执行图"""
        graph = Graph()

        # 定义节点
        graph.add_node("start", lambda x: {"question": x["input"]})
        graph.add_node("find_similar", lambda x: {"result": self.agent_factory.find_similar_question(x)})
        graph.add_node("analyze_intent", lambda x: {"result": self.agent_factory.analyze_user_intent(x["result"])})
        graph.add_node("generate_sql", lambda x: {"result": self.agent_factory.generate_sql(x["result"])})
        graph.add_node("execute_sql", lambda x: {"result": self.agent_factory.execute_sql(x["result"])})
        graph.add_node("summarize", lambda x: {"result": self.agent_factory.summarize_sql_result(x["result"])})
        graph.add_node("end", lambda x: x["result"])

        # 定义条件边
        def route_after_similar(data: Dict[str, Any]) -> str:
            logger.info("Route after similar question: %s", data)
            result = data["result"]
            return "end" if result.get("answer") else "analyze_intent"

        # 添加边
        graph.add_edge("start", "find_similar")
        graph.add_conditional_edges("find_similar", route_after_similar,
                                    {"end": "end", "analyze_intent": "analyze_intent"})
        graph.add_edge("analyze_intent", "generate_sql")
        graph.add_edge("generate_sql", "execute_sql")
        graph.add_edge("execute_sql", "summarize")
        graph.add_edge("summarize", "end")

        graph.set_entry_point("start")
        graph.set_finish_point("end")
        return graph

    def execute(self, question: str) -> str:
        """执行自然语言查询"""
        try:
            workflow = self.create_graph().compile()
            result = workflow.invoke({"input": question})
            sql = result.get("sql", "")
            answer = result.get("answer", "")

            # 更新QA对
            if sql and answer and not result.get("error"):
                qa_manager.update(question, result["sql"], answer)

            return answer
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return "查询处理失败，请稍后再试"



class WorkflowState(TypedDict):
    input: str          # 初始用户问题
    question: str       # 来自起始节点的已处理问题
    result: Any         # 中间结果的灵活类型（例如，带有 'answer'、'sql' 等的 dict）
    answer: str         # 返回的最终答案
    error: bool

class WorkflowWithStateGraph:
    """使用 StateGraph 管理工作流"""

    def __init__(self, agent_factory: AgentFactory):
        self.agent_factory = agent_factory

    def create_state_graph(self) -> StateGraph:
        """创建带有 StateGraph 的工作流"""
        state_graph = StateGraph(state_schema=WorkflowState)

        # 在 StateGraph 中添加节点
        state_graph.add_node("start", lambda state: {"question": state["input"]})
        state_graph.add_node("find_similar", lambda state: {"result": self.agent_factory.find_similar_question(state)})
        state_graph.add_node("analyze_intent",
                             lambda state: {"result": self.agent_factory.analyze_user_intent(state["result"])})
        state_graph.add_node("generate_sql", lambda state: {"result": self.agent_factory.generate_sql(state["result"])})
        state_graph.add_node("execute_sql", lambda state: {"result": self.agent_factory.execute_sql(state["result"])})
        state_graph.add_node("summarize", lambda state: {"result": self.agent_factory.summarize_sql_result(state["result"])})
        state_graph.add_node("end", lambda state: state["result"])

        # 设置条件边
        def route_after_similar(state: WorkflowState) -> str:
            logger.info("Routing after similar question: %s", state)
            result = state["result"]
            return "end" if result.get("answer") else "analyze_intent"

        # 添加边并配置条件
        state_graph.add_edge("start", "find_similar")
        state_graph.add_conditional_edges("find_similar", route_after_similar,
                                          {"end": "end", "analyze_intent": "analyze_intent"})
        state_graph.add_edge("analyze_intent", "generate_sql")
        state_graph.add_edge("generate_sql", "execute_sql")
        state_graph.add_edge("execute_sql", "summarize")
        state_graph.add_edge("summarize", "end")

        # 设置起始和结束点
        state_graph.set_entry_point("start")
        state_graph.set_finish_point("end")
        return state_graph

    def execute(self, question: str) -> str:
        """执行工作流并使用 StateGraph"""
        try:
            state_graph = self.create_state_graph().compile()
            result = state_graph.invoke({"input": question})
            answer = result.get("answer", "")
            sql = result["result"].get("sql", "")

            # 更新QA对
            if sql and answer and not result.get("error"):
                qa_manager.update(question, sql, answer)

            return answer
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return "查询处理失败，请稍后再试"


def main():
    """主函数"""

    agent_factory = AgentFactory()
    workflow = Workflow(agent_factory)

    question = "帮我查下药物索托拉西布都有哪些别名？"
    result = workflow.execute(question)
    print(f"Input: {question}")
    print(f"Result: {result}")


def workflow_with_stategraph_main():
    """使用 StateGraph 管理工作流"""

    agent_factory = AgentFactory()
    workflow = WorkflowWithStateGraph(agent_factory)

    question = "帮我找三条药物通用名比较多的药物，返回药物ID及药物名称及通用名"
    result = workflow.execute(question)
    print(f"Input: {question}")
    print(f"Result: {result}")


if __name__ == "__main__":
    # main()
    workflow_with_stategraph_main()
