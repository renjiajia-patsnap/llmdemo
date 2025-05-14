#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Git钩子工具模块
用于实现Git提交内容分析和检查的功能
"""

import os
import re
import sys
import json
import yaml
import subprocess
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import openai
from pathlib import Path
from colorama import Fore, Style, init
from dotenv import load_dotenv

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # 项目根目录
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入LLM客户端
from llm.client import LLMClient

load_dotenv()
# 初始化colorama，设置strip=False以防止表情符号输出问题
init(strip=False)
# 解决Windows下的编码问题
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    # Windows环境下使用英文输出，避免中文编码问题
    USE_ENGLISH = True
else:
    USE_ENGLISH = False

# 中英文消息映射
MSG = {
    "git_analysis": "Git Commit Analysis" if USE_ENGLISH else "Git提交分析",
    "commit_analysis_disabled": "Commit analysis is disabled" if USE_ENGLISH else "提交分析功能已禁用",
    "commit_msg_short": "Commit message too short (min: {}, current: {})" if USE_ENGLISH else "提交信息过短（最小长度: {}，当前长度: {}）",
    "no_staged_files": "No staged files" if USE_ENGLISH else "没有暂存的文件",
    "sensitive_files": "Detected sensitive files" if USE_ENGLISH else "检测到可能的敏感文件",
    "no_diff": "Failed to get staged diff" if USE_ENGLISH else "无法获取暂存区差异",
    "analyzing": "Analyzing commit..." if USE_ENGLISH else "正在分析提交内容...",
    "analysis_result": "Analysis Result" if USE_ENGLISH else "提交分析结果",
    "overview": "Overview" if USE_ENGLISH else "概述",
    "no_overview": "No overview" if USE_ENGLISH else "无概述",
    "quality": "Quality" if USE_ENGLISH else "质量评估",
    "no_quality": "No quality assessment" if USE_ENGLISH else "无评估",
    "rating": "Rating" if USE_ENGLISH else "评分",
    "potential_issues": "Potential Issues" if USE_ENGLISH else "潜在问题",
    "no_issues": "No potential issues found" if USE_ENGLISH else "未发现潜在问题",
    "suggestions": "Suggestions" if USE_ENGLISH else "改进建议",
    "ai_response": "AI Raw Response" if USE_ENGLISH else "AI原始响应",
    "tips": "Note: This is an AI-assisted code analysis for reference only. Always perform manual review." if USE_ENGLISH else "提示: 这是由AI辅助的代码分析，仅供参考。请始终进行人工审查。",
    "block_sensitive": "Commit blocked due to sensitive files" if USE_ENGLISH else "由于存在敏感文件，提交被阻止",
    "block_low_rating": "Commit blocked due to low rating" if USE_ENGLISH else "由于评分过低，提交被阻止",
    "low_rating": "Commit rating is low, consider improvements" if USE_ENGLISH else "提交评分较低，请考虑改进"
}

class GitCommitAnalyzer:
    """Git提交分析器，用于检查和分析提交内容"""
    
    def __init__(self, config_path: str = None):
        """初始化Git提交分析器
        
        Args:
            config_path: 配置文件路径，默认为项目根目录下的config/git_hook_config.yaml
        """
        # 获取项目根目录
        self.root_dir = self._get_git_root()
        
        # 设置配置文件路径
        if not config_path:
            config_path = os.path.join(self.root_dir, "config", "git_hook_config.yaml")
        
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 设置API密钥
        self._setup_api_keys()
        
        # 检查是否启用分析
        self.enabled = self.config.get("analysis", {}).get("enabled", True)
        
        # 输出设置
        self.colorize = self.config.get("output", {}).get("colorize", True)
        self.use_emoji = self.config.get("output", {}).get("use_emoji", True)
        self.verbosity = self.config.get("output", {}).get("verbosity", "normal")
        self.show_tips = self.config.get("output", {}).get("show_tips", True)
        
        # 行为设置
        self.save_history = self.config.get("behavior", {}).get("save_history", True)
        self.block_on_critical = self.config.get("behavior", {}).get("block_on_critical", False)
        
        # 获取关键文件模式
        self.critical_file_patterns = self.config.get("behavior", {}).get("critical_file_patterns", [])
        self.ignored_file_patterns = self.config.get("behavior", {}).get("ignored_file_patterns", [])
        
        # 历史记录设置
        history_config = self.config.get("history", {})
        self.history_file = os.path.join(self.root_dir, history_config.get("file_path", "logs/commit_analysis.json"))
        self.export_path = os.path.join(self.root_dir, history_config.get("export_path", "logs/commit_analysis.md"))
        self.max_records = history_config.get("max_records", 100)
        
        # 创建日志目录（如果不存在）
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
    
    def _get_git_root(self) -> str:
        """获取Git项目根目录
        
        Returns:
            项目根目录路径
        """
        try:
            git_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], 
                                             stderr=subprocess.STDOUT, 
                                             universal_newlines=True).strip()
            return git_root
        except subprocess.CalledProcessError:
            # 回退到当前目录
            return os.getcwd()
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config or {}
        except Exception as e:
            self._print_error(f"加载配置文件失败: {str(e)}")
            # 返回默认配置
            return {
                "model": {"type": "openai", "name": "gpt-3.5-turbo", "timeout": 30},
                "analysis": {"enabled": True, "level": "basic", "include_rating": True, 
                             "max_diff_size": 50000, "min_commit_message_length": 10},
                "behavior": {"save_history": True, "block_on_critical": False},
                "output": {"colorize": True, "use_emoji": True, "verbosity": "normal", "show_tips": True},
                "history": {"file_path": "logs/commit_analysis.json", "export_path": "logs/commit_analysis.md", "max_records": 100}
            }
    
    def _setup_api_keys(self) -> None:
        """设置API密钥"""
        # 从环境变量中获取API密钥
        model_type = self.config.get("model", {}).get("type", "openai")
        
        if model_type == "openai":
            openai.api_key = os.environ.get("OPENAI_API_KEY")
        # 可以添加其他模型的API密钥设置
    
    def _get_commit_message(self) -> str:
        """获取当前提交信息
        
        Returns:
            提交信息
        """
        commit_msg_file = sys.argv[1] if len(sys.argv) > 1 else ".git/COMMIT_EDITMSG"
        
        # 尝试不同的编码读取提交信息
        encodings_to_try = ['utf-8', 'gbk', 'latin-1', 'utf-16', 'cp1252']
        commit_msg = ""
        
        for encoding in encodings_to_try:
            try:
                with open(commit_msg_file, 'r', encoding=encoding) as f:
                    commit_msg = f.read().strip()
                print(f"成功使用 {encoding} 编码读取提交信息")
                break
            except UnicodeDecodeError:
                print(f"尝试以 {encoding} 编码读取提交信息失败")
                continue
            except Exception as e:
                self._print_error(f"读取提交信息失败: {str(e)}")
                return ""
        
        # 如果是Windows环境，确保所有文本都是ASCII可表示的
        if sys.platform == 'win32':
            # 将非ASCII字符替换为英文描述
            try:
                temp_msg = commit_msg.encode('ascii', errors='xmlcharrefreplace').decode('ascii')
                print(f"原始信息长度: {len(commit_msg)}, 处理后长度: {len(temp_msg)}")
                commit_msg = temp_msg
            except Exception as e:
                print(f"处理提交信息时出错: {str(e)}")

        print(commit_msg)
        return commit_msg
    
    def _get_staged_diff(self) -> str:
        """获取暂存区的差异
        
        Returns:
            差异文本
        """
        try:
            # 尝试使用utf-8编码获取差异
            try:
                diff = subprocess.check_output(
                    ["git", "diff", "--staged", "--unified=3"],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    encoding='utf-8'
                )
                print("成功使用utf-8编码获取差异")
            except UnicodeDecodeError:
                # 如果utf-8失败，尝试使用二进制模式获取，然后使用多种编码尝试解码
                print("使用utf-8编码获取差异失败，尝试二进制模式")
                diff_binary = subprocess.check_output(
                    ["git", "diff", "--staged", "--unified=3"],
                    stderr=subprocess.STDOUT
                )
                
                # 尝试多种编码
                encodings_to_try = ['latin-1', 'cp1252', 'gbk', 'utf-16']
                diff = ""
                for encoding in encodings_to_try:
                    try:
                        diff = diff_binary.decode(encoding)
                        print(f"成功使用{encoding}编码解码差异")
                        break
                    except UnicodeDecodeError:
                        print(f"使用{encoding}编码解码差异失败")
                        continue
                
                # 如果所有编码都失败，使用latin-1强制解码（不会抛出UnicodeDecodeError）
                if not diff:
                    diff = diff_binary.decode('latin-1', errors='replace')
                    print("使用latin-1强制解码差异")
            
            # 截断过大的差异
            max_diff_size = self.config.get("analysis", {}).get("max_diff_size", 50000)
            if len(diff) > max_diff_size:
                diff = diff[:max_diff_size] + f"\n... (差异过大，已截断，总长度: {len(diff)} 字节)"
            
            return diff
        except Exception as e:
            self._print_error(f"获取暂存区差异失败: {str(e)}")
            return ""
    
    def _get_staged_files(self) -> List[str]:
        """获取暂存区中的文件列表
        
        Returns:
            文件路径列表
        """
        try:
            # 尝试使用utf-8编码获取文件列表
            try:
                output = subprocess.check_output(
                    ["git", "diff", "--staged", "--name-only"],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    encoding='utf-8'
                )
                print("成功使用utf-8编码获取暂存文件列表")
            except UnicodeDecodeError:
                # 如果utf-8失败，尝试使用二进制模式获取，然后使用多种编码尝试解码
                print("使用utf-8编码获取暂存文件列表失败，尝试二进制模式")
                output_binary = subprocess.check_output(
                    ["git", "diff", "--staged", "--name-only"],
                    stderr=subprocess.STDOUT
                )
                
                # 尝试多种编码
                encodings_to_try = ['latin-1', 'cp1252', 'gbk', 'utf-16']
                output = ""
                for encoding in encodings_to_try:
                    try:
                        output = output_binary.decode(encoding)
                        print(f"成功使用{encoding}编码解码暂存文件列表")
                        break
                    except UnicodeDecodeError:
                        print(f"使用{encoding}编码解码暂存文件列表失败")
                        continue
                
                # 如果所有编码都失败，使用latin-1强制解码（不会抛出UnicodeDecodeError）
                if not output:
                    output = output_binary.decode('latin-1', errors='replace')
                    print("使用latin-1强制解码暂存文件列表")
            
            return [file for file in output.strip().split('\n') if file]
        except Exception as e:
            self._print_error(f"获取暂存文件列表失败: {str(e)}")
            return []
    
    def _check_critical_files(self, file_list: List[str]) -> List[str]:
        """检查是否存在关键文件
        
        Args:
            file_list: 文件路径列表
            
        Returns:
            匹配的关键文件列表
        """
        critical_files = []
        
        for file_path in file_list:
            # 忽略匹配的文件
            skip = False
            for pattern in self.ignored_file_patterns:
                if re.search(pattern, file_path):
                    skip = True
                    break
            
            if skip:
                continue
            
            # 检查关键文件模式
            for pattern in self.critical_file_patterns:
                if re.search(pattern, file_path):
                    critical_files.append(file_path)
                    break
        
        return critical_files
    
    def _analyze_with_ai(self, commit_msg: str, diff: str) -> Dict:
        """使用AI分析提交内容
        
        Args:
            commit_msg: 提交信息
            diff: 差异内容
            
        Returns:
            分析结果字典
        """
        model_config = self.config.get("model", {})
        model_type = model_config.get("type", "openai")
        model_name = model_config.get("name", "gpt-3.5-turbo")
        timeout = model_config.get("timeout", 30)
        
        analysis_level = self.config.get("analysis", {}).get("level", "basic")
        include_rating = self.config.get("analysis", {}).get("include_rating", True)
        
        # 构建提示词
        system_message = f"""
        你是一个专业的代码审查助手，负责分析Git提交内容。请根据提交信息和代码差异进行分析，评估提交质量。
        分析级别: {analysis_level}
        {f"请给这次提交评分(1-10分)" if include_rating else ""}
        """
        
        prompt = f"""
        请分析以下Git提交:
        
        ## 提交信息
        {commit_msg}
        
        ## 代码差异
        ```diff
        {diff}
        ```
        
        请提供以下分析:
        1. 提交概述：简要总结这次提交的变更
        2. 提交质量：评估提交信息和代码变更的质量
        3. 潜在问题：指出任何潜在的代码问题或安全隐患
        4. 建议：提供改进建议
        {f"5. 评分：给这次提交评分(1-10分)" if include_rating else ""}
        
        以JSON格式返回结果，包含以下字段：summary, quality, issues, suggestions, {"rating, " if include_rating else ""}analysis_level
        注意：suggestions如果存在多条则以数组形式返回 ["suggestion1"，"suggestion2"]
        """
        
        try:
            llm = LLMClient(model_type = model_type, model_name = model_name).get_model()
            messages = [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": prompt}
                        ]
            response = llm.invoke(messages)
            content = response.content

            try:
                # 提取JSON部分
                json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    result = json.loads(content)

                # 添加原始响应
                result["raw_response"] = content
                return result
            except json.JSONDecodeError:
                # 如果无法解析JSON，则返回原始响应
                return {
                    "summary": "无法解析AI响应",
                    "quality": "解析失败",
                    "issues": ["AI返回的响应不是有效的JSON格式"],
                    "suggestions": ["请重试或调整提示词"],
                    "raw_response": content,
                    "analysis_level": analysis_level
                }
        except Exception as e:
            self._print_error(f"AI分析失败: {str(e)}")
            return {
                "summary": "AI分析过程中出现错误",
                "quality": "分析失败",
                "issues": [f"错误信息: {str(e)}"],
                "suggestions": ["请检查网络连接和API配置"],
                "analysis_level": analysis_level
            }
    
    def _save_to_history(self, result: Dict) -> None:
        """保存分析结果到历史记录
        
        Args:
            result: 分析结果字典
        """
        if not self.save_history:
            return
        
        try:
            # 加载现有历史记录
            history = []
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    try:
                        history = json.load(f)
                    except json.JSONDecodeError:
                        history = []
            
            # 添加新记录
            history.append({
                "timestamp": datetime.now().isoformat(),
                "result": result
            })
            
            # 限制记录数量
            if self.max_records > 0 and len(history) > self.max_records:
                history = history[-self.max_records:]
            
            # 保存历史记录
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            
            # 导出Markdown格式
            self._export_history_to_markdown(history)
            
        except Exception as e:
            self._print_error(f"保存历史记录失败: {str(e)}")
    
    def _export_history_to_markdown(self, history: List[Dict]) -> None:
        """导出历史记录为Markdown格式
        
        Args:
            history: 历史记录列表
        """
        try:
            with open(self.export_path, 'w', encoding='utf-8') as f:
                f.write("# Git提交分析历史记录\n\n")
                
                for i, record in enumerate(reversed(history), 1):
                    timestamp = datetime.fromisoformat(record["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                    result = record["result"]
                    
                    f.write(f"## {i}. {timestamp}\n\n")
                    f.write(f"### 概述\n{result.get('summary', '无概述')}\n\n")
                    f.write(f"### 质量评估\n{result.get('quality', '无评估')}\n\n")
                    
                    if "rating" in result:
                        f.write(f"### 评分\n{result.get('rating', 'N/A')}/10\n\n")
                    
                    if result.get("issues"):
                        f.write("### 潜在问题\n")
                        for issue in result["issues"]:
                            f.write(f"- {issue}\n")
                        f.write("\n")
                    
                    if result.get("suggestions"):
                        f.write("### 改进建议\n")
                        for suggestion in result["suggestions"]:
                            f.write(f"- {suggestion}\n")
                        f.write("\n")
                    
                    f.write("---\n\n")
        except Exception as e:
            self._print_error(f"导出Markdown失败: {str(e)}")
    
    def _print_colored(self, text: str, color: str = None, emoji: str = None) -> None:
        """打印彩色文本
        
        Args:
            text: 要打印的文本
            color: 颜色代码
            emoji: 表情符号
        """
        # 在Windows环境下，避免使用表情符号
        use_emoji = emoji and self.use_emoji and not (sys.platform == 'win32')
        prefix = emoji + " " if use_emoji else ""
        
        if self.colorize and color:
            print(f"{prefix}{color}{text}{Style.RESET_ALL}")
        else:
            print(f"{prefix}{text}")
    
    def _print_info(self, text: str) -> None:
        """打印信息
        
        Args:
            text: 信息文本
        """
        self._print_colored(text, Fore.CYAN, "i" if sys.platform == 'win32' else "ℹ️")
    
    def _print_success(self, text: str) -> None:
        """打印成功信息
        
        Args:
            text: 成功信息文本
        """
        self._print_colored(text, Fore.GREEN, "√" if sys.platform == 'win32' else "✅")
    
    def _print_warning(self, text: str) -> None:
        """打印警告信息
        
        Args:
            text: 警告信息文本
        """
        self._print_colored(text, Fore.YELLOW, "!" if sys.platform == 'win32' else "⚠️")
    
    def _print_error(self, text: str) -> None:
        """打印错误信息
        
        Args:
            text: 错误信息文本
        """
        self._print_colored(text, Fore.RED, "x" if sys.platform == 'win32' else "❌")
    
    def _print_header(self, text: str) -> None:
        """打印标题
        
        Args:
            text: 标题文本
        """
        self._print_colored(f"\n=== {text} ===", Fore.CYAN, "*" if sys.platform == 'win32' else "🔍")
    
    def _display_analysis_result(self, result: Dict) -> None:
        """显示分析结果
        
        Args:
            result: 分析结果字典
        """
        # 根据详细程度调整输出
        if self.verbosity == "minimal":
            # 最小化输出
            if "rating" in result:
                rating = result.get("rating", "N/A")
                self._print_info(f"{MSG['rating']}: {rating}/10")
            
            # 只显示问题和建议的数量
            issues_count = len(result.get("issues", []))
            if issues_count > 0:
                self._print_warning(f"{MSG['potential_issues']}: {issues_count}")
            else:
                self._print_success(MSG["no_issues"])
        
        else:
            # 正常或详细输出
            self._print_header(MSG["analysis_result"])
            
            # 概述
            self._print_colored(f"{MSG['overview']}:", Fore.CYAN)
            self._print_colored(result.get("summary", MSG["no_overview"]), None)
            print()
            
            # 质量评估
            self._print_colored(f"{MSG['quality']}:", Fore.CYAN)
            self._print_colored(result.get("quality", MSG["no_quality"]), None)
            print()
            
            # 评分（如果存在）
            if "rating" in result:
                rating = result.get("rating", "N/A")
                rating_color = Fore.GREEN if rating >= 7 else (Fore.YELLOW if rating >= 4 else Fore.RED)
                self._print_colored(f"{MSG['rating']}:", Fore.CYAN)
                self._print_colored(f"{rating}/10", rating_color)
                print()
            
            # 潜在问题
            issues = result.get("issues", [])
            if issues:
                self._print_colored(f"{MSG['potential_issues']}:", Fore.YELLOW)
                for issue in issues:
                    self._print_warning(f"- {issue}")
                print()
            else:
                self._print_success(MSG["no_issues"])
                print()
            
            # 改进建议
            suggestions = result.get("suggestions", [])
            if suggestions:
                self._print_colored(f"{MSG['suggestions']}:", Fore.CYAN)
                # 将每条建议单独一行显示
                for suggestion in suggestions:
                    self._print_info(f"- {suggestion}")
                print()
            
            # 详细模式下显示更多信息
            if self.verbosity == "verbose" and "raw_response" in result:
                self._print_header(MSG["ai_response"])
                print(result["raw_response"])
                print()
        
        # 显示提示（如果启用）
        if self.show_tips:
            self._print_colored(f"\n{MSG['tips']}", Fore.CYAN, 
                               ">" if sys.platform == 'win32' else "💡")
    
    def analyze(self) -> bool:
        """分析当前的提交
        
        Returns:
            分析结果，True表示通过检查，False表示未通过
        """
        if not self.enabled:
            self._print_info(MSG["commit_analysis_disabled"])
            return True
        
        # 输出标题
        self._print_header(MSG["git_analysis"])
        
        # 获取提交信息
        commit_msg = self._get_commit_message()
        print(commit_msg)
        # 检查提交信息长度
        min_length = self.config.get("analysis", {}).get("min_commit_message_length", 10)
        if len(commit_msg) < min_length:
            self._print_error(MSG["commit_msg_short"].format(min_length, len(commit_msg)))
            return False
        
        # 获取暂存文件列表
        staged_files = self._get_staged_files()
        if not staged_files:
            self._print_error(MSG["no_staged_files"])
            return False
        
        # 检查关键文件
        critical_files = self._check_critical_files(staged_files)
        if critical_files:
            self._print_warning(MSG["sensitive_files"])
            for file in critical_files:
                self._print_warning(f"- {file}")
        
        # 获取差异
        diff = self._get_staged_diff()
        if not diff:
            self._print_error(MSG["no_diff"])
            return False
        
        # 使用AI分析提交
        self._print_info(MSG["analyzing"])
        result = self._analyze_with_ai(commit_msg, diff)
        
        # 保存到历史记录
        if self.save_history:
            self._save_to_history(result)
        
        # 显示分析结果
        self._display_analysis_result(result)
        
        # 检查是否有严重问题需要阻止提交
        if self.block_on_critical and critical_files:
            self._print_error(MSG["block_sensitive"])
            return False
        
        # 检查分析结果中的评分（如果有）
        if "rating" in result and result.get("rating", 0) < 3:
            if self.block_on_critical:
                self._print_error(MSG["block_low_rating"])
                return False
            else:
                self._print_warning(MSG["low_rating"])
        
        return True


def main():
    """主函数，用于从命令行运行"""
    # 检查是否通过环境变量或参数禁用钩子
    if 'SKIP_GIT_HOOKS' in os.environ or '--skip-hooks' in sys.argv or '--no-verify' in sys.argv:
        print("警告: Git钩子检查已被跳过")
        sys.exit(0)
    
    # 检查钩子类型
    hook_type = os.path.basename(sys.argv[0]) if len(sys.argv) > 0 else "unknown"
    
    # 如果输入参数包含--help或-h，显示帮助信息
    if '--help' in sys.argv or '-h' in sys.argv:
        print(f"Git钩子: {hook_type}")
        print("用法: git commit [选项]")
        print("")
        print("可用选项:")
        print("  --skip-hooks, --no-verify  跳过钩子检查")
        print("  --help, -h                 显示此帮助信息")
        print("")
        print("环境变量:")
        print("  SKIP_GIT_HOOKS=1           设置此环境变量可跳过钩子检查")
        sys.exit(0)
    
    analyzer = GitCommitAnalyzer()
    result = analyzer.analyze()
    
    if not result:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main() 