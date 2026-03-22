# -*- coding: utf-8 -*-
"""
日志工具 - 同时输出到文件和控制台
"""
import os
import sys
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logger(name: str = "shengtu2", level: int = logging.INFO) -> logging.Logger:
    """设置并返回logger"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s:%(funcName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出
    try:
        from utils.path_manager import pm
        log_dir = pm.log_dir()
    except Exception:
        log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"shengtu2_{datetime.now():%Y%m%d}.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# 全局logger
logger = setup_logger()
