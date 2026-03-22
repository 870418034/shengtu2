# -*- coding: utf-8 -*-
"""
配置管理器 - YAML配置文件读写，支持运行时修改
"""
import os
import yaml
import copy


class ConfigManager:
    """配置管理单例"""

    _instance = None
    _initialized = False

    # 默认配置
    DEFAULT_CONFIG = {
        "app": {
            "name": "翡翠珠宝镶嵌托设计AI辅助系统",
            "version": "1.0.0",
            "theme": "dark",
            "language": "zh_CN",
        },
        "sd_webui": {
            "api_url": "http://127.0.0.1:7860",
            "api_mode": "a1111",
            "timeout": 120,
            "default_sampler": "DPM++ 2M Karras",
            "default_steps": 30,
            "default_cfg_scale": 7.0,
            "default_width": 512,
            "default_height": 512,
            "default_batch_size": 1,
            "hires_fix_enabled": False,
            "hires_fix_upscaler": "4x-UltraSharp",
            "hires_fix_scale": 2.0,
            "adetailer_enabled": False,
        },
        "mimo_api": {
            "api_key": "",
            "base_url": "https://api.xiaomimimo.com/v1",
            "model": "mimo-v2-flash",
            "timeout": 60,
            "max_retries": 3,
        },
        "available_models": {
            "sd_models": [],
            "sd_loras": [],
            "mimo_models": [
                {"id": "mimo-v2-flash", "name": "MiMo-V2-Flash (免费)", "free": True},
                {"id": "mimo-v2-lite", "name": "MiMo-V2-Lite", "free": False},
            ],
        },
        "training": {
            "default_network_type": "LoRA",
            "default_rank": 32,
            "default_learning_rate_unet": 0.0001,
            "default_learning_rate_te": 0.00005,
            "default_epochs": 10,
            "default_batch_size": 1,
            "default_resolution": 512,
            "default_optimizer": "AdamW8bit",
            "default_mixed_precision": "fp16",
            "save_format": "safetensors",
            "save_every_n_steps": 500,
            "preview_every_n_steps": 100,
            "kohya_ss_path": "",
        },
        "crawler": {
            "concurrent_requests": 3,
            "request_interval_min": 2.0,
            "request_interval_max": 5.0,
            "min_resolution_width": 800,
            "min_resolution_height": 600,
            "similarity_threshold": 60,
            "max_images_per_site": 100,
            "proxy_enabled": False,
            "proxy_type": "http",
            "proxy_url": "",
            "user_agent_rotation": True,
        },
        "gallery": {
            "thumbnail_size": 256,
            "default_sort": "time_desc",
        },
        "batch": {
            "max_concurrent": 4,
        },
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._config = {}
        self._config_path = self._find_config_path()
        self._load()

    def _find_config_path(self) -> str:
        """查找配置文件路径"""
        # 优先使用环境变量
        env_path = os.environ.get("SHENGTU2_CONFIG")
        if env_path and os.path.exists(env_path):
            return env_path

        # 尝试多个常见位置
        candidates = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "settings.yaml"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "default_settings.yaml"),
            os.path.join("F:\\shengtu2", "config", "settings.yaml"),
        ]

        for path in candidates:
            if os.path.exists(path):
                return path

        # 默认路径
        default = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "settings.yaml")
        os.makedirs(os.path.dirname(default), exist_ok=True)
        return default

    def _load(self):
        """加载配置文件"""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f) or {}
                # 用默认值填充缺失的键
                self._config = self._merge_defaults(self.DEFAULT_CONFIG, loaded)
            except Exception as e:
                print(f"配置加载失败，使用默认配置: {e}")
                self._config = copy.deepcopy(self.DEFAULT_CONFIG)
        else:
            self._config = copy.deepcopy(self.DEFAULT_CONFIG)

    def _merge_defaults(self, defaults: dict, overrides: dict) -> dict:
        """递归合并默认值和覆盖值"""
        result = copy.deepcopy(defaults)
        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_defaults(result[key], value)
            else:
                result[key] = value
        return result

    def save(self):
        """保存配置到文件"""
        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        except Exception as e:
            print(f"配置保存失败: {e}")

    def get(self, section: str, key: str = None, default=None):
        """获取配置值"""
        section_data = self._config.get(section, {})
        if key is None:
            return section_data
        if isinstance(section_data, dict):
            return section_data.get(key, default)
        return default

    def set(self, section: str, key: str, value):
        """设置配置值"""
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value

    def get_section(self, section: str) -> dict:
        """获取整个配置节"""
        return self._config.get(section, {})

    def reload(self):
        """重新加载配置"""
        self._load()

    @property
    def config_path(self) -> str:
        return self._config_path


# 全局实例
config = ConfigManager()
