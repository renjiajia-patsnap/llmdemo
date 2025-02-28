# -*- coding: utf-8 -*-
# @Time : 2025/2/18 下午12:19
# @Author : renjiajia
import json
import re
from typing import Dict, Any


class ResponseParser:
    @staticmethod
    def parse_sql_response(response: str) -> Dict[str, Any]:
        try:
            # 尝试提取JSON格式
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            # 处理非标准格式
            return {
                "sql": ResponseParser._extract_sql(response),
                "explanation": ResponseParser._extract_explanation(response)
            }
        except json.JSONDecodeError:
            return {"error": "Invalid response format"}

    @staticmethod
    def _extract_sql(text: str) -> str:
        sql_match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL)
        return sql_match.group(1) if sql_match else ""

    @staticmethod
    def _extract_explanation(text: str) -> str:
        explanation_match = re.search(r"Explanation:\s*(.*)", text)
        return explanation_match.group(1) if explanation_match else ""