# -*- coding: utf-8 -*-
# @Time : 2025/3/5 下午1:31
# @Author : renjiajia
import requests
import json
from dotenv import load_dotenv
import os
import time



# 加载环境变量
load_dotenv()

# 获取环境变量
BASE_URL = os.getenv('minimax_base_url')+ "/text2voice"
API_KEY = os.getenv('minimax_api_key')
output_file = "data/video" #请在此输入生成视频的保存路径


"""
视频生成，文档地址：https://platform.minimaxi.com/document/video_generation?key=66d1439376e52fcee2853049
"""

def create_voice_generation(
        gender: str = "female",
        age: str = "old",
        voice_desc = ["Kind and friendly","Kind and amiable","Kind hearted","Calm tone"],
        text = '真正的危险不是计算机开始像人一样思考，而是人开始像计算机一样思考'

) -> dict:

    payload = {
        "gender": gender,
        "age": age,
        "voice_desc": voice_desc,
        "text": text
    }

    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(BASE_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        response1 = response.json()
        return response1
    except requests.exceptions.RequestException as e:
        print(f"视频生成任务提交失败: {e}")
        return {}


if __name__ == '__main__':
    response = create_voice_generation()