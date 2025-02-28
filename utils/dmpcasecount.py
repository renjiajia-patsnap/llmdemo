# -*- coding: utf-8 -*-
# @Time : 2025/2/28 上午10:17
# @Author : renjiajia
import time
import os
import requests
import json

def get_product_node(product_id,):
    url = 'https://tmp-backend.patsnap.info/test_management_platform/1.0/dict/tree/search'
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Authorization': 'Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJjZGRlYmJmNmY1ZjA5Y2EzYTk1YTdiYTViOWQzYWIyZCIsImF1dGhvcml0aWVzIjpbXSwiaXNzIjoidGVzdF9tYW5hZ2VfcGxhdGZvcm0iLCJpYXQiOjE3NDA0NTI4NjUsImV4cCI6MTc0MzA0NDg2NX0.hRRHSPx313P15DToZEGtTp6kafxaCgT3GXK8AKTL_jqK-Gy4XCVTHuitnLMTs68ApZjpS0N3FXv7J63TKcXnyg',
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

    data = {
        "root_id": [product_id]
    }
    product_node={}
    product_node['update_time'] = time.time()
    response = requests.post(url, headers=headers, json=data).json()
    nodes = response[0]['children']
    for node in nodes:
        product_node[node['dict_name']] = node
    # 将product_node{}写入文件
    with open('data/product_nodes.json', 'w') as f:
        json.dump(product_node, f)
    return product_node

def get_product_moudles(product_name, refresh=False):
    # 从data/product_node.json中读取product_node{}
    product_id = get_product_id(product_name)
    if not os.path.exists('data/product_nodes.json') or refresh:
        product_nodes = get_product_node(product_id)
    else:
        with open('data/product_nodes.json', 'r') as f:
            product_nodes = json.load(f)
            # 如果product_node 中 update_time 距离现在超过365天，或者refresh = True 则重新获取product_node
            if time.time() - product_nodes['update_time'] > 365 * 24 * 60 * 60:
                product_nodes = get_product_node(product_id)

    # 遍历product_node{}，获取模块名称和模块id
    product_moudles = {}
    for key in product_nodes.keys():
        if key != 'update_time':
            product_moudles[key] = product_nodes[key]['dict_id']
    return product_moudles


def get_product_dict():
    url = 'https://tmp-backend.patsnap.info/test_management_platform/1.0/dict/search'
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Authorization': 'Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJjZGRlYmJmNmY1ZjA5Y2EzYTk1YTdiYTViOWQzYWIyZCIsImF1dGhvcml0aWVzIjpbXSwiaXNzIjoidGVzdF9tYW5hZ2VfcGxhdGZvcm0iLCJpYXQiOjE3NDA0NTI4NjUsImV4cCI6MTc0MzA0NDg2NX0.hRRHSPx313P15DToZEGtTp6kafxaCgT3GXK8AKTL_jqK-Gy4XCVTHuitnLMTs68ApZjpS0N3FXv7J63TKcXnyg',
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

    data = {
        "dict_type": "PRODUCT",
        "limit": 100,
        "offset": 0
    }

    response = requests.post(url, headers=headers, json=data).json()
    product_dict={}
    product_dict['update_time'] = time.time()
    # 获取product_dict{}
    for item in response['items']:
        product_dict[item['short_name']] = item

    # 将product_dict{}写入文件
    with open('data/product_dict.json', 'w') as f:
        json.dump(product_dict, f)

    return product_dict


def get_product_cases(product_id,module_id,priority,verification_method = None ,case_type = None):
    """
    获取产品用例
    :param product_name: 产品名称 例如：DMP
    :param priority: 优先级 1-高 2-中 3-低
    :param module: 模块名称
    :param verification_method: INTERFACE_AUTOMATION-接口自动化 UI_AUTOMATION-UI自动化 MANUAL-手工
    :param case_type: FUNCTIONAL-功能测试 INTERFACE-接口测试 UI-界面测试
    :return:
    """

    url = 'https://tmp-backend.patsnap.info/test_management_platform/1.0/case/search'
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Authorization': 'Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJjZGRlYmJmNmY1ZjA5Y2EzYTk1YTdiYTViOWQzYWIyZCIsImF1dGhvcml0aWVzIjpbXSwiaXNzIjoidGVzdF9tYW5hZ2VfcGxhdGZvcm0iLCJpYXQiOjE3NDA0NTI4NjUsImV4cCI6MTc0MzA0NDg2NX0.hRRHSPx313P15DToZEGtTp6kafxaCgT3GXK8AKTL_jqK-Gy4XCVTHuitnLMTs68ApZjpS0N3FXv7J63TKcXnyg',
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

    response = requests.post(url, headers=headers, json=data).json()

    return response['items']


def get_cases_by_product(product_name,module_name,module_id,priority):
    product_id = get_product_id(product_name)
    all_cases = get_product_cases(product_id,module_id,priority)
    all_case, publish_case, notautomatedcase = count_cases(all_cases)
    print(f"\n\n产品：{product_name}\n模块:{module_name}\nP1用例总数：{all_case}，未自动化用例数：{notautomatedcase}，发布相关用例数：{publish_case}")
    return {
        'product':product_name,
        'model':module_name,
        'publish_case':publish_case,
        'notautomatedcase':notautomatedcase
    }

def product_case_count(product_name):
    product_moudles = get_product_moudles(product_name)
    all_cases_count = []
    for module_name,module_id in product_moudles.items():
        case_count = get_cases_by_product(product_name,module_name,module_id,1)
        all_cases_count.append(case_count)
    return all_cases_count


def count_cases(all_cases):
    all_case = len(all_cases)
    publish_case = 0
    notautomatedcase = 0
    for case in all_cases:
        if "发布" in case['case_name'] :
            publish_case += 1
        # 如果用例没有ci字段，说明未自动化
        if not case.get('ci',None):
            notautomatedcase += 1
    return all_case,publish_case,notautomatedcase

def get_product_id(product_name,refresh=False):
    # 判断data/product_dict.json是否存在，如果不存在则调用get_product_dict()获取product_dict{}
    if not os.path.exists('data/product_dict.json') or refresh:
        product_dict = get_product_dict()
    else:
        with open('data/product_dict.json', 'r') as f:
            product_dict = json.load(f)
            # 如果product_dict 中 update_time 距离现在超过365天，或者refresh = True 则重新获取product_dict
            if time.time() - product_dict['update_time'] > 365 * 24 * 60 * 60:
                product_dict = get_product_dict()

    return product_dict[product_name].get("dict_id",None)

if __name__ == '__main__':
    product_name = 'DMP'
    all_cases_count =product_case_count(product_name)
    print(all_cases_count)