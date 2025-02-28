# -*- coding: utf-8 -*-
# @Time : 2025/2/18 下午12:40
# @Author : renjiajia
import re
from typing import Tuple

class SQLValidator:
    def __init__(self):
        self.dml_keywords = r'\b(INSERT|UPDATE)\b'
    def validate(self, sql: str) -> Tuple[bool, str]:
        """全面SQL验证"""
        if self._detect_dml(sql):
            return False, "DML operations are not allowed"
        return True, "Validation passed"

    def sanitize_input(self, user_input: str) -> str:
        """输入净化处理"""
        return re.sub(r"[;'\"]", "", user_input).strip()

    def _detect_dml(self, sql: str) -> bool:
        return bool(re.search(self.dml_keywords, sql, re.IGNORECASE))
