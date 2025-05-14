#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Git钩子单元测试
用于测试Git提交分析功能
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest import mock

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

# 导入要测试的模块
from utils.git_hooks import GitCommitAnalyzer

# 创建示例数据
SAMPLE_DIFF = """diff --git a/example.py b/example.py
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

SAMPLE_COMMIT_MSG = """改进hello_world函数并添加文档

1. 为hello_world函数添加显示当前目录功能
2. 为add函数添加文档注释
3. 将add函数重命名为更清晰的add_numbers"""

SAMPLE_FILES = ["example.py"]

# 模拟AI分析结果
MOCK_ANALYSIS_RESULT = {
    "summary": "本次提交改进了代码质量和可读性",
    "quality": "良好",
    "issues": [],
    "suggestions": ["考虑增加更多函数文档注释"],
    "rating": 8,
    "analysis_level": "comprehensive"
}

class TestGitCommitAnalyzer:
    """Git提交分析器测试类"""
    
    @pytest.fixture
    def analyzer(self):
        """创建带有模拟方法的分析器实例"""
        with mock.patch('utils.git_hooks.GitCommitAnalyzer._get_git_root', return_value=root_dir):
            analyzer = GitCommitAnalyzer()
            # 替换方法为模拟方法
            analyzer._get_staged_diff = mock.MagicMock(return_value=SAMPLE_DIFF)
            analyzer._get_commit_message = mock.MagicMock(return_value=SAMPLE_COMMIT_MSG)
            analyzer._get_staged_files = mock.MagicMock(return_value=SAMPLE_FILES)
            analyzer._analyze_with_ai = mock.MagicMock(return_value=MOCK_ANALYSIS_RESULT)
            yield analyzer
    
    def test_initialization(self, analyzer):
        """测试分析器初始化"""
        assert analyzer is not None
        assert analyzer.root_dir == root_dir
        assert analyzer.enabled is True
    
    def test_analyze_success(self, analyzer):
        """测试分析成功的情况"""
        result = analyzer.analyze()
        assert result is True
        analyzer._get_commit_message.assert_called_once()
        analyzer._get_staged_files.assert_called_once()
        analyzer._get_staged_diff.assert_called_once()
        analyzer._analyze_with_ai.assert_called_once()
    
    def test_critical_files_detection(self, analyzer):
        """测试关键文件检测"""
        # 添加测试用的关键文件模式
        analyzer.critical_file_patterns = [".*password.*", ".*secret.*"]
        analyzer.ignored_file_patterns = [".*\\.md$"]
        
        # 模拟存在关键文件
        analyzer._get_staged_files = mock.MagicMock(return_value=["config/password.py", "README.md", "secret_key.txt"])
        
        # 运行分析
        result = analyzer.analyze()
        
        # 验证结果
        assert result is True  # 默认不阻止提交
        
        # 设置阻止提交
        analyzer.block_on_critical = True
        result = analyzer.analyze()
        assert result is False  # 应该阻止提交
    
    def test_short_commit_message(self, analyzer):
        """测试提交信息过短的情况"""
        # 设置最小提交信息长度
        analyzer.config["analysis"] = {"min_commit_message_length": 20}
        
        # 模拟短提交信息
        analyzer._get_commit_message = mock.MagicMock(return_value="短信息")
        
        # 运行分析
        result = analyzer.analyze()
        
        # 验证结果
        assert result is False  # 应该阻止提交
    
    def test_empty_staged_files(self, analyzer):
        """测试暂存文件为空的情况"""
        # 模拟空暂存文件列表
        analyzer._get_staged_files = mock.MagicMock(return_value=[])
        
        # 运行分析
        result = analyzer.analyze()
        
        # 验证结果
        assert result is False  # 应该阻止提交
    
    def test_empty_diff(self, analyzer):
        """测试空差异的情况"""
        # 模拟空差异
        analyzer._get_staged_diff = mock.MagicMock(return_value="")
        
        # 运行分析
        result = analyzer.analyze()
        
        # 验证结果
        assert result is False  # 应该阻止提交
    
    def test_low_rating_with_block(self, analyzer):
        """测试低评分阻止提交的情况"""
        # 设置阻止提交
        analyzer.block_on_critical = True
        
        # 模拟低评分
        mock_result = MOCK_ANALYSIS_RESULT.copy()
        mock_result["rating"] = 2
        analyzer._analyze_with_ai = mock.MagicMock(return_value=mock_result)
        
        # 运行分析
        result = analyzer.analyze()
        
        # 验证结果
        assert result is False  # 应该阻止提交
    
    def test_low_rating_without_block(self, analyzer):
        """测试低评分不阻止提交的情况"""
        # 设置不阻止提交
        analyzer.block_on_critical = False
        
        # 模拟低评分
        mock_result = MOCK_ANALYSIS_RESULT.copy()
        mock_result["rating"] = 2
        analyzer._analyze_with_ai = mock.MagicMock(return_value=mock_result)
        
        # 运行分析
        result = analyzer.analyze()
        
        # 验证结果
        assert result is True  # 不应该阻止提交
    
    def test_combined_suggestions_display(self, analyzer, capsys):
        """测试合并建议显示"""
        # 设置多条建议
        mock_result = MOCK_ANALYSIS_RESULT.copy()
        mock_result["suggestions"] = [
            "考虑增加更多函数文档注释", 
            "使用类型提示", 
            "添加单元测试"
        ]
        analyzer._analyze_with_ai = mock.MagicMock(return_value=mock_result)
        
        # 运行分析
        analyzer.analyze()
        
        # 获取输出内容
        captured = capsys.readouterr()
        
        # 验证输出中包含合并的建议
        assert "考虑增加更多函数文档注释; 使用类型提示; 添加单元测试" in captured.out
    
    def test_save_history(self, analyzer, tmpdir):
        """测试保存历史记录"""
        # 设置临时历史文件路径
        history_dir = tmpdir.mkdir("logs")
        history_file = history_dir.join("test_history.json")
        md_file = history_dir.join("test_history.md")
        
        analyzer.history_file = str(history_file)
        analyzer.export_path = str(md_file)
        
        # 运行分析
        analyzer.analyze()
        
        # 验证历史文件是否创建
        assert os.path.exists(analyzer.history_file)
        
        # 验证历史文件内容
        with open(analyzer.history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
            assert len(history) == 1
            assert "timestamp" in history[0]
            assert "result" in history[0]
            assert history[0]["result"] == MOCK_ANALYSIS_RESULT
        
        # 验证Markdown文件是否创建
        assert os.path.exists(analyzer.export_path)
        
    def test_disabled_analysis(self, analyzer):
        """测试禁用分析的情况"""
        # 禁用分析
        analyzer.enabled = False
        
        # 运行分析
        result = analyzer.analyze()
        
        # 验证结果
        assert result is True  # 应该允许提交
        
        # 验证方法未被调用
        analyzer._get_commit_message.assert_not_called()
        analyzer._get_staged_files.assert_not_called()
        analyzer._get_staged_diff.assert_not_called()
        analyzer._analyze_with_ai.assert_not_called()


# 为向后兼容保留原始测试函数
def create_sample_diff():
    """创建一个示例diff用于测试
    
    Returns:
        示例diff文本
    """
    return SAMPLE_DIFF

def create_sample_commit_msg():
    """创建一个示例提交信息
    
    Returns:
        示例提交信息
    """
    return SAMPLE_COMMIT_MSG

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

def test_run():
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
    test_run()
