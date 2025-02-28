# -*- coding: utf-8 -*-
# @Time : 2025/2/18 下午12:36
# @Author : renjiajia

from typing import Any
class DatabaseError(Exception):
    """基础数据库异常"""
    def __init__(self, message: str, code: int = 500, original_error: Exception = None):
        super().__init__(message)
        self.code = code  # 错误类型码
        self.original_error = original_error  # 原始异常对象
        self.context = {}  # 额外上下文信息

    def add_context(self, key: str, value: Any) -> None:
        """添加上下文信息"""
        self.context[key] = value

class DatabaseConnectionError(DatabaseError):
    """数据库连接异常"""
    def __init__(self, message: str = "Database connection failed", original_error: Exception = None):
        super().__init__(message, code=1001, original_error=original_error)

class QueryExecutionError(DatabaseError):
    """查询执行异常"""
    def __init__(self, message: str = "Query execution failed", original_error: Exception = None):
        super().__init__(message, code=1002, original_error=original_error)

class QueryValidationError(DatabaseError):
    """查询验证异常"""
    def __init__(self, message: str = "Query validation failed", original_error: Exception = None):
        super().__init__(message, code=1003, original_error=original_error)