# -*- coding: utf-8 -*-
"""
图片工具 - 保存/加载图片
"""
import os
from datetime import datetime
from PIL import Image


def save_image(img, save_dir, prefix="design"):
    """保存图片到指定目录"""
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}.png"
    filepath = os.path.join(save_dir, filename)
    if isinstance(img, Image.Image):
        img.save(filepath, "PNG")
    return filepath


def load_image(path):
    """加载图片"""
    return Image.open(path).convert("RGB")
