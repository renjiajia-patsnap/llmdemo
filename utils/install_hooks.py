#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Git钩子安装脚本
用于将钩子脚本安装到.git/hooks目录下
"""

import os
import sys
import stat
import shutil
from pathlib import Path
import subprocess

def get_git_root():
    """获取Git项目根目录
    
    Returns:
        项目根目录路径
    """
    try:
        git_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], 
            stderr=subprocess.STDOUT, 
            universal_newlines=True).strip()
        return git_root
    except subprocess.CalledProcessError:
        print("错误: 未找到Git仓库，请在Git仓库中运行此脚本")
        sys.exit(1)

def create_hook_script(hook_name, script_content):
    """创建钩子脚本
    
    Args:
        hook_name: 钩子名称 (pre-commit, commit-msg等)
        script_content: 脚本内容
    
    Returns:
        脚本路径
    """
    git_root = get_git_root()
    hooks_dir = os.path.join(git_root, ".git", "hooks")
    hook_path = os.path.join(hooks_dir, hook_name)
    
    # 创建目录（如果不存在）
    os.makedirs(hooks_dir, exist_ok=True)
    
    # 写入脚本内容
    with open(hook_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # 设置可执行权限
    os.chmod(hook_path, os.stat(hook_path).st_mode | stat.S_IEXEC)
    
    return hook_path

def check_dependencies():
    """检查依赖项
    
    Returns:
        缺失的依赖项列表
    """
    required_packages = ["colorama", "pyyaml", "openai"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_hooks():
    """安装所有钩子"""
    # 检查依赖项
    missing_packages = check_dependencies()
    if missing_packages:
        print(f"警告: 以下依赖项缺失: {', '.join(missing_packages)}")
        choice = input("是否安装缺失的依赖项? [y/N]: ")
        if choice.lower() == 'y':
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
    
    git_root = get_git_root()
    project_root = Path(git_root)
    
    # 创建pre-commit钩子
    pre_commit_content = f"""#!/bin/sh
# Git pre-commit钩子，在提交前分析代码

# 获取项目根目录
PROJECT_ROOT="{git_root}"

# 运行Python脚本进行分析
python "$PROJECT_ROOT/utils/git_hooks.py" "$@"

# 检查脚本返回值
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "提交被中止，请修复上述问题后重试"
    exit $exit_code
fi

exit 0
"""
    
    pre_commit_path = create_hook_script("pre-commit", pre_commit_content)
    print(f"✅ pre-commit钩子已安装到: {pre_commit_path}")
    
    # 创建commit-msg钩子
    commit_msg_content = f"""#!/bin/sh
# Git commit-msg钩子，用于验证提交消息

# 获取项目根目录
PROJECT_ROOT="{git_root}"

# 运行Python脚本进行分析
python "$PROJECT_ROOT/utils/git_hooks.py" "$@"

# 检查脚本返回值
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "提交被中止，请修复上述问题后重试"
    exit $exit_code
fi

exit 0
"""
    
    commit_msg_path = create_hook_script("commit-msg", commit_msg_content)
    print(f"✅ commit-msg钩子已安装到: {commit_msg_path}")
    
    # 检查是否需要更新requirements.txt
    print("检查是否需要更新requirements.txt...")
    req_path = project_root / "requirements.txt"
    
    if req_path.exists():
        # 读取已有的依赖项
        with open(req_path, 'r', encoding='utf-8') as f:
            current_requirements = f.read()
        
        # 检查依赖项是否已经存在
        needed_packages = []
        for package in ["colorama", "pyyaml", "openai"]:
            if not any(line.startswith(package) for line in current_requirements.splitlines()):
                needed_packages.append(package)
        
        # 添加缺失的依赖项
        if needed_packages:
            with open(req_path, 'a', encoding='utf-8') as f:
                f.write("\n# Git钩子依赖项\n")
                for package in needed_packages:
                    f.write(f"{package}\n")
            print(f"✅ 已将缺失的依赖项添加到requirements.txt")
    
    print("\n🎉 Git钩子安装完成！")
    print("现在，每次提交前都会自动运行代码分析。")
    print("如需配置或禁用钩子，请编辑config/git_hook_config.yaml文件。")

if __name__ == "__main__":
    install_hooks() 