# -*- coding: utf-8 -*-
# @Time : 2025/2/21 下午2:25
# @Author : renjiajia
from agents.querydbagents import natural_language_query_with_task_planning
from agents.querydbagents import AIMessage


def test_natural_language_query_database_by_agents():
    #query = "帮我找几条专利延长类型为PTE的专利，返回专利id及关联的药物ID"
    query = "帮我找出生物类似药最多的原研药物，返回原研药物ID"
    result = natural_language_query_with_task_planning(query)

    if isinstance(result, AIMessage):
        message_content = result.content  # 提取 AI 消息的内容

    # 提取问题和结果
    print(f"问题: {query}")
    print(f"结果: {message_content}")

    # query = "帮我找出生物类似药最多的原研药物，返回原研药物ID"
    # 预期：68431d4745744d9e9e17a3073edd3920  68431d4745744d9e9e17a3073edd3920