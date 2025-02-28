import base64
import urllib
from urllib import parse
import requests
import logging
import time
import hmac
import hashlib

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
            "text": content
        }
    }
    response = requests.post(webhook, headers=headers, json=data)
    if not response.ok:
        logging.error(f"Failed to send alert: {response.text}")

if __name__ == '__main__':
    secret = 'SECcbc9a1341b1e1116e15a4fdae35a2363dbe247b4685b8307cc073d3a7a66dc5e'
    webhook = 'https://oapi.dingtalk.com/robot/send?access_token=b587ce9ea14a5ddc58cb687896655f32e789651ecda8d0276229f372788cb9b8'
    msgtype = 'markdown'
    # 从data/casecount.md文件中读取内容发送到钉钉
    with open('data/casecount.md', 'r', encoding='utf-8') as f:
        content = f.read()
    send_alert(secret, webhook,content)