# -*- coding: utf-8 -*-
"""
路径管理器 - 确保所有路径在F盘，禁止写入C盘
"""
import os
import sys
import platform

# ==================== 硬编码根目录 ====================
ROOT_DIR = r"F:\shengtu2"
IS_WINDOWS = platform.system() == "Windows"


class PathManager:
    """路径管理单例，所有模块通过它获取路径"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._root = ROOT_DIR
            self._dirs = self._define_dirs()
            self._initialized = True

    def _define_dirs(self) -> dict:
        """定义所有子目录"""
        return {
            "models": os.path.join(self._root, "models"),
            "models_sd": os.path.join(self._root, "models", "stable-diffusion"),
            "models_lora": os.path.join(self._root, "models", "lora"),
            "models_vae": os.path.join(self._root, "models", "vae"),
            "models_controlnet": os.path.join(self._root, "models", "controlnet"),
            "models_clip": os.path.join(self._root, "models", "clip"),
            "models_upscaler": os.path.join(self._root, "models", "upscaler"),
            "datasets": os.path.join(self._root, "datasets"),
            "datasets_raw": os.path.join(self._root, "datasets", "raw"),
            "datasets_tagged": os.path.join(self._root, "datasets", "tagged"),
            "outputs": os.path.join(self._root, "outputs"),
            "outputs_designs": os.path.join(self._root, "outputs", "designs"),
            "outputs_variants": os.path.join(self._root, "outputs", "variants"),
            "outputs_batch": os.path.join(self._root, "outputs", "batch"),
            "outputs_exports": os.path.join(self._root, "outputs", "exports"),
            "crawled": os.path.join(self._root, "crawled"),
            "database": os.path.join(self._root, "database"),
            "config": os.path.join(self._root, "config"),
            "logs": os.path.join(self._root, "logs"),
            "cache": os.path.join(self._root, "cache"),
            "backups": os.path.join(self._root, "backups"),
            "project": os.path.join(self._root, "project"),
        }

    @property
    def root(self) -> str:
        return self._root

    def get(self, key: str) -> str:
        if key not in self._dirs:
            raise KeyError(f"未知的路径键: {key}")
        return self._dirs[key]

    def db_path(self) -> str:
        return os.path.join(self._root, "database", "designs.db")

    def config_path(self) -> str:
        return os.path.join(self._root, "config", "settings.yaml")

    def prompt_templates_path(self) -> str:
        return os.path.join(self._root, "config", "prompt_templates.yaml")

    def log_dir(self) -> str:
        return os.path.join(self._root, "logs")

    def ensure_dirs(self):
        for key, path in self._dirs.items():
            os.makedirs(path, exist_ok=True)
        os.makedirs(os.path.join(self._root, "database"), exist_ok=True)

    def get_dataset_dir(self, project_name: str, dtype: str = "raw") -> str:
        if dtype == "raw":
            base = self.get("datasets_raw")
        elif dtype == "tagged":
            base = self.get("datasets_tagged")
        else:
            raise ValueError(f"未知的数据集类型: {dtype}")
        path = os.path.join(base, project_name)
        os.makedirs(path, exist_ok=True)
        return path


# ==================== 全局实例 ====================
pm = PathManager()


def init_paths():
    pm.ensure_dirs()
    return pm
