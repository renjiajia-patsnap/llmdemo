# -*- coding: utf-8 -*-
# @Time : 2025/4/30 15:31
# @Author : renjiajia
import os
import time
import requests
import logging
from dotenv import load_dotenv
from typing import Optional, List
import base64
# 加载环境变量
load_dotenv()
# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

current_dir = os.getcwd()
print(f"当前工作目录: {current_dir}")

# 设置 DashScope API Key
API_KEY = os.getenv("TONGYI_API_KEY")  # 请确保环境变量中设置了 DASHSCOPE_API_KEY
if not API_KEY:
    raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")

"""
https://bailian.console.aliyun.com/?tab=api#/api/?type=model&url=https%3A%2F%2Fhelp.aliyun.com%2Fdocument_detail%2F2862677.html
"""
def submit_image_generation_task(prompt:str,model:str = "wanx2.1-t2i-turbo",num:int = 2,size:str = "1024*1024",negative_prompt:str = "") -> str:
    """
    提交图像生成任务，返回任务 ID。
    """
    base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable"
    }
    if negative_prompt:
        input_dict = {"prompt": prompt,
                      "negative_prompt":negative_prompt}
    else:
        input_dict =  {
            "prompt": prompt
        }


    payload = {
        "model": model,
        "input":input_dict,
        "parameters": {
        "size": size,
        "n": num
        }
    }
    response = requests.post(url=base_url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    task_id = data["output"]["task_id"]
    logging.info(f"任务已提交，任务 ID：{task_id}")
    return task_id


def poll_task_status(task_id: str, interval: int = 20, timeout: int = 600) -> Optional[List[str]]:
    """
    轮询任务状态，直到任务完成或超时，返回结果中的图像 URL 列表。
    """
    base_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    elapsed_time = 0
    while elapsed_time < timeout:
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        status = data["output"]["task_status"]
        if status == "SUCCEEDED":
            logging.info("任务已完成。")
            results = data["output"].get("results", [])
            return [result["url"] for result in results if "url" in result]
        elif status in ["FAILED", "CANCELLED"]:
            logging.error(f"任务失败，状态：{status}")
            return None
        else:
            logging.info(f"当前任务状态：{status}，等待 {interval} 秒后继续检查...")
            time.sleep(interval)
            elapsed_time += interval
    logging.error("任务超时。")
    return None

def download_images(image_urls: List[str], save_dir: str = ".", prefix: str = "test_image") -> None:
    """
    下载图像并保存到指定目录。
    """
    for idx, url in enumerate(image_urls):
        try:
            response = requests.get(url)
            response.raise_for_status()
            filename = os.path.join(save_dir, f"{prefix}_{idx + 1}.jpg")
            with open(filename, "wb") as f:
                f.write(response.content)
            logging.info(f"图像已保存为 {filename}")
        except requests.RequestException as e:
            logging.error(f"下载图像失败：{e}")

def main(user_input):
    """
    主函数，执行图像生成流程。
    """
    try:
        save_dir = current_dir + "/image"
        task_id = submit_image_generation_task(prompt=user_input,num=5)
        image_urls = poll_task_status(task_id)
        if image_urls:
            download_images(image_urls=image_urls, save_dir=save_dir)
        else:
            logging.error("未获取到图像 URL。")
    except Exception as e:
        logging.error(f"程序执行过程中发生错误：{e}")


if __name__ == "__main__":
    user_input = "小河，小船，钓鱼翁，刚钓到一条大鱼，很开心，旁边握着一只小猫，卡通可爱风"
    main(user_input)