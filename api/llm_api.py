# api/llm_api.py
from flask import Flask, request, jsonify
import logging
import os
import sys

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from llm.client import LLMClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(project_root, "logs", "llm_api.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    大模型对话接口

    请求体格式:
    {
        "model_type": "tongyi|deepseek|openai", // 必填
        "model_name": "qwen-plus|deepseek-chat|gpt-3.5-turbo", // 可选，不填则使用默认
        "message": "你好，请问有什么可以帮助你的？", // 必填
        "history": [  // 可选，对话历史
            {"role": "user", "content": "之前问题"},
            {"role": "assistant", "content": "之前回答"}
        ]
    }

    返回格式:
    {
        "code": 0,  // 0表示成功，非0表示失败
        "message": "success",  // 成功或错误信息
        "data": {
            "response": "大模型回复内容"
        }
    }
    """
    try:
        # 获取请求数据
        data = request.get_json()

        # 参数校验
        if not data:
            return jsonify({"code": 1, "message": "请求体不能为空", "data": None}), 400

        model_type = data.get('model_type')
        if not model_type:
            return jsonify({"code": 2, "message": "model_type 参数必填", "data": None}), 400

        message = data.get('message')
        if not message:
            return jsonify({"code": 3, "message": "message 参数必填", "data": None}), 400

        model_name = data.get('model_name')
        history = data.get('history', [])

        # 记录请求
        logger.info(f"收到对话请求: model_type={model_type}, model_name={model_name}")

        # 初始化LLM客户端
        try:
            llm_client = LLMClient(model_type=model_type, model_name=model_name)
            model = llm_client.get_model()
        except ValueError as e:
            return jsonify({"code": 4, "message": str(e), "data": None}), 400
        except Exception as e:
            logger.error(f"初始化LLM客户端失败: {str(e)}")
            return jsonify({"code": 5, "message": f"初始化LLM客户端失败: {str(e)}", "data": None}), 500

        # 构建对话消息
        messages = []
        for msg in history:
            role = msg.get('role')
            content = msg.get('content')
            if role and content:
                if role == 'user':
                    messages.append({"role": "user", "content": content})
                elif role == 'assistant':
                    messages.append({"role": "assistant", "content": content})

        # 添加当前用户消息
        messages.append({"role": "user", "content": message})

        # 调用LLM模型
        try:
            # 调用langchain的ChatOpenAI
            response = model.invoke(messages)
            response_content = response.content

            # 记录响应
            logger.info(f"模型响应成功: {response_content[:50]}...")

            return jsonify({
                "code": 0,
                "message": "success",
                "data": {
                    "response": response_content
                }
            })
        except Exception as e:
            logger.error(f"调用模型失败: {str(e)}")
            return jsonify({
                "code": 6,
                "message": f"调用模型失败: {str(e)}",
                "data": None
            }), 500

    except Exception as e:
        logger.error(f"处理请求失败: {str(e)}")
        return jsonify({
            "code": 99,
            "message": f"处理请求失败: {str(e)}",
            "data": None
        }), 500


@app.route('/api/models', methods=['GET'])
def get_models():
    """
    获取支持的模型列表

    返回格式:
    {
        "code": 0,
        "message": "success",
        "data": {
            "tongyi": ["qwen-plus", "qwen-max", "qwq-plus"],
            "deepseek": ["deepseek-chat", "deepseek-reasoner"],
            "openai": ["gpt-3.5-turbo", "gpt-4", "o3-mini"]
        }
    }
    """
    try:
        return jsonify({
            "code": 0,
            "message": "success",
            "data": LLMClient.MODEL_CONFIG
        })
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        return jsonify({
            "code": 99,
            "message": f"获取模型列表失败: {str(e)}",
            "data": None
        }), 500


def create_app():
    """创建应用实例，便于WSGI服务器调用"""
    return app


if __name__ == '__main__':
    # 确保日志目录存在
    log_dir = os.path.join(project_root, "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 启动应用
    app.run(host='0.0.0.0', port=5000, debug=False)
