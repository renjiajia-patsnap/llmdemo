# -*- coding: utf-8 -*-
# @Time : 2025/2/28 下午3:21
# @Author : renjiajia
import os
import time
import json
import requests
import logging
from functools import wraps
from utils.ddtalk import send_alert
from dotenv import load_dotenv

load_dotenv()


# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

token = os.getenv('tmp_token')

# 全局请求头
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Authorization': f'Bearer {token}',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Origin': 'https://tmp.patsnap.info',
    'Referer': 'https://tmp.patsnap.info/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'x-use-cache': 'False',
}


# 缓存装饰器
def cache_decorator(cache_file, expire_days=365):
    """缓存函数结果到文件，避免重复请求"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            refresh = kwargs.get('refresh', False)
            if os.path.exists(cache_file) and not refresh:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if time.time() - data.get('update_time', 0) < expire_days * 24 * 3600:
                        return data
            result = func(*args, **kwargs)
            result['update_time'] = time.time()
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f)
            return result
        return wrapper
    return decorator


@cache_decorator('data/product_nodes.json')
def get_product_node(product_id, refresh=False):
    """获取产品节点树"""
    url = 'https://tmp-backend.patsnap.info/test_management_platform/1.0/dict/tree/search'
    data = {"root_id": [product_id]}
    response = requests.post(url, headers=HEADERS, json=data).json()
    product_node = {'update_time': time.time()}
    nodes = response[0]['children']
    for node in nodes:
        product_node[node['dict_name']] = node
    return product_node


def get_product_modules(product_name, refresh=False):
    """获取产品模块信息"""
    product_id = get_product_id(product_name, refresh=refresh)
    product_nodes = get_product_node(product_id, refresh=refresh)
    product_modules = {
        key: product_nodes[key]['dict_id']
        for key in product_nodes.keys()
        if key != 'update_time'
    }
    return product_modules


@cache_decorator('data/product_dict.json')
def get_product_dict(refresh=False):
    """获取产品字典"""
    url = 'https://tmp-backend.patsnap.info/test_management_platform/1.0/dict/search'
    data = {"dict_type": "PRODUCT", "limit": 100, "offset": 0}
    response = requests.post(url, headers=HEADERS, json=data).json()
    product_dict = {'update_time': time.time()}
    for item in response['items']:
        product_dict[item['short_name']] = item
    return product_dict


def get_product_cases(product_id, module_id, priority, verification_method=None, case_type=None):
    """获取产品用例"""
    if not isinstance(product_id, str) or not isinstance(module_id, str):
        raise ValueError("product_id 和 module_id 必须是字符串")
    if priority not in [1, 2, 3]:
        raise ValueError("priority 必须是 1、2 或 3")
    url = 'https://tmp-backend.patsnap.info/test_management_platform/1.0/case/search'
    data = {
        "case_name": "",
        "product": [product_id],
        "verification_method": verification_method,
        "case_type": case_type,
        "module": [module_id],
        "priority": [priority],
        "updated_by": "",
        "created_by": "",
        "offset": 0,
        "limit": 10000,
        "sort_fields": [
            {"field": "created_at", "type": "DESC"},
            {"field": "case_id", "type": "ASC"}
        ]
    }
    response = requests.post(url, headers=HEADERS, json=data).json()
    return response['items']


def get_cases_by_product(product_name, module_name, module_id, priority):
    """根据产品名称获取用例并统计"""
    product_id = get_product_id(product_name)
    all_cases = get_product_cases(product_id, module_id, priority)
    all_case, publish_case, notautomatedcase = count_cases(all_cases)
    #print(f"产品：{product_name}\n模块：{module_name}\nP{priority}用例总数：{all_case}，未自动化用例数：{notautomatedcase}，发布相关用例数：{publish_case}\n\n")
    return {
        'product': product_name,
        'module': module_name,
        'p1case': all_case,
        'publish_case': publish_case,
        'notautomatedcase': notautomatedcase
    }

def product_case_count(product_name):
    """统计产品所有模块的用例"""
    product_modules = get_product_modules(product_name)
    all_cases_count = []
    for module_name, module_id in product_modules.items():
        case_count = get_cases_by_product(product_name, module_name, module_id, 1)
        all_cases_count.append(case_count)
    return all_cases_count


def count_cases(all_cases):
    """统计用例数量"""
    all_case = len(all_cases)
    publish_case = sum(1 for case in all_cases if "发布" in case['case_name'])
    notautomatedcase = sum(1 for case in all_cases if not case.get('ci'))
    return all_case, publish_case, notautomatedcase


def get_product_id(product_name, refresh=False):
    """根据产品名称获取产品ID"""
    product_dict = get_product_dict(refresh=refresh)
    return product_dict.get(product_name, {}).get("dict_id")


if __name__ == '__main__':
    product_name = 'DMP'
    secret = os.getenv('dd_secret')
    webhook = os.getenv('dd_webhook')
    all_cases_count = product_case_count(product_name)
    # 将all_cases_count生成markdown表格
    with open('data/casecount.md', 'w', encoding='utf-8') as f:
        f.write('| 产品 | 模块 | P1用例 | 流程相关 | 未自动化用例 |\n')
        f.write('| --- | --- | --- | --- | --- |\n')
        for case_count in all_cases_count:
            f.write(f"| {case_count['product']} | {case_count['module']} | {case_count['p1case']} | {case_count['publish_case']} | {case_count['notautomatedcase']} |\n")

    # 从'data/casecount.md'文件中读取内容发送到钉钉
    with open('data/casecount.md', 'r', encoding='utf-8') as f:
        content = f.read()
    # 发送到钉钉
    send_alert(secret, webhook, content)
    # print(all_cases_count)