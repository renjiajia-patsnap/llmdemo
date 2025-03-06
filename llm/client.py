# -*- coding: utf-8 -*-
# @Time : 2025/2/18 上午11:43
# @Author : renjiajia
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from typing import Optional
import os

load_dotenv()


class LLMClient:
    # 定义每个模型支持的配置
    MODEL_CONFIG = {
        "tongyi": {
            "base_url": os.getenv('tongyi_base_url'),
            "api_key": os.getenv('tongyi_api_key'),
            "supported_models": ["qwen-plus","qwen-max"],  # 通义千问支持的模型
        },
        "deepseek": {
            "base_url": os.getenv('deepseek_base_url'),
            "api_key": os.getenv('deepSeek_api_key'),
            # mode=deepseek-chat:DeepSeek-V3,model='deepseek-reasoner' DeepSeek-R1支持的模型
            "supported_models": ["deepseek-chat","deepseek-reasoner"],
        },
        "openai": {
            "base_url": os.getenv('openai_base_url'),
            "api_key": os.getenv('openai_api_key'),
            "supported_models": ["gpt-3.5-turbo", "gpt-4","o3-mini"],  # OpenAI 支持的模型
        },
    }

    def __init__(self, model_type: str, model_name: Optional[str] = None):
        """
        初始化 LLMdemo 实例。

        : param model_type: 模型类型，如 "tongyi", "deepSeek", "openai"
        : param model: 模型名称，如 "qwen-plus", "deepseek-chat", "gpt-3.5-turbo"
        """
        self.model_type = model_type
        self.model_name = model_name

        # 校验模型类型是否支持
        if self.model_type not in self.MODEL_CONFIG:
            raise ValueError(f"不支持的模型类型: {self.model_type}")

        # 如果传入了 model，校验是否是该模型支持的类型
        if self.model_name and self.model_name not in self.MODEL_CONFIG[self.model_type]["supported_models"]:
            raise ValueError(
                f"模型类型 {self.model_type} 不支持 {self.model_name}，支持的模型为: {self.MODEL_CONFIG[self.model_type]['supported_models']}"
            )

    def get_model(self) -> ChatOpenAI:
        """创建并返回 OpenAI 实例"""
        # 获取模型配置
        config = self.MODEL_CONFIG[self.model_type]

        # 如果未传入 model，使用默认模型
        if not self.model_name:
            self.model_name = config["supported_models"][0]  # 使用第一个支持的模型作为默认值

        # 直接定义 default_headers 为字典 ，如果是deepseek，则不需要headers
        if self.model_type == "deepseek":
            default_headers = {}
        else:
            default_headers = {
                "X-Ai-Engine": "openai",  # 自定义的 HTTP 头  openai
            }

        return ChatOpenAI(
            default_headers = default_headers,
            base_url = config["base_url"],
            api_key = config["api_key"],
            model = self.model_name,
        )

if __name__ == '__main__':
    # 创建一个 OpenAI 实例
    openai = LLMClient(model_type="openai", model_name="gpt-3.5-turbo").get_model()
    print(openai.get_response("你好"))


