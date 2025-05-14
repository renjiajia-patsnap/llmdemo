#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Git钩子测试脚本
用于测试Git提交分析功能，无需实际提交
"""

import os
import sys
import subprocess
from pathlib import Path

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

# 导入钩子模块
from utils.git_hooks import GitCommitAnalyzer

def create_sample_diff():
    """创建一个示例diff用于测试
    
    Returns:
        示例diff文本
    """
    return """diff --git a/example.py b/example.py
index 1234567..abcdefg 100644
--- a/example.py
+++ b/example.py
@@ -1,5 +1,7 @@
 # 这是一个示例文件
 
+import os
+
 def hello_world():
     print("Hello, World!")
+    print(f"当前工作目录: {os.getcwd()}")
 
-def add(a, b):
-    return a + b
+def add_numbers(a, b):
+    \"\"\"两数相加
+    
+    Args:
+        a: 第一个数
+        b: 第二个数
+        
+    Returns:
+        两数之和
+    \"\"\"
+    return a + b"""

def create_sample_commit_msg():
    """创建一个示例提交信息
    
    Returns:
        示例提交信息
    """
    return """改进hello_world函数并添加文档

1. 为hello_world函数添加显示当前目录功能
2. 为add函数添加文档注释
3. 将add函数重命名为更清晰的add_numbers"""

def mock_get_staged_diff(self):
    """模拟获取暂存区差异的方法
    
    Returns:
        示例diff文本
    """
    return create_sample_diff()

def mock_get_commit_message(self):
    """模拟获取提交信息的方法
    
    Returns:
        示例提交信息
    """
    return create_sample_commit_msg()

def mock_get_staged_files(self):
    """模拟获取暂存文件列表的方法
    
    Returns:
        示例文件列表
    """
    return ["example.py"]

def run_test():
    """运行测试函数"""
    print("=" * 50)
    print("Git钩子测试环境")
    print("=" * 50)
    print("\n模拟分析Git提交...")
    
    # 创建分析器实例
    analyzer = GitCommitAnalyzer()
    
    # 替换方法为模拟方法
    analyzer._get_staged_diff = mock_get_staged_diff.__get__(analyzer)
    analyzer._get_commit_message = mock_get_commit_message.__get__(analyzer)
    analyzer._get_staged_files = mock_get_staged_files.__get__(analyzer)
    
    # 运行分析
    result = analyzer.analyze()
    
    # 输出结果
    print("\n" + "=" * 50)
    print(f"分析结果: {'通过' if result else '未通过'}")
    print("=" * 50)
    
    # 检查日志文件是否已创建
    history_file = os.path.join(root_dir, "logs", "commit_analysis.json")
    if os.path.exists(history_file):
        print(f"\n✅ 分析历史已保存到: {history_file}")
    
    md_file = os.path.join(root_dir, "logs", "commit_analysis.md")
    if os.path.exists(md_file):
        print(f"✅ Markdown报告已生成: {md_file}")
    
    print("\n提示: 运行以下命令安装钩子:")
    print(f"python {os.path.join('utils', 'install_hooks.py')}")

if __name__ == "__main__":
    run_test() 