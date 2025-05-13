# -*- coding: utf-8 -*-
# @Time : 2025/5/9
# @Author : renjiajia

import argparse
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
from .voice_trainer import VoiceTrainer, print_training_texts, DEFAULT_TEXT_ID

def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="语音训练工具 - 训练自定义声音模型",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看训练文本列表
  python -m media.voice.cli list-texts
  
  # 训练声音（男声）
  python -m media.voice.cli train --file data/voice/sample.wav --gender 1
  
  # 训练声音（女声）并自定义任务名称
  python -m media.voice.cli train --file data/voice/sample.wav --gender 2 --name "我的女声模型"
  
  # 使用特定文本ID训练
  python -m media.voice.cli train --file data/voice/sample.wav --text-id 5001 --seg-id 1
  
  # 不等待训练完成
  python -m media.voice.cli train --file data/voice/sample.wav --no-wait
""")
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # 列出训练文本
    list_texts_parser = subparsers.add_parser("list-texts", help="列出可用的训练文本")
    list_texts_parser.add_argument("--text-id", type=int, default=DEFAULT_TEXT_ID, 
                              help=f"文本集ID (默认: {DEFAULT_TEXT_ID})")
    
    # 检查任务状态
    check_parser = subparsers.add_parser("check", help="检查任务状态")
    check_parser.add_argument("--task-id", required=True, help="任务ID")
    
    # 训练声音
    train_parser = subparsers.add_parser("train", help="训练声音")
    train_parser.add_argument("--file", required=True, help="音频文件路径")
    train_parser.add_argument("--text-id", type=int, default=DEFAULT_TEXT_ID,
                             help=f"训练文本集ID (默认: {DEFAULT_TEXT_ID})")
    train_parser.add_argument("--seg-id", type=int, default=1,
                             help="训练文本段落ID (默认: 1)")
    train_parser.add_argument("--gender", type=int, choices=[1, 2], default=1,
                             help="性别 (1: 男, 2: 女, 默认: 1)")
    train_parser.add_argument("--name", help="任务名称 (默认: 自动生成)")
    train_parser.add_argument("--no-wait", action="store_true", 
                             help="不等待训练完成就返回 (默认: 等待)")
    
    return parser

def handle_list_texts(args):
    """处理list-texts命令"""
    trainer = VoiceTrainer()
    texts = trainer.get_training_texts(args.text_id)
    
    print("\n可用的训练文本列表:")
    print(f"文本集ID: {args.text_id}")
    print("-" * 50)
    
    for text in texts:
        print(f"段落ID: {text['segId']}")
        print(f"内容: {text['segText']}")
        print("-" * 50)

def handle_check_task(args):
    """处理check命令"""
    trainer = VoiceTrainer()
    trainer.task_id = args.task_id
    
    try:
        response = trainer.get_task_status()
        
        if not response.get('data'):
            print(f"任务 {args.task_id} 不存在或无法访问")
            return 1
            
        status = response['data']['trainStatus']
        status_text = {
            -1: "训练中",
            0: "训练失败",
            1: "训练成功"
        }.get(status, f"未知状态({status})")
        
        print(f"\n任务ID: {args.task_id}")
        print(f"状态: {status_text}")
        
        if status == 1:
            print(f"音库ID: {response['data']['assetId']}")
        elif status == 0:
            print(f"失败原因: {response['data'].get('reason', '未知')}")
            
        return 0
        
    except Exception as e:
        print(f"检查任务状态失败: {e}")
        return 1

def handle_train(args):
    """处理train命令"""
    # 检查文件是否存在
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"错误: 文件 {args.file} 不存在")
        return 1
        
    # 初始化训练器
    trainer = VoiceTrainer()
    
    try:
        print(f"\n使用文件 {args.file} 开始训练流程...")
        print(f"文本ID: {args.text_id}, 段落ID: {args.seg_id}, 性别: {'男' if args.gender == 1 else '女'}")
        
        result = trainer.train_voice(
            file_path=str(file_path),
            text_id=args.text_id,
            text_seg_id=args.seg_id,
            task_name=args.name,
            gender=args.gender,
            wait=not args.no_wait
        )
        
        if args.no_wait:
            print(f"\n任务已提交，但未等待完成。")
            print(f"任务ID: {result['task_id']}")
            print(f"可以随时使用以下命令检查状态:")
            print(f"  python -m media.voice.cli check --task-id {result['task_id']}")
        else:
            print(f"\n训练成功!")
            print(f"音库ID: {result['assetId']}")
            
        return 0
            
    except Exception as e:
        print(f"\n训练过程出错: {e}")
        return 1

def main():
    """命令行入口函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
        
    # 执行相应的命令
    if args.command == "list-texts":
        return handle_list_texts(args)
    elif args.command == "check":
        return handle_check_task(args)
    elif args.command == "train":
        return handle_train(args)
    else:
        parser.print_help()
        return 0

if __name__ == "__main__":
    sys.exit(main()) 