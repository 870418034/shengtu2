# -*- coding: utf-8 -*-
"""
图像处理工具 - OpenCV + Pillow + rembg
"""
import os
import cv2
import numpy as np
from io import BytesIO
from typing import Tuple, Optional, List
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from datetime import datetime

from utils.path_manager import pm
from utils.logger import logger


def load_image(path: str) -> Image.Image:
    """加载图片"""
    return Image.open(path).convert("RGB")


def save_image(img: Image.Image, directory: str, prefix: str = "img",
               suffix: str = "") -> str:
    """保存图片，自动生成带时间戳的文件名"""
    pm.safe_path(directory)
    os.makedirs(directory, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = f"{prefix}_{timestamp}{suffix}.png"
    filepath = os.path.join(directory, filename)
    img.save(filepath, "PNG")
    return filepath


def remove_background(img: Image.Image) -> Image.Image:
    """一键抠图 - 使用rembg"""
    try:
        from rembg import remove
        result = remove(img)
        return result
    except ImportError:
        logger.error("rembg未安装，请执行: pip install rembg")
        raise


def batch_remove_background(input_dir: str, output_dir: str,
                            callback=None) -> List[str]:
    """批量抠图"""
    pm.safe_path(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    from rembg import remove
    results = []
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
    files = [f for f in os.listdir(input_dir)
             if os.path.splitext(f)[1].lower() in exts]

    for i, filename in enumerate(files):
        try:
            img = Image.open(os.path.join(input_dir, filename)).convert("RGBA")
            result = remove(img)
            out_path = os.path.join(output_dir, f"nobg_{filename}")
            result.save(out_path, "PNG")
            results.append(out_path)
            if callback:
                callback(i + 1, len(files), filename)
        except Exception as e:
            logger.error(f"抠图失败 {filename}: {e}")

    return results


def replace_background(img: Image.Image, bg_type: str = "white",
                       bg_color: Tuple = (255, 255, 255),
                       bg_image_path: str = "") -> Image.Image:
    """
    背景替换
    bg_type: white / black / gray / custom / gradient / image
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    w, h = img.size

    if bg_type == "white":
        bg = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    elif bg_type == "black":
        bg = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    elif bg_type == "gray":
        bg = Image.new("RGBA", (w, h), (128, 128, 128, 255))
    elif bg_type == "custom":
        bg = Image.new("RGBA", (w, h), (*bg_color, 255))
    elif bg_type == "gradient":
        bg = create_gradient_bg(w, h, bg_color)
    elif bg_type == "image" and bg_image_path:
        bg = Image.open(bg_image_path).convert("RGBA").resize((w, h))
    else:
        bg = Image.new("RGBA", (w, h), (255, 255, 255, 255))

    composite = Image.alpha_composite(bg, img)
    return composite.convert("RGB")


def create_gradient_bg(width: int, height: int,
                       color: Tuple = (200, 200, 200)) -> Image.Image:
    """创建渐变背景"""
    bg = Image.new("RGBA", (width, height))
    for y in range(height):
        ratio = y / height
        r = int(color[0] * (1 - ratio * 0.3))
        g = int(color[1] * (1 - ratio * 0.3))
        b = int(color[2] * (1 - ratio * 0.3))
        for x in range(width):
            bg.putpixel((x, y), (r, g, b, 255))
    return bg


def add_shadow(img: Image.Image, offset: Tuple[int, int] = (10, 10),
               blur_radius: int = 15, opacity: int = 100) -> Image.Image:
    """添加自然投影"""
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # 创建阴影层
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow_draw = Image.new("RGBA", img.size, (0, 0, 0, opacity))
    # 用原图的alpha通道做阴影形状
    shadow.paste(shadow_draw, mask=img.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))

    # 创建合成画布（需要更大以容纳偏移）
    canvas_w = img.width + abs(offset[0]) + blur_radius * 2
    canvas_h = img.height + abs(offset[1]) + blur_radius * 2
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # 放置阴影
    shadow_x = blur_radius + max(0, offset[0])
    shadow_y = blur_radius + max(0, offset[1])
    canvas.paste(shadow, (shadow_x, shadow_y))

    # 放置原图
    img_x = blur_radius + max(0, -offset[0])
    img_y = blur_radius + max(0, -offset[1])
    canvas.paste(img, (img_x, img_y), img)

    return canvas


def add_reflection(img: Image.Image, ratio: float = 0.3,
                   fade: bool = True) -> Image.Image:
    """添加镜面倒影"""
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    w, h = img.size
    reflect_h = int(h * ratio)

    # 截取底部区域并翻转
    bottom = img.crop((0, h - reflect_h, w, h))
    reflected = bottom.transpose(Image.FLIP_TOP_BOTTOM)

    if fade:
        # 渐变透明
        for y in range(reflect_h):
            alpha = int(255 * (1 - y / reflect_h) * 0.4)
            for x in range(w):
                r, g, b, _ = reflected.getpixel((x, y))
                reflected.putpixel((x, y), (r, g, b, alpha))

    # 合成
    canvas = Image.new("RGBA", (w, h + reflect_h), (0, 0, 0, 0))
    canvas.paste(img, (0, 0))
    canvas.paste(reflected, (0, h))

    return canvas


def image_similarity(img1: Image.Image, img2: Image.Image) -> float:
    """
    计算两张图片的相似度（SSIM）
    返回 0-100 的相似度百分比
    """
    try:
        from skimage.metrics import structural_similarity as ssim

        # 统一尺寸
        size = (256, 256)
        i1 = np.array(img1.convert("RGB").resize(size))
        i2 = np.array(img2.convert("RGB").resize(size))

        score = ssim(i1, i2, channel_axis=2)
        return round(score * 100, 2)
    except ImportError:
        # 降级到直方图比较
        h1 = img1.convert("RGB").resize((64, 64))
        h2 = img2.convert("RGB").resize((64, 64))
        hist1 = np.array(h1).flatten()
        hist2 = np.array(h2).flatten()
        corr = np.corrcoef(hist1, hist2)[0, 1]
        return round(corr * 100, 2)


def phash(img: Image.Image, hash_size: int = 16) -> str:
    """感知哈希（pHash）"""
    try:
        import imagehash
        h = imagehash.phash(img, hash_size=hash_size)
        return str(h)
    except ImportError:
        # 简单实现
        gray = img.convert("L").resize((hash_size, hash_size))
        pixels = list(gray.getdata())
        avg = sum(pixels) / len(pixels)
        bits = "".join("1" if p > avg else "0" for p in pixels)
        return bits


def is_blurry(img: Image.Image, threshold: float = 100.0) -> bool:
    """检测图片是否模糊"""
    gray = np.array(img.convert("L"))
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian_var < threshold


def resize_image(img: Image.Image, width: int, height: int) -> Image.Image:
    """等比缩放图片"""
    img.thumbnail((width, height), Image.LANCZOS)
    return img


def upscale_image(img: Image.Image, scale: int = 2) -> Image.Image:
    """超分辨率放大（简单实现，实际应用中调用ESRGAN等）"""
    w, h = img.size
    return img.resize((w * scale, h * scale), Image.LANCZOS)


def create_thumbnail_grid(images: List[Image.Image], cols: int = 4,
                          thumb_size: Tuple[int, int] = (200, 200),
                          padding: int = 10) -> Image.Image:
    """创建缩略图网格"""
    rows = (len(images) + cols - 1) // cols
    grid_w = cols * thumb_size[0] + (cols + 1) * padding
    grid_h = rows * thumb_size[1] + (rows + 1) * padding
    grid = Image.new("RGB", (grid_w, grid_h), (26, 26, 26))

    for idx, img in enumerate(images):
        row = idx // cols
        col = idx % cols
        thumb = img.copy()
        thumb.thumbnail(thumb_size, Image.LANCZOS)
        x = padding + col * (thumb_size[0] + padding)
        y = padding + row * (thumb_size[1] + padding)
        # 居中放置
        tx = x + (thumb_size[0] - thumb.width) // 2
        ty = y + (thumb_size[1] - thumb.height) // 2
        grid.paste(thumb, (tx, ty))

    return grid


def img_to_base64(img: Image.Image, format: str = "PNG") -> str:
    """图片转base64"""
    buffer = BytesIO()
    img.save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode()


def base64_to_img(b64_str: str) -> Image.Image:
    """base64转图片"""
    import base64
    data = base64.b64decode(b64_str)
    return Image.open(BytesIO(data)).convert("RGB")
