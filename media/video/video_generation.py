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
BASE_URL = os.getenv('minimax_base_url')+ "/video_generation"
API_KEY = os.getenv('minimax_api_key')
output_file = "data/video" #请在此输入生成视频的保存路径


"""
视频生成，文档地址：https://platform.minimaxi.com/document/video_generation?key=66d1439376e52fcee2853049
"""

def create_video_generation(
        prompt: str,
        model: str = "T2V-01-Director"  # 调用的算法模型ID。可选项：T2V-01-DirectorI2V-01-DirectorS2V-01I2V-01-liveI2V-01T2V-01
) -> dict:

    payload = {
        "prompt": prompt,
        "model": model
    }

    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(BASE_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        task_id = response.json()['task_id']
        print("视频生成任务提交成功，任务ID：" + task_id)
        # 检查请求是否成功
        return task_id
    except requests.exceptions.RequestException as e:
        print(f"视频生成任务提交失败: {e}")
        return {}


def query_video_generation(task_id: str):
    url = os.getenv('minimax_base_url')+"/query/video_generation?task_id="+task_id
    headers = {
      'authorization': f'Bearer {API_KEY}'
    }
    response = requests.get(url, headers=headers)
    status = response.json()['status']
    if status == 'Preparing':
        print("...准备中...")
        return "", 'Preparing'
    elif status == 'Queueing':
        print("...队列中...")
        return "", 'Queueing'
    elif status == 'Processing':
        print("...生成中...")
        return "", 'Processing'
    elif status == 'Success':
        return response.json()['file_id'], "Finished"
    elif status == 'Fail':
        return "", "Fail"
    else:
        return "", "Unknown"


def fetch_video_result(file_id: str):
    print("---------------视频生成成功，下载中---------------")
    url = os.getenv('minimax_base_url')+"/files/retrieve?file_id="+file_id
    headers = {
        'authorization': f'Bearer {API_KEY}'
    }

    response = requests.request("GET", url, headers=headers)
    print(response.text)

    download_url = response.json()['file']['download_url']
    print("视频下载链接：" + download_url)
    with open("output.mp4", 'wb') as f:
        f.write(requests.get(download_url).content)
    print("已下载在："+output_file+'/'+"output.mp4")

if __name__ == '__main__':
    prompt = """
    "请为我编写一个视频脚本，介绍一位虚构人物的一生，名字叫李明，出生于1980年3月15日，逝世于2050年12月10日。脚本需要适合3分钟的视频，时长约400-500字，语言简洁生动，适合旁白配音。内容包括以下要点：
    早年生活：李明出生在中国南方一个小村庄，家庭贫困但充满爱，喜欢读书和探索自然。
    青年时期：20岁时搬到城市，学习工程技术，努力工作成为一名桥梁设计师。
    职业成就：在职业生涯中设计了一座著名的大桥，象征连接与希望，获得了国家奖项。
    个人生活：与大学恋人结婚，育有两个孩子，喜欢旅行和摄影。
    晚年与遗产：退休后致力于慈善，帮助贫困儿童教育，去世后被人们铭记为善良和有远见的人。
    请以叙述性语气编写，加入情感和画面感，例如描述他设计大桥时的专注，或晚年与孙子共赏夕阳的温馨场景。脚本应适合视频配音和视觉呈现，避免过于复杂的术语。"
    """
    task_id = create_video_generation(prompt)
    print("-----------------已提交视频生成任务-----------------")
    while True:
        time.sleep(10)
        file_id, status = query_video_generation(task_id)
        if file_id != "":
            fetch_video_result(file_id)
            print("---------------生成成功---------------")
            break
        elif status == "Fail" or status == "Unknown":
            print("---------------生成失败---------------")
            break