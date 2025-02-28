# -*- coding: utf-8 -*-
# @Time : 2025/2/18 下午12:19
# @Author : renjiajia
import logging
from logging.handlers import RotatingFileHandler
import sys


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 控制台Handler，确保使用UTF-8编码
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console_stream = sys.stdout
    console_stream.reconfigure(encoding="utf-8")  # 让sys.stdout用UTF-8编码
    console.setStream(console_stream)

    # 文件Handler，确保使用UTF-8编码
    file_handler = RotatingFileHandler(
        'app.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'  # 显式指定 UTF-8 编码
    )
    file_handler.setLevel(logging.DEBUG)

    # 格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    console.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger(__name__)