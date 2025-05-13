# -*- coding: utf-8 -*-
# @Time : 2025/3/5 下午1:27
# @Author : renjiajia
import requests
import json
from dotenv import load_dotenv
import os
from pathlib import Path
from typing import List

# 加载环境变量
load_dotenv()

# 获取环境变量
BASE_URL = os.getenv('minimax_base_url')+ "/image_generation"
API_KEY = os.getenv('minimax_api_key')

def create_image_generation(
        prompt: str,
        model: str = "image-01",
        aspect_ratio: str = "16:9",
        response_format: str = "url",
        n: int = 1,
        prompt_optimizer: bool = True
) -> dict:
    """
    生成图片

    :param prompt: 输入文本
    :param model: 模型名称
    :param aspect_ratio: 图像宽高比
    :param response_format: 返回格式
    :param n: 生成图片数量
    :param prompt_optimizer: 是否开启优化
    :return: 返回生成的图片信息字典
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "response_format": response_format,
        "n": n,
        "prompt_optimizer": prompt_optimizer
    }

    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(BASE_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # 检查请求是否成功
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"图片生成失败: {e}")
        return {}


def download_images(image_urls: List[str], save_dir: str) -> List[str]:
    """
    下载图片到指定目录

    :param image_urls: 图片URL列表
    :param save_dir: 保存目录路径
    :return: 保存的文件路径列表
    """
    # 确保目录存在
    Path(save_dir).mkdir(parents=True, exist_ok=True)

    saved_files = []

    for image_url in image_urls:
        try:
            response = requests.get(image_url)
            response.raise_for_status()

            # 从URL中提取文件名，如果没有则生成默认文件名
            image_name = image_url.split('?')[0].split('/')[-1]
            if not image_name:
                image_name = f"image_{len(saved_files)}.jpg"

            # 构造完整的保存路径
            save_path = os.path.join(save_dir, image_name)

            with open(save_path, 'wb') as file:
                file.write(response.content)
            saved_files.append(save_path)
            print(f"成功下载图片到: {save_path}")

        except requests.exceptions.RequestException as e:
            print(f"下载图片失败 {image_url}: {e}")

    return saved_files