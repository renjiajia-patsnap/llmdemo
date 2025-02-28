import base64
import urllib
from urllib import parse
import requests
import logging
import time
import hmac
import hashlib
from dotenv import load_dotenv
from typing import Optional
import os

load_dotenv()


def send_alert(secret: str, webhook: str, content: str,msgtype: str = 'markdown') -> None:
    timestamp = str(round(time.time() * 1000))
    secret_enc = secret.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = parse.quote_plus(base64.b64encode(hmac_code))

    webhook = f'{webhook}&timestamp={timestamp}&sign={sign}'
    headers = {'Content-Type': 'application/json;charset=utf-8'}
    data = {
        "msgtype": msgtype,
        "markdown": {
            "title": "用例统计",
            "text": content
        }
    }
    response = requests.post(webhook, headers=headers, json=data)
    if not response.ok:
        logging.error(f"Failed to send alert: {response.text}")

if __name__ == '__main__':
    secret = os.getenv('dd_secret')
    webhook = os.getenv('dd_webhook')
    msgtype = 'markdown'
    # 从data/casecount.md文件中读取内容发送到钉钉
    with open('data/casecount.md', 'r', encoding='utf-8') as f:
        content = f.read()
    send_alert(secret, webhook,content)