# -*- coding: utf-8 -*-
# @Time : 2025/5/9
# @Author : renjiajia

import json
import time
import requests
import hashlib
import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any
from requests_toolbelt.multipart.encoder import MultipartEncoder
from dotenv import load_dotenv

# 尝试导入配置文件，如果失败则继续使用默认配置
try:
    from config.settings import API_CONFIG, VOICE_TRAIN_CONFIG
    
    # 从配置中获取值
    BASE_AUTH_URL = API_CONFIG['voice_train']['auth_url']
    BASE_TRAIN_URL = API_CONFIG['voice_train']['train_url']
    DEFAULT_TEXT_ID = API_CONFIG['voice_train']['default_text_id']
    DEFAULT_APP_ID = API_CONFIG['voice_train']['app_id']
    DEFAULT_API_KEY = API_CONFIG['voice_train']['api_key']
    MAX_WAIT_TIME = VOICE_TRAIN_CONFIG['max_wait_time']
    CHECK_INTERVAL = VOICE_TRAIN_CONFIG['check_interval']
    AUDIO_FILE_PATH = VOICE_TRAIN_CONFIG['audio_file_path']
    
except ImportError:
    # 加载环境变量和默认配置
    load_dotenv()
    
    # 使用默认值
    BASE_AUTH_URL = "http://avatar-hci.xfyousheng.com/aiauth/v1/token"
    BASE_TRAIN_URL = "http://opentrain.xfyousheng.com/voice_train"
    DEFAULT_TEXT_ID = 5001  # 通用的训练文本集
    DEFAULT_APP_ID = os.getenv("APPID")
    DEFAULT_API_KEY = os.getenv("APIKey")
    MAX_WAIT_TIME = 3600
    CHECK_INTERVAL = 10
    AUDIO_FILE_PATH = "data/voice/training"

# 确保音频文件目录存在
Path(AUDIO_FILE_PATH).mkdir(parents=True, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VoiceTrainer")

# 状态码映射
TRAINING_STATUS = {
    -1: "训练中",
    0: "训练失败",
    1: "训练成功"
}


class VoiceTrainer:
    """语音训练器类，用于创建和管理语音训练任务"""

    def __init__(self, appid: str = None, apikey: str = None):
        """
        初始化语音训练器
        
        Args:
            appid: 应用ID，如果不提供则从环境变量或配置获取
            apikey: API密钥，如果不提供则从环境变量或配置获取
        """
        self.appid = appid or DEFAULT_APP_ID
        self.apikey = apikey or DEFAULT_API_KEY
        
        if not self.appid or not self.apikey:
            raise ValueError("APPID和APIKey必须提供或在环境变量/配置中设置")
            
        self.token = self._get_token()
        self.timestamp = int(time.time() * 1000)
        self.task_id = ""
        
    def _get_authorization(self, timestamp: int, data: Dict) -> str:
        """
        获取鉴权签名
        
        Args:
            timestamp: 时间戳
            data: 请求数据
            
        Returns:
            生成的签名字符串
        """
        body = json.dumps(data)
        key_sign = hashlib.md5((self.apikey + str(timestamp)).encode('utf-8')).hexdigest()
        sign = hashlib.md5((key_sign + body).encode("utf-8")).hexdigest()
        return sign

    def _get_token(self) -> str:
        """
        获取鉴权token
        
        Returns:
            鉴权token字符串
        
        Raises:
            Exception: 获取token失败时抛出异常
        """
        timestamp = int(time.time() * 1000)
        body = {
            "base": {
                "appid": self.appid,
                "version": "v1",
                "timestamp": str(timestamp)
            },
            "model": "remote"
        }
        
        headers = {
            'Authorization': self._get_authorization(timestamp, body),
            'Content-Type': 'application/json'
        }
        
        logger.debug(f"获取Token: body={body}")
        
        try:
            response = requests.post(
                url=BASE_AUTH_URL, 
                data=json.dumps(body),
                headers=headers
            )
            response.raise_for_status()
            resp_data = response.json()
            
            if resp_data.get('retcode') != '000000':
                raise Exception(f"获取token失败: {resp_data}")
                
            logger.info("成功获取API访问Token")
            return resp_data.get('accesstoken')
            
        except Exception as e:
            logger.error(f"获取token失败: {str(e)}")
            raise

    def _get_sign(self, body: Any) -> str:
        """
        获取请求签名
        
        Args:
            body: 请求体内容
            
        Returns:
            生成的签名
        """
        key_sign = hashlib.md5(str(body).encode('utf-8')).hexdigest()
        sign = hashlib.md5((self.apikey + str(self.timestamp) + key_sign).encode("utf-8")).hexdigest()
        return sign

    def _get_headers(self, sign: str) -> Dict[str, str]:
        """
        构建请求头
        
        Args:
            sign: 签名字符串
            
        Returns:
            请求头字典
        """
        return {
            "X-Sign": sign,
            "X-Token": self.token,
            "X-AppId": self.appid,
            "X-Time": str(self.timestamp)
        }
        
    def _make_request(self, endpoint: str, body: Dict, headers: Dict = None, is_json: bool = True) -> Dict:
        """
        发送API请求
        
        Args:
            endpoint: API端点路径
            body: 请求体
            headers: 请求头
            is_json: 是否返回JSON数据
            
        Returns:
            响应数据
        
        Raises:
            Exception: 请求失败时抛出异常
        """
        url = f"{BASE_TRAIN_URL}/{endpoint}"
        
        if headers is None:
            sign = self._get_sign(body)
            headers = self._get_headers(sign)
        
        try:
            if is_json:
                response = requests.post(url=url, json=body, headers=headers)
            else:
                response = requests.post(url=url, data=body, headers=headers)
                
            response.raise_for_status()
            
            if is_json:
                return response.json()
            return {"text": response.text}
            
        except Exception as e:
            logger.error(f"请求失败: {endpoint}, 错误: {str(e)}")
            raise

    def get_training_texts(self, text_id: int = DEFAULT_TEXT_ID) -> List[Dict]:
        """
        获取训练文本列表
        
        Args:
            text_id: 文本集ID
            
        Returns:
            训练文本列表
        """
        body = {"textId": text_id}
        response = self._make_request("task/traintext", body)
        
        logger.info("成功获取训练文本列表")
        return response['data']['textSegs']

    def create_task(self, 
                    task_name: str = None, 
                    gender: int = 1, 
                    resource_name: str = None,
                    language: str = "cn", 
                    callback_url: str = None) -> str:
        """
        创建训练任务
        
        Args:
            task_name: 任务名称
            gender: 训练音色性别 (1:男, 2:女)
            resource_name: 音库名称
            language: 语言 (cn: 中文, en: 英文, jp: 日文, ko: 韩文, ru: 俄文)
            callback_url: 回调URL
            
        Returns:
            任务ID
        """
        # 使用当前时间作为默认名称
        timestamp = time.strftime("%Y%m%d%H%M%S")
        
        body = {
            "taskName": task_name or f"语音训练_{timestamp}",
            "sex": gender,
            "resourceType": 12,
            "resourceName": resource_name or f"音库_{timestamp}",
            "language": language
        }
        
        if callback_url:
            body["callbackUrl"] = callback_url
            
        response = self._make_request("task/add", body, is_json=False)
        resp_data = json.loads(response["text"])
        
        if resp_data.get('data'):
            self.task_id = resp_data['data']
            logger.info(f"成功创建训练任务: {self.task_id}")
            return self.task_id
        else:
            error_msg = f"创建任务失败: {resp_data}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def add_audio_from_url(self, audio_url: str, text_id: int = DEFAULT_TEXT_ID, text_seg_id: int = 1) -> Dict:
        """
        通过URL添加音频到训练任务
        
        Args:
            audio_url: 音频URL
            text_id: 文本集ID
            text_seg_id: 文本段落ID
            
        Returns:
            响应数据
        """
        if not self.task_id:
            self.create_task()
            
        body = {
            "taskId": self.task_id,
            "audioUrl": audio_url,
            "textId": text_id,
            "textSegId": text_seg_id
        }
        
        response = self._make_request("audio/v1/add", body, is_json=False)
        resp_data = json.loads(response["text"])
        
        logger.info(f"添加音频URL成功: {audio_url}")
        return resp_data

    def add_audio_from_file(self, 
                          file_path: str, 
                          text_id: int = DEFAULT_TEXT_ID, 
                          text_seg_id: int = 1) -> Dict:
        """
        通过本地文件添加音频到训练任务
        
        Args:
            file_path: 音频文件路径
            text_id: 文本集ID
            text_seg_id: 文本段落ID
            
        Returns:
            响应数据
        """
        if not self.task_id:
            self.create_task()
            
        # 确保文件存在
        audio_path = Path(file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {file_path}")
            
        # 获取MIME类型
        file_ext = audio_path.suffix.lower()
        content_type = {
            '.wav': 'audio/wav',
            '.mp3': 'audio/mpeg',
            '.m4a': 'audio/m4a',
            '.pcm': 'audio/pcm'
        }.get(file_ext, 'audio/wav')
        
        # 构造multipart请求
        form_data = MultipartEncoder(
            fields={
                "file": (audio_path.name, open(str(audio_path), 'rb'), content_type),
                "taskId": str(self.task_id),
                "textId": str(text_id),
                "textSegId": str(text_seg_id)
            }
        )
        
        sign = self._get_sign(form_data)
        headers = self._get_headers(sign)
        headers['Content-Type'] = form_data.content_type
        
        response = self._make_request(
            "task/submitWithAudio",
            form_data,
            headers=headers,
            is_json=False
        )
        
        resp_data = json.loads(response["text"])
        logger.info(f"添加音频文件成功: {file_path}")
        return resp_data

    def submit_task(self) -> Dict:
        """
        提交训练任务
        
        Returns:
            响应数据
        """
        if not self.task_id:
            raise ValueError("需要先创建任务")
            
        body = {"taskId": self.task_id}
        response = self._make_request("task/submit", body, is_json=False)
        resp_data = json.loads(response["text"])
        
        logger.info(f"已提交训练任务: {self.task_id}")
        return resp_data

    def get_task_status(self) -> Dict:
        """
        获取任务状态
        
        Returns:
            任务状态数据
        """
        if not self.task_id:
            raise ValueError("需要先创建任务")
            
        body = {"taskId": self.task_id}
        response = self._make_request("task/result", body, is_json=False)
        resp_data = json.loads(response["text"])
        
        logger.debug(f"获取任务状态: {resp_data}")
        return resp_data

    def wait_for_completion(self, 
                           check_interval: int = CHECK_INTERVAL, 
                           max_wait_time: int = MAX_WAIT_TIME) -> Dict:
        """
        等待任务完成
        
        Args:
            check_interval: 检查间隔（秒）
            max_wait_time: 最大等待时间（秒）
            
        Returns:
            完成的任务数据
        
        Raises:
            TimeoutError: 超时时抛出异常
            Exception: 任务失败时抛出异常
        """
        # 计算最大尝试次数
        max_attempts = max_wait_time // check_interval
        start_time = time.time()
        
        for attempt in range(max_attempts):
            elapsed_time = time.time() - start_time
            remaining_time = max_wait_time - elapsed_time
            
            if remaining_time <= 0:
                raise TimeoutError(f"等待任务完成超时，已等待{elapsed_time:.1f}秒")
                
            response = self.get_task_status()
            
            if not response.get('data'):
                logger.warning(f"获取任务状态异常: {response}")
                time.sleep(min(check_interval, remaining_time))
                continue
                
            status = response['data']['trainStatus']
            status_text = TRAINING_STATUS.get(status, f"未知状态({status})")
            
            logger.info(f"任务状态: {status_text}, 尝试次数: {attempt+1}/{max_attempts}, 已用时: {elapsed_time:.1f}秒")
            
            if status == 1:  # 训练成功
                asset_id = response['data']['assetId']
                logger.info(f"训练成功! 音库ID(res_id): {asset_id}")
                return response['data']
                
            elif status == 0:  # 训练失败
                error_msg = f"训练失败: {response['data'].get('reason', '未知原因')}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
            time.sleep(min(check_interval, remaining_time))
            
        raise TimeoutError(f"等待任务完成超时，已等待{max_wait_time}秒")

    def train_voice(self, 
                  file_path: str, 
                  text_id: int = DEFAULT_TEXT_ID,
                  text_seg_id: int = 1,
                  task_name: str = None,
                  gender: int = 1,
                  wait: bool = True) -> Dict:
        """
        一站式训练语音
        
        Args:
            file_path: 音频文件路径
            text_id: 文本集ID
            text_seg_id: 文本段落ID
            task_name: 任务名称
            gender: 性别 (1:男, 2:女)
            wait: 是否等待训练完成
            
        Returns:
            训练结果
        """
        # 创建任务
        self.create_task(task_name=task_name, gender=gender)
        
        # 添加音频
        self.add_audio_from_file(file_path, text_id, text_seg_id)
        
        # 提交任务
        self.submit_task()
        
        # 等待完成
        if wait:
            return self.wait_for_completion()
            
        return {"task_id": self.task_id, "status": "submitted"}


def print_training_texts(trainer: VoiceTrainer):
    """打印可用的训练文本列表"""
    texts = trainer.get_training_texts()
    print("\n-----可用的训练文本列表-----")
    for text in texts:
        print(f"文本ID: {text['segId']}")
        print(f"文本内容: {text['segText']}")
        print("-" * 30)


if __name__ == "__main__":
    # 初始化训练器
    trainer = VoiceTrainer()
    
    # 打印可用的训练文本列表
    print_training_texts(trainer)
    
    # 从环境变量或配置获取音频文件路径
    audio_path = os.getenv("AUDIO_FILE", os.path.join(AUDIO_FILE_PATH, "origin_audio.wav"))
    
    # 开始训练过程
    try:
        print("\n开始训练过程...")
        result = trainer.train_voice(
            file_path=audio_path,
            text_id=DEFAULT_TEXT_ID,
            text_seg_id=1,
            gender=1,  # 1为男声，2为女声
            wait=True
        )
        
        print("\n训练成功！")
        print(f"音库ID: {result['assetId']}")
        
    except Exception as e:
        print(f"\n训练过程出错: {e}") 