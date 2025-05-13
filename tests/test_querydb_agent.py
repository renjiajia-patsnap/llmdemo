# -*- coding: utf-8 -*-
# @Time : 2025/2/21 下午2:25
# @Author : renjiajia
from agents.querydbagent import natural_language_query_database
from langchain.agents.agent import AgentAction


def test_natural_language_query_database_by_agent():
    query = "帮我找几条专利延长类型为PTE的专利，返回专利id及关联的药物ID"
    result = natural_language_query_database(query)
    # 提取问题和结果
    print(f"问题: {query}")
    print(f"结果: {result['output']}")
    for index,step in enumerate(result['intermediate_steps']):
        if isinstance(step[0], AgentAction):
            print(f"步骤{index}：{step[0].tool}")
