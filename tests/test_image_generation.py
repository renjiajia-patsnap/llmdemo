# -*- coding: utf-8 -*-
# @Time : 2025/3/5 上午11:19
# @Author : renjiajia

import sys
sys.path.append("c:\\Users\\renjiajia\\PycharmProjects\\llmdemo") 
from llm.image_generation import create_image_generation, download_images

def test_create_image_generation():
    # 配置参数
    save_directory = "data/images"  # 可自定义保存路径

    # 测试生成图片
    prompt = (
        "男士 穿着白色 T 恤，全身站立前视图图像：25， 户外， "
        "威尼斯海滩标志， 全身图像， 洛杉矶， 90 年代时尚摄影， "
        "纪实， 胶片颗粒， 写实"
    )

    response = create_image_generation(
        prompt=prompt,
        model="image-01",
        aspect_ratio="16:9",
        response_format="url",
        n=3,
        prompt_optimizer=True
    )

    # 检查响应并下载图片
    if response and 'data' in response and 'image_urls' in response['data']:
        image_urls = response['data']['image_urls']
        print("生成的图片URL:", image_urls)

        # 下载图片到指定目录
        saved_paths = download_images(image_urls, save_directory)
        print("所有图片保存路径:", saved_paths)
    else:
        print("未能获取图片URL")

