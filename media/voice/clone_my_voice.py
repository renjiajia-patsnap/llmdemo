# -*- coding: utf-8 -*-
# @Time : 2025/5/6 13:43
# @Author : renjiajia

"""
声音克隆工具 - 基于阿里云通义千问语音合成服务

本模块用于克隆用户声音并使用克隆的声音进行语音合成。
使用阿里云通义千问的CosyVoice服务。

文档参考: https://help.aliyun.com/zh/model-studio/cosyvoice-clone-api

使用方法:
1. 克隆新声音:
   python clone_my_voice.py clone --url <音频URL> --prefix <声音前缀> 

2. 使用已有声音ID合成语音:
   python clone_my_voice.py synthesize --voice-id <声音ID> --text <文本> --output <输出文件>

3. 列出所有声音:
   python clone_my_voice.py list-voices
"""

import os
import logging
import sys
import argparse
from typing import Optional, List, Dict, Any, Union
import dashscope
from dashscope.audio.tts_v2 import VoiceEnrollmentService, SpeechSynthesizer
from dotenv import load_dotenv
import uuid

"""
# 创建logs目录（如果不存在）
os.makedirs('logs', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler('logs/voice_cloner.log')  # 输出到文件
    ]
)
"""

# 创建logs目录
os.makedirs('logs', exist_ok=True)

# 获取根日志记录器
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 创建格式器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# 创建文件处理器
# 日志名称按照文件名生成
# 获取文件名
logname = os.path.basename(__file__)
# 去掉文件名的后缀
logname = os.path.splitext(logname)[0]
file_handler = logging.FileHandler(f'logs/{logname}.log')
file_handler.setFormatter(formatter)

# 添加处理器到日志记录器
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# 获取当前工作目录
current_dir = os.getcwd()
print(f"当前工作目录: {current_dir}")

class VoiceCloner:
    """声音克隆工具类"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化声音克隆工具
        
        Args:
            api_key: 阿里云API密钥，如果不提供则从环境变量读取
        """
        # 加载环境变量
        load_dotenv()
        
        # 设置API密钥
        self.api_key = api_key or os.getenv('TONGYI_API_KEY')
        if not self.api_key:
            logger.error("未设置API密钥，请设置TONGYI_API_KEY环境变量或在初始化时提供")
            raise ValueError("API密钥未设置")
            
        dashscope.api_key = self.api_key
        
        # 默认使用的模型
        self.target_model = "cosyvoice-v2"
        
        # 初始化服务
        self.enrollment_service = VoiceEnrollmentService()
        
    def clone_voice(self, audio_url: str, prefix: str) -> str:
        """
        从音频URL克隆声音
        
        Args:
            audio_url: 音频文件URL
            prefix: 声音ID前缀
            
        Returns:
            生成的voice_id
        """
        try:
            logger.info(f"开始克隆声音，前缀: {prefix}")
            
            # 避免频繁调用 create_voice 方法的提示
            logger.warning("注意: 每次调用都会创建新音色，阿里云主账号最多可复刻1000个音色")
            
            voice_id = self.enrollment_service.create_voice(
                target_model=self.target_model, 
                prefix=prefix, 
                url=audio_url
            )
            logger.info(f"声音克隆成功，声音ID: {voice_id}")
            logger.debug(f"请求ID: {self.enrollment_service.get_last_request_id()}")
            return voice_id
        except Exception as e:
            logger.error(f"声音克隆失败: {str(e)}")
            raise
    
    def synthesize_speech(self, voice_id: str, text: str, output_file: str = "output.mp3") -> None:
        """
        使用克隆的声音合成语音
        
        Args:
            voice_id: 声音ID
            text: 要合成的文本
            output_file: 输出文件路径
        """
        try:
            logger.info(f"开始合成语音，声音ID: {voice_id}")
            synthesizer = SpeechSynthesizer(model=self.target_model, voice=voice_id)
            audio = synthesizer.call(text)
            logger.debug(f"请求ID: {synthesizer.get_last_request_id()}")
            
            with open(output_file, "wb") as f:
                f.write(audio)
            logger.info(f"语音合成成功，已保存到: {output_file}")
        except Exception as e:
            logger.error(f"语音合成失败: {str(e)}")
            raise
    
    def list_voices(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出当前账号下的所有声音ID
        
        Args:
            prefix: 可选的前缀过滤器，只返回指定前缀的声音
            
        Returns:
            声音ID列表
        """
        try:
            logger.info("获取所有声音列表...")
            
            # 调用API获取列表
            if prefix:
                logger.info(f"使用前缀过滤: {prefix}")
                response = self.enrollment_service.list_voices(prefix=prefix)
            else:
                response = self.enrollment_service.list_voices()
            
            # 处理响应数据
            logger.debug(f"API响应数据: {response}")
            
            # 根据实际返回的格式处理
            # 如果响应本身就是列表
            if isinstance(response, list):
                voices = response
                logger.info(f"获取到 {len(voices)} 个声音")
                return voices
            
            # 如果响应是字典，可能包含不同的键
            elif isinstance(response, dict):
                # 尝试获取声音列表的可能键
                for key in ['voices', 'voice_list', 'data', 'results']:
                    if key in response and isinstance(response[key], list):
                        voices = response[key]
                        logger.info(f"获取到 {len(voices)} 个声音 (从 '{key}' 字段)")
                        return voices
                
                # 如果响应中没有找到声音列表，但响应本身可能包含声音信息
                if 'voice_id' in response or 'id' in response:
                    logger.info("响应似乎包含单个声音信息")
                    return [response]
                
                # 无法从响应中提取出声音列表
                logger.warning(f"无法从响应中提取出声音列表，响应数据: {response}")
                return []
            
            # 其他情况
            else:
                logger.warning(f"意外的响应类型: {type(response)}")
                return []
                
        except Exception as e:
            logger.error(f"获取声音列表失败: {str(e)}")
            raise
            
    def delete_voice(self, voice_id: str) -> bool:
        """
        删除指定的声音ID
        
        Args:
            voice_id: 要删除的声音ID
            
        Returns:
            删除是否成功
        """
        try:
            logger.info(f"删除声音: {voice_id}")
            result = self.enrollment_service.delete_voice(voice_id)
            logger.info(f"声音删除成功: {voice_id}")
            return True
        except Exception as e:
            logger.error(f"删除声音失败: {str(e)}")
            raise

def setup_argparse() -> argparse.ArgumentParser:
    """设置命令行参数解析器"""
    parser = argparse.ArgumentParser(description="阿里云通义千问声音克隆工具")
    subparsers = parser.add_subparsers(dest="command", help="操作命令")
    
    # 克隆声音命令
    clone_parser = subparsers.add_parser("clone", help="从音频URL克隆新声音")
    clone_parser.add_argument("--url", required=True, help="音频文件URL")
    clone_parser.add_argument("--prefix", required=True, help="声音ID前缀")
    
    # 语音合成命令
    synth_parser = subparsers.add_parser("synthesize", help="使用已有声音ID合成语音")
    synth_parser.add_argument("--voice-id", required=True, help="声音ID")
    synth_parser.add_argument("--text", required=True, help="要合成的文本")
    synth_parser.add_argument("--output", default="output.mp3", help="输出文件路径")
    
    # 列出声音命令
    list_parser = subparsers.add_parser("list-voices", help="列出所有可用声音")
    list_parser.add_argument("--prefix", help="筛选指定前缀的声音")
    
    # 删除声音命令
    delete_parser = subparsers.add_parser("delete-voice", help="删除指定声音")
    delete_parser.add_argument("--voice-id", required=True, help="要删除的声音ID")
    
    # 一站式流程：克隆并合成
    all_in_one_parser = subparsers.add_parser("clone-and-synthesize", 
                                             help="一站式流程：克隆声音并立即合成")
    all_in_one_parser.add_argument("--url", required=True, help="音频文件URL")
    all_in_one_parser.add_argument("--prefix", required=True, help="声音ID前缀")
    all_in_one_parser.add_argument("--text", required=True, help="要合成的文本")
    all_in_one_parser.add_argument("--output", default="output.mp3", help="输出文件路径")
    
    return parser

def main():
    """命令行入口函数"""
    parser = setup_argparse()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # 创建声音克隆器实例
        cloner = VoiceCloner()
        
        # 执行对应命令
        if args.command == "clone":
            voice_id = cloner.clone_voice(args.url, args.prefix)
            print(f"声音ID: {voice_id}")
            
        elif args.command == "synthesize":
            cloner.synthesize_speech(args.voice_id, args.text, args.output)
            
        elif args.command == "list-voices":
            voices = cloner.list_voices(args.prefix if hasattr(args, 'prefix') else None)
            print("\n可用的声音列表:")
            for voice in voices:
                # 尝试获取不同命名的字段
                voice_id = voice.get('voice_id', voice.get('id', 'N/A'))
                created_time = voice.get('gmt_create', voice.get('createTime', voice.get('created_at', 'N/A')))
                status = voice.get('status', 'N/A')
                modified_time = voice.get('gmt_modified', voice.get('updatedTime', voice.get('modified_at', 'N/A')))
                
                print(f"ID: {voice_id}")
                print(f"创建时间: {created_time}")
                print(f"状态: {status}")
                print(f"最后修改时间: {modified_time}")
                
                # 打印其他可能有用的字段
                for key, value in voice.items():
                    if key not in ['voice_id', 'id', 'gmt_create', 'createTime', 'created_at', 
                                  'status', 'gmt_modified', 'updatedTime', 'modified_at']:
                        print(f"{key}: {value}")
                
                print("-" * 40)
                
        elif args.command == "delete-voice":
            success = cloner.delete_voice(args.voice_id)
            if success:
                print(f"声音 {args.voice_id} 已成功删除")
                
        elif args.command == "clone-and-synthesize":
            voice_id = cloner.clone_voice(args.url, args.prefix)
            print(f"声音ID: {voice_id}")
            cloner.synthesize_speech(voice_id, args.text, args.output)
            
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    audio_url = "https://jiajia-aliyun-file.oss-cn-beijing.aliyuncs.com/youyou3.mp3?Expires=1746625911&OSSAccessKeyId=TMP.3Ksz7uJsBzGgt6bGcmEsmDCdeBfL2eytnQaBDxoNeMjT1Zy5LPMPtpYcGwNNMDBXKVHHoPzhaWLmw2vV7zBYsiHQ2GHA6Y&Signature=5k6ABbShrZLROX2qc%2B%2BVLM24WXg%3D"
    cloner = VoiceCloner()
    voice_id = cloner.clone_voice(audio_url = audio_url , prefix="yangping")
    print("\n声音ID:%s",voice_id)
    voices = cloner.list_voices()
    print("\n可用的声音列表:")
    for voice in voices:
        print(f"ID: {voice.get('voice_id','N/A')}")
        print(f"状态: {voice.get('status', 'N/A')}")
        print(f"创建时间: {voice.get('gmt_create', 'N/A')}")
        print("-" * 40)
    #voice_id = "cosyvoice-v2-jiajia-2cc8ce17365f46d8aa464df49b51fab1"
    text = """
    小白兔开超市
    从前，在森林里住着一只聪明又勤劳的小白兔。它每天都在想："森林里的朋友们常常要跑到很远的地方买东西，要是我能开一家超市，大家就方便多了！"
    
    说干就干！小白兔用胡萝卜换来了一间空木屋，把它打扫得干干净净，然后写了一块牌子：
    
    "小白兔森林超市开张啦！"
    
    超市里有好多好东西：
    
    新鲜的胡萝卜
    
    香甜的蜂蜜
    
    软绵绵的蘑菇
    
    各种颜色的果汁
    
    还有彩色铅笔、画本和故事书
    
    第一天，森林里的朋友们都来了。
    
    小松鼠跳着说："太好了！我再也不用跑到山那边去买坚果啦！"
    小刺猬慢慢地走过来说："我想买点蜂蜜，给妈妈做甜点。"
    小熊还带来了一大筐蓝莓，跟小白兔换了几本故事书。
    
    小白兔笑眯眯地说："欢迎大家来逛超市，有需要都可以告诉我，我还可以帮大家订货呢！"
    
    一天，小鸟飞来告诉小白兔："冬天快来了，大家想提前准备一些粮食和保暖的东西。"
    
    于是，小白兔马上进了更多货物，还摆上了暖暖的围巾、帽子和干果包。森林朋友们都夸小白兔贴心又能干。
    
    从那以后，小白兔的超市每天都热热闹闹，不只是买东西的地方，还是朋友们聊天、交换故事的小天地。
    
    故事寓意：
    这个故事告诉我们：帮助别人会让大家更幸福，动脑筋加上努力，就能实现美好的梦想。
    """
    # 随机生成一个文件名
    filename = str(uuid.uuid4())

    output_file = f"voice/{filename}.mp3"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    cloner.synthesize_speech(voice_id = voice_id,text = text, output_file= output_file)