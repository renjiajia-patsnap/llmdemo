from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.agents.agent import RunnableAgent
from database.manager import DatabaseManager
from langchain.schema import AIMessage
from typing import Dict, Any, Optional
from langchain.schema import Document
from utils.cache import CacheManager
from llm.client import LLMClient
from langchain.tools import tool
from utils.logger import logger
import pandas as pd
import json
import re
import os




# Initialize Data Cache and LLM
databasemanager = DatabaseManager()
data_cache = CacheManager()

# 加载 OpenAI 的嵌入模型
embeddings = OpenAIEmbeddings()
llm = LLMClient("openai",'o3-mini').get_model()

#llm = LLMClient("tongyi").get_model()


# 定义一个从excel中读取问题，sql和答案的函数，问答对第一列为序号，第二列为问题，第三列为sql，第四列为答案
def read_qa_pairs_from_excel(file_path ='data/qa_pairs.xlsx') -> Dict[str, Dict[str, str]]:
    """Read QA pairs from an Excel file and return as a dictionary."""
    try:
        if not os.path.exists(file_path):
            return {}  # 文件不存在则返回空字典
        df = pd.read_excel(file_path)
        if df.empty:
            return {}  # 处理空文件情况
        qa_pairs = df.set_index("question").to_dict(orient="index")
        return qa_pairs
    except Exception as e:
        logger.error(f"Failed to read QA pairs from Excel: {e}")
        return {}


# 定义一个添加问题，sql和答案到excel的函数第二列为问题，第三列为sql，第四列为答案
def update_qa_pairs(question: str, sql: str, answer: str,file_path ='data/qa_pairs.xlsx') -> None:
    """
    Add a QA pair to an Excel file. The first column is the question, the third column is SQL,
    and the fourth column is the answer.
    """
    try:
        # 读取原始数据（如果文件不存在或为空，创建空 DataFrame）
        if os.path.exists(file_path):
            df = pd.read_excel(file_path)
        else:
            df = pd.DataFrame(columns=["question", "sql", "answer"])

        # 追加新数据,如果question已经存在，则更新sql和answer
        if question in df["question"].values:
            df.loc[df["question"] == question, ["sql", "answer"]] = sql, answer
        else:
            new_row = pd.DataFrame({"question": [question], "sql": [sql], "answer": [answer]})
            df = pd.concat([df, new_row], ignore_index=True)

        # 写回 Excel 文件
        df.to_excel(file_path, index=False)
        logger.info("Updated QA pairs with question: %s", question)
    except Exception as e:
        logger.error(f"Failed to add QA pair to Excel: {e}")


def parse_llm_response(response: Any) -> Dict[str, Any]:
    """Parse the LLM response into a dictionary."""
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
        .replace("“", '"')  # 替换中文引号
        .replace("”", '"')
    )

    try:
        return json.loads(response_content)
    except json.JSONDecodeError as e:
        logger.info(f"JSON解析失败: {e}")
        logger.info(f"原始内容: {response_content}")
        return {"error": "无法解析LLM响应"}


# Agent 1: 查找相似问题代理
def create_find_similar_question_agent() -> RunnableAgent:
    """Create an agent to find a similar question in the QA file."""
    @tool
    def find_similar_question(input: str) -> Optional[Dict[str, Any]]:
        """Find a similar question in the QA file based on the input."""
        # 读取问答对
        qa = read_qa_pairs_from_excel()

        # 构造 FAISS 数据库
        docs = [Document(page_content=q, metadata={"sql": sql_info["sql"], "answer": sql_info.get("answer", "")}) for
                q, sql_info in qa.items()]
        vector_store = FAISS.from_documents(docs, embeddings)

        results = vector_store.similarity_search_with_score(input, k=1)  # 取最相似的 1 个
        similarity = 1 - results[0][1] if results else 0.0
        if results and similarity > 0.90:  # 设置相似度阈值为0.9
            logger.info(f"Found most similar question with score {results[0][1]}")
            return {
                "sql": results[0][0].metadata['sql'],
                "answer": results[0][0].metadata.get('answer', '')
            }
        return None

    return RunnableAgent(runnable=find_similar_question)


# Agent 2: 分析用户意图代理
def create_analyze_user_intent_agent() -> RunnableAgent:
    """Create an agent to analyze user intent and return possible related tables."""

    @tool
    def analyze_user_intent(input: str) -> Dict[str, Any]:
        """Analyze the user's natural language query and determine the intent."""
        table_description = get_all_tables.invoke("")
        prompt = (
            f"请分析用户的自然语言问题，并确定其意图及相关的业务表。问题如下：\n{input}\n\n"
            f"可用的表信息：\n{table_description}\n\n"
            f"请以JSON格式返回结果，包括：\n"
            f"1. 用户意图（intent）\n"
            f"2. 相关的业务表（tables）\n"
            f"示例输出：\n"
            f"{'{'}'intent': '用户意图', 'tables': ['表1', '表2', ...]{'}'}"
        )
        intent_analysis = llm.invoke(prompt)
        logger.info("Analyzed User Intent: %s", intent_analysis)
        return parse_llm_response(intent_analysis)

    return RunnableAgent(runnable=analyze_user_intent)


# Agent 3: SQL 生成与执行代理
def create_generate_sql_agent() -> RunnableAgent:
    """Create an agent to generate SQL based on user intent."""

    @tool
    def generate_and_execute_sql(input: Dict[str, Any]) -> Dict[str, Any]:
        """Generate and execute SQL based on the user's intent and related tables."""
        intent = input.get("intent", {})
        logger.info("User Intent: %s", intent)
        related_tables = input.get("tables", [])
        logger.info("Related Tables: %s", related_tables)

        if not related_tables:
            return {"error": "No related tables found in the intent analysis."}

        table_info = get_table_info.invoke(",".join(related_tables))
        prompt = (f"您是旨在与TiDB（兼容 MySQL 5.7 的分布式数据库） 数据库交互的代理。给定一个输入问题，创建一个语法正确的 MySQL 查询。\n"
                  f"除非用户指定了他们希望获取的特定数量的示例，否则请始终将查询限制为最多 5 个结果。\n"
                  f"您可以按相关列对结果进行排序，以返回数据库中最相关示例。\n"
                  f"永远不要查询特定表中的所有列，只询问给定问题的相关列。不要对数据库进行任何 DML 语句（INSERT、UPDATE、DELETE、DROP 等）。\n"
                  f"如果问题似乎与数据库无关，只需返回 “I don't know” 作为答案。\n"
                  f"特别注意：对于涉及多个表的问题，请使用 JOIN 语句来连接相关表，并确保查询语句包含所有必要的表和字段。\n"
                  f"用户意图：{intent}\n"
                  f"涉及的业务表信息如下：\n{table_info}\n\n"
        )

        # 调用 LLM 生成 SQL
        sql_response = llm.invoke(prompt)
        logger.info("Generated SQL Response: %s", sql_response)

        # 从 AIMessage 对象中提取 SQL 字符串
        if isinstance(sql_response, AIMessage):
            sql_content = sql_response.content
            # 如果sql_content 包含多个sql语句，只取最后一个，如果sql_content只有一个sql语句，直接取
            sql_content = sql_content.replace('\n', ' ').replace('\r', ' ')

            sql_pattern =  r"(SELECT.*?)(?:;|$)"
            matches = re.findall(sql_pattern, sql_content, re.DOTALL)
            # 只取最后一个 SQL 语句
            if matches:
                sql = matches[-1].strip()  # 去除前后的空格
            else:
                sql = ""

        else:
            sql = str(sql_response.content)

        logger.info("Generated SQL: %s", sql)

        # # 调用 query_database 执行 SQL
        # query_result = query_database.invoke(sql)
        # return {"sql": sql, "query_result": query_result}
        return {"sql": sql}

    return RunnableAgent(runnable=generate_and_execute_sql)


# Agent 4: 执行SQL代理
def create_execute_sql_agent() -> RunnableAgent:
    """Create an agent to execute SQL based on user intent."""

    @tool
    def execute_sql(input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SQL based on the user's intent and related tables."""
        sql = input.get("sql")
        query_result = query_database.invoke(sql)
        return {"sql": sql, "query_result": query_result}

    return RunnableAgent(runnable=execute_sql)


# Agent 5: 结果总结代理
def create_summarize_sql_result_agent() -> RunnableAgent:
    """Create an agent to summarize the SQL query result using LLM."""

    @tool
    def summarize_sql_result(input: Dict[str, Any]) -> str:
        """Summarize the SQL query result using LLM."""
        query_result = input.get("query_result")
        #message = input.get("message", "未提供用户问题")
        prompt = (
            f"您是一个代理，负责将数据库查询结果整理为易于查看的格式。\n\n"
            f"--------------------------------------------------------\n\n"
            f"数据库查询到以下数据符合用户预期：\n\n{query_result}\n\n"

        )
        summary = llm.invoke(prompt)
        logger.info("Summarized Result: %s", summary)
        return summary

    return RunnableAgent(runnable=summarize_sql_result)


# Agent 6: 任务规划代理
def create_task_planning_agent() -> RunnableAgent:
    """Create an agent to plan tasks and decide the execution order of agents."""

    @tool
    def plan_task(input: str) -> Dict[str, Any]:
        """
        Analyze the user's query and determine the necessary agents to invoke
        along with their execution order.
        """
        prompt = (
            f"用户问题：{input}\n\n"
            "请分析问题并确定需要执行的代理及其调用顺序。\n"
            "可选的代理包括：\n"
            "1. find_similar_question_agent - 查找相似问题代理\n"
            "2. analyze_user_intent_agent - 分析用户意图代理\n"
            "3. generate_sql_agent - SQL生成代理\n" 
            "4. execute_sql_agent - SQL执行代理\n"
            "5. summarize_sql_result_agent - 结果总结代理\n\n"
            "请严格按照以下JSON格式输出，不要包含任何其他内容：\n"
            '{"agents": [{"name": "agent_name", "description": "任务描述"}, ...]}'
        )
        plan = llm.invoke(prompt)
        print("Task Plan: %s", plan)
        return parse_llm_response(plan)

    return RunnableAgent(runnable=plan_task)


# Supporting Tools
@tool
def get_all_tables(input: str = "") -> Dict[str, Any]:
    """Retrieve all tables and their descriptions from the database."""
    if data_cache.exists("all_tables"):
        all_tables = data_cache.get("all_tables")
    else:
        all_tables = databasemanager.get_all_tables()
        data_cache.set("all_tables", all_tables)
    logger.info("Retrieved all available tables: %s", all_tables)
    return all_tables


@tool
def get_table_info(table_names: str) -> Dict[str, Any]:
    """Retrieve the schema and sample data for specified MySQL tables."""
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


def natural_language_query_with_task_planning(message: str) -> Any:
    """Query the database using natural language with a task planning agent."""

    try:
        # 首先尝试查找相似问题
        find_agent = create_find_similar_question_agent()
        similar_result = find_agent.runnable.invoke({"input": message})

        # 如果找到相似问题且相似度足够高
        if similar_result and similar_result.get("sql"):
            logger.info("Found similar question with high confidence. Re-executing SQL and summarizing.")

            # 执行SQL查询
            sql_agent = create_execute_sql_agent()
            sql_result = sql_agent.runnable.invoke({
                "input": {
                    "sql": similar_result["sql"],
                    "message": message
                }
            })

            # 使用总结代理处理结果
            if sql_result and "query_result" in sql_result:
                summarize_agent = create_summarize_sql_result_agent()
                final_answer = summarize_agent.runnable.invoke({
                    "input": {
                        "query_result": sql_result["query_result"],
                        "message": message
                    }
                })
                return final_answer
            else:
                logger.error("Failed to execute SQL from similar question")
                return "查询执行失败，请稍后再试"

        # 如果没有找到相似问题或相似度不够，继续执行任务规划
        task_planning_agent = create_task_planning_agent()
        task_plan = task_planning_agent.runnable.invoke({"input": message})

        # 如果解析失败，使用默认任务流
        if "error" in task_plan:
            print("任务规划失败，使用默认流程")
            task_plan = {
                "agents": [
                    {"name": "find_similar_question_agent"},
                    {"name": "analyze_user_intent_agent"},
                    {"name": "generate_and_execute_sql_agent"},
                    {"name": "summarize_sql_result_agent"}
                ]
            }

        execution_flow = task_plan.get("agents", [])
        context = {}
        for step in execution_flow:
            agent_name = step.get("name")
            print("Executing %s...", agent_name)
            if agent_name == "find_similar_question_agent":
                agent = create_find_similar_question_agent()
                context["similar_question"] = agent.runnable.invoke({"input": message})
                if context["similar_question"]:
                    logger.info("Found similar question. Reusing existing SQL.")
                    sql = context["similar_question"]["sql"]
                    query_result = query_database.invoke(sql)
                    summary_agent = create_summarize_sql_result_agent()
                    context["final_answer"] = summary_agent.runnable.invoke({
                        "input": {
                            "query_result": query_result,
                            "message": message
                        }
                    })
                    if isinstance(context["final_answer"], AIMessage):
                        answer = context["final_answer"].content
                    else:
                        answer = context["final_answer"]
                    update_qa_pairs(message, sql, answer)
                    return context["final_answer"]
            elif agent_name == "analyze_user_intent_agent":
                agent = create_analyze_user_intent_agent()
                context["intent_analysis"] = agent.runnable.invoke({"input": message})
            elif agent_name == "generate_sql_agent":
                agent = create_generate_sql_agent()
                agent_input = {"input": context.get("intent_analysis", {})}
                context["generated_sql"] = agent.runnable.invoke(agent_input)
            elif agent_name == "execute_sql_agent":
                agent = create_execute_sql_agent()
                agent_input = {"input": context.get("generated_sql", {})}
                context["sql_result"] = agent.runnable.invoke(agent_input)
            elif agent_name == "summarize_sql_result_agent":
                agent = create_summarize_sql_result_agent()
                sql_result = context.get("sql_result")
                if sql_result and "query_result" in sql_result:
                    agent_input = {
                        "input": {
                            "query_result": sql_result["query_result"],
                            "message": message
                        }
                    }
                    context["final_answer"] = agent.runnable.invoke(agent_input)
                else:
                    logger.info("SQL result is missing query_result. Skipping summarization.")
                    context["final_answer"] = "查询结果缺失，无法生成总结。"
    except Exception as e:
        logger.info(f"执行过程中发生错误: {str(e)}")
        return "抱歉，查询过程中出现错误，请稍后再试"

    final_answer = context.get("final_answer").content if isinstance(context.get("final_answer"), AIMessage) else context.get("final_answer")
    if "sql_result" in context:
        update_qa_pairs(message, context["sql_result"]["sql"], final_answer)
    return final_answer

if __name__ == "__main__":
    message = '帮我找几条最近更新的专利延长类型是PTE的数据，发挥专利ID，延长类型及关联药物ID'
    result = natural_language_query_with_task_planning(message)
    print("<------------------------------------------------------------------------------------------->\n\n")
    print("input: %s", message)
    print("Query Result: %s", result)

