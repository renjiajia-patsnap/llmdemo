#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试用例生成器
从Figma读取设计稿，从Confluence读取需求文档，然后生成测试用例
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_case_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

class FigmaClient:
    """Figma API客户端，用于获取设计稿信息"""
    
    def __init__(self, personal_access_token: str):
        """
        初始化Figma客户端
        
        Args:
            personal_access_token: Figma个人访问令牌
        """
        self.personal_access_token = personal_access_token
        self.base_url = "https://api.figma.com/v1"
        self.headers = {
            "X-Figma-Token": personal_access_token
        }
    
    def get_file(self, file_key: str) -> Dict[str, Any]:
        """
        获取Figma文件信息
        
        Args:
            file_key: Figma文件的Key
            
        Returns:
            包含Figma文件信息的字典
        """
        url = f"{self.base_url}/files/{file_key}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            logger.error(f"获取Figma文件失败: {response.text}")
            response.raise_for_status()
        
        return response.json()
    
    def get_file_nodes(self, file_key: str, node_ids: List[str]) -> Dict[str, Any]:
        """
        获取Figma文件中特定节点的信息
        
        Args:
            file_key: Figma文件的Key
            node_ids: 要获取的节点ID列表
            
        Returns:
            包含节点信息的字典
        """
        url = f"{self.base_url}/files/{file_key}/nodes"
        params = {
            "ids": ",".join(node_ids)
        }
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code != 200:
            logger.error(f"获取Figma节点失败: {response.text}")
            response.raise_for_status()
        
        return response.json()
    
    def get_file_images(self, file_key: str, node_ids: List[str]) -> Dict[str, Any]:
        """
        获取Figma文件中特定节点的图片
        
        Args:
            file_key: Figma文件的Key
            node_ids: 要获取图片的节点ID列表
            
        Returns:
            包含图片URL的字典
        """
        url = f"{self.base_url}/images/{file_key}"
        params = {
            "ids": ",".join(node_ids),
            "format": "png"
        }
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code != 200:
            logger.error(f"获取Figma图片失败: {response.text}")
            response.raise_for_status()
        
        return response.json()


class ConfluenceClient:
    """Confluence API客户端，用于获取需求文档信息"""
    
    def __init__(self, base_url: str, username: str, api_token: str):
        """
        初始化Confluence客户端
        
        Args:
            base_url: Confluence实例的基础URL
            username: 用户名
            api_token: API令牌
        """
        self.base_url = base_url
        self.auth = (username, api_token)
        self.headers = {
            "Content-Type": "application/json"
        }
    
    def get_page_content(self, page_id: str) -> Dict[str, Any]:
        """
        获取Confluence页面内容
        
        Args:
            page_id: Confluence页面ID
            
        Returns:
            包含页面内容的字典
        """
        url = f"{self.base_url}/wiki/rest/api/content/{page_id}?expand=body.storage"
        response = requests.get(url, auth=self.auth, headers=self.headers)
        
        if response.status_code != 200:
            logger.error(f"获取Confluence页面失败: {response.text}")
            response.raise_for_status()
        
        return response.json()
    
    def search_content(self, space_key: str, title: str) -> Dict[str, Any]:
        """
        在Confluence中搜索内容
        
        Args:
            space_key: 空间键
            title: 标题关键词
            
        Returns:
            包含搜索结果的字典
        """
        url = f"{self.base_url}/wiki/rest/api/content"
        params = {
            "spaceKey": space_key,
            "title": title,
            "expand": "body.storage"
        }
        response = requests.get(url, auth=self.auth, headers=self.headers, params=params)
        
        if response.status_code != 200:
            logger.error(f"搜索Confluence内容失败: {response.text}")
            response.raise_for_status()
        
        return response.json()


class TestCaseGenerator:
    """测试用例生成器"""
    
    def __init__(self, figma_client: FigmaClient, confluence_client: ConfluenceClient):
        """
        初始化测试用例生成器
        
        Args:
            figma_client: Figma客户端
            confluence_client: Confluence客户端
        """
        self.figma_client = figma_client
        self.confluence_client = confluence_client
        
    def extract_requirements(self, confluence_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从Confluence内容中提取需求
        
        Args:
            confluence_content: Confluence页面内容
            
        Returns:
            需求列表
        """
        # 这里需要根据具体的Confluence页面结构进行解析
        # 下面是一个简单的示例，实际情况需要根据文档结构调整
        requirements = []
        
        try:
            body_content = confluence_content["body"]["storage"]["value"]
            # 这里应该有更复杂的HTML解析逻辑
            # 为简单起见，我们假设需求以特定格式存在
            
            # 这里只是示例，实际实现需要根据文档结构适当调整
            import re
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(body_content, 'html.parser')
            
            # 查找所有的需求项
            # 假设需求项是以特定标题格式存在的
            requirement_sections = soup.find_all(['h2', 'h3'])
            
            for section in requirement_sections:
                if '需求' in section.text or '功能' in section.text:
                    requirement = {
                        "title": section.text.strip(),
                        "description": "",
                        "acceptance_criteria": []
                    }
                    
                    # 获取描述内容（段落）
                    description_elem = section.find_next('p')
                    if description_elem:
                        requirement["description"] = description_elem.text.strip()
                    
                    # 获取验收标准（列表项）
                    criteria_list = section.find_next('ul')
                    if criteria_list:
                        for item in criteria_list.find_all('li'):
                            requirement["acceptance_criteria"].append(item.text.strip())
                    
                    requirements.append(requirement)
            
        except Exception as e:
            logger.error(f"解析Confluence内容失败: {str(e)}")
            
        return requirements
    
    def extract_ui_components(self, figma_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从Figma内容中提取UI组件
        
        Args:
            figma_content: Figma文件内容
            
        Returns:
            UI组件列表
        """
        ui_components = []
        
        try:
            # 递归函数来遍历Figma文档结构
            def traverse_node(node):
                components = []
                
                # 如果节点是UI组件（按钮、输入框等）
                if node.get("type") in ["COMPONENT", "INSTANCE", "FRAME"] and node.get("name"):
                    component = {
                        "id": node.get("id"),
                        "name": node.get("name"),
                        "type": node.get("type"),
                        "properties": {}
                    }
                    
                    # 提取属性
                    if "fills" in node:
                        component["properties"]["color"] = node["fills"]
                    
                    if "characters" in node:
                        component["properties"]["text"] = node["characters"]
                    
                    if "style" in node:
                        component["properties"]["style"] = node["style"]
                    
                    components.append(component)
                
                # 递归处理子节点
                if "children" in node:
                    for child in node["children"]:
                        components.extend(traverse_node(child))
                
                return components
            
            # 从文档根节点开始遍历
            document = figma_content.get("document", {})
            ui_components = traverse_node(document)
            
        except Exception as e:
            logger.error(f"解析Figma内容失败: {str(e)}")
            
        return ui_components
    
    def generate_test_cases(self, requirements: List[Dict[str, Any]], ui_components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据需求和UI组件生成测试用例
        
        Args:
            requirements: 需求列表
            ui_components: UI组件列表
            
        Returns:
            测试用例列表
        """
        test_cases = []
        
        # 为每个需求生成测试用例
        for req in requirements:
            # 基本信息测试用例
            test_case = {
                "title": f"验证{req['title']}",
                "description": f"测试{req['description']}的功能",
                "preconditions": "用户已登录系统",
                "steps": [],
                "expected_results": [],
                "priority": "高",
                "type": "功能测试"
            }
            
            # 根据验收标准添加测试步骤和预期结果
            for i, criteria in enumerate(req["acceptance_criteria"], 1):
                test_case["steps"].append(f"步骤 {i}: 验证{criteria}")
                test_case["expected_results"].append(f"结果符合要求: {criteria}")
            
            test_cases.append(test_case)
            
            # UI相关测试用例
            ui_test_case = {
                "title": f"{req['title']}的UI测试",
                "description": f"测试{req['title']}相关界面元素",
                "preconditions": "用户已登录系统并导航至相关页面",
                "steps": [],
                "expected_results": [],
                "priority": "中",
                "type": "UI测试"
            }
            
            # 查找与需求相关的UI组件
            related_components = []
            for component in ui_components:
                # 这里需要一个相关性判断逻辑，简单示例如下
                if any(keyword.lower() in component["name"].lower() for keyword in req["title"].lower().split()):
                    related_components.append(component)
            
            # 为相关UI组件添加测试步骤
            for i, component in enumerate(related_components, 1):
                ui_test_case["steps"].append(f"步骤 {i}: 检查{component['name']}的显示")
                ui_test_case["expected_results"].append(f"{component['name']}正确显示且符合设计规范")
            
            if related_components:
                test_cases.append(ui_test_case)
        
        return test_cases
    
    def save_test_cases(self, test_cases: List[Dict[str, Any]], output_file: str) -> None:
        """
        保存测试用例到文件
        
        Args:
            test_cases: 测试用例列表
            output_file: 输出文件路径
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(test_cases, f, ensure_ascii=False, indent=2)
            logger.info(f"测试用例已保存到: {output_file}")
        except Exception as e:
            logger.error(f"保存测试用例失败: {str(e)}")
    
    def generate(self, figma_file_key: str, confluence_page_id: str, output_file: str) -> None:
        """
        生成测试用例的主函数
        
        Args:
            figma_file_key: Figma文件Key
            confluence_page_id: Confluence页面ID
            output_file: 输出文件路径
        """
        try:
            # 获取Figma设计稿
            logger.info(f"正在获取Figma设计稿: {figma_file_key}")
            figma_content = self.figma_client.get_file(figma_file_key)
            
            # 获取Confluence需求文档
            logger.info(f"正在获取Confluence需求文档: {confluence_page_id}")
            confluence_content = self.confluence_client.get_page_content(confluence_page_id)
            
            # 提取需求
            logger.info("正在分析需求文档...")
            requirements = self.extract_requirements(confluence_content)
            logger.info(f"已提取 {len(requirements)} 条需求")
            
            # 提取UI组件
            logger.info("正在分析设计稿...")
            ui_components = self.extract_ui_components(figma_content)
            logger.info(f"已提取 {len(ui_components)} 个UI组件")
            
            # 生成测试用例
            logger.info("正在生成测试用例...")
            test_cases = self.generate_test_cases(requirements, ui_components)
            logger.info(f"已生成 {len(test_cases)} 个测试用例")
            
            # 保存测试用例
            self.save_test_cases(test_cases, output_file)
            
        except Exception as e:
            logger.error(f"生成测试用例失败: {str(e)}")
            raise


def main():
    """主函数"""
    # 从环境变量获取API凭证
    figma_token = os.getenv("FIGMA_TOKEN")
    confluence_url = os.getenv("CONFLUENCE_URL")
    confluence_username = os.getenv("CONFLUENCE_USERNAME")
    confluence_token = os.getenv("CONFLUENCE_TOKEN")
    
    if not all([figma_token, confluence_url, confluence_username, confluence_token]):
        logger.error("缺少必要的API凭证。请确保设置了所有必需的环境变量。")
        sys.exit(1)
    
    # 初始化客户端
    figma_client = FigmaClient(figma_token)
    confluence_client = ConfluenceClient(confluence_url, confluence_username, confluence_token)
    
    # 初始化测试用例生成器
    generator = TestCaseGenerator(figma_client, confluence_client)
    
    # 生成测试用例
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_cases_{timestamp}.json"
    
    # 这里需要用户提供实际的Figma文件Key和Confluence页面ID
    figma_file_key = input("请输入Figma文件Key: ")
    confluence_page_id = input("请输入Confluence页面ID: ")
    
    generator.generate(figma_file_key, confluence_page_id, output_file)


if __name__ == "__main__":
    main() 