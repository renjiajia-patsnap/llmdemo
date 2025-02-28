# -*- coding: utf-8 -*-
# @Time : 2025/2/18 上午11:33
# @Author : renjiajia
from pydantic import BaseModel
from typing import Dict, List, Optional

class QueryPlan(BaseModel):
    explain_result: Dict
    execution_time: float
    indexes_used: List[str]

class IntentAnalysis(BaseModel):
    intent: str
    tables: List[str]
    confidence: float
    complexity: str = "simple"

class SQLResult(BaseModel):
    sql: str
    result: List[Dict]
    execution_time: float
    cache_hit: bool = False