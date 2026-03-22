# -*- coding: utf-8 -*-
"""
设置对话框 - 支持模型选择、一键下载、MiMo API 配置
"""
import os
import json
import requests
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
    QTabWidget, QFileDialog, QMessageBox, QScrollArea, QWidget, QProgressBar,
    QListWidget, QListWidgetItem, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal, QSize

from core.config_manager import config
from core.sd_api import sd_api
from core.mimo_api import mimo_api
from utils.path_manager import pm
from utils.logger import logger


class ModelListThread(QThread):
    """异步获取 SD 模型列表"""
    finished = Signal(list, list, list)  # sd_models, loras, samplers

    def run(self):
        models = sd_api.get_models()
        loras = sd_api.get_loras()
        samplers = sd_api.get_samplers()
        self.finished.emit(models, loras, samplers)


class ModelDownloadThread(QThread):
    """下载模型文件"""
    progress = Signal(int, int)  # downloaded_bytes, total_bytes
    finished = Signal(str, bool)  # filename, success
    error = Signal(str)

    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path

    def run(self):
        try:
            resp = requests.get(self.url, stream=True, timeout=30)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(self.save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    self.progress.emit(downloaded, total)
            self.finished.emit(os.path.basename(self.save_path), True)
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(os.path.basename(self.save_path), False)


class MimoTestThread(QThread):
    """异步测试 MiMo 连接"""
    finished = Signal(dict)

    def run(self):
        result = mimo_api.test_connection()
        self.finished.emit(result)


# 推荐的珠宝设计模型
RECOMMENDED_MODELS = [
    {
        "name": "RealVisXL V5.0",
        "filename": "RealVisXL_V5.0.safetensors",
        "url": "https://huggingface.co/SG161222/RealVisXL_V5.0/resolve/main/RealVisXL_V5.0.safetensors",
        "description": "XL写实模型，适合珠宝摄影风格",
        "type": "sd",
        "size_gb": 6.5,
    },
    {
        "name": "dreamshaperXL_v21Turbo",
        "filename": "dreamshaperXL_v21Turbo.safetensors",
        "url": "https://huggingface.co/Lykon/DreamShaper/resolve/main/DreamShaper%20XL%20V2.1%20Turbo.safetensors",
        "description": "XL Turbo 模型，速度快质量好",
        "type": "sd",
        "size_gb": 6.5,
    },
    {
        "name": "juggernautXL_v9",
        "filename": "juggernautXL_v9.safetensors",
        "url": "https://huggingface.co/RunDiffusion/Juggernaut-XL-v9/resolve/main/Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors",
        "description": "全能型 XL 模型，摄影级质量",
        "type": "sd",
        "size_gb": 6.5,
    },
    {
        "name": "sd_xl_base_1.0",
        "filename": "sd_xl_base_1.0.safetensors",
        "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors",
        "description": "SDXL 官方基础模型",
        "type": "sd",
        "size_gb": 6.5,
    },
    {
        "name": "v1-5-pruned-emaonly",
        "filename": "v1-5-pruned-emaonly.safetensors",
        "url": "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors",
        "description": "SD 1.5 基础模型，兼容性最好",
        "type": "sd",
        "size_gb": 4.0,
    },
]

RECOMMENDED_LORAS = [
    {
        "name": "珠宝摄影 LoRA (示例)",
        "filename": "",
        "url": "",
        "description": "请自行训练或从 Civitai 下载珠宝设计 LoRA",
        "type": "lora",
        "size_gb": 0,
    },
]


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumSize(750, 550)
        self._download_threads = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        tabs.addTab(self._create_sd_tab(), "🎨 SD WebUI")
        tabs.addTab(self._create_mimo_tab(), "🤖 MiMo API")
        tabs.addTab(self._create_model_tab(), "📦 模型管理")
        tabs.addTab(self._create_train_tab(), "🧠 训练")
        tabs.addTab(self._create_crawler_tab(), "🕷️ 爬虫")
        tabs.addTab(self._create_general_tab(), "⚙️ 通用")

        layout.addWidget(tabs)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("💾 保存设置")
        save_btn.setProperty("gold", True)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    # ==================== SD WebUI 设置 ====================

    def _create_sd_tab(self) -> QWidget:
        panel = QWidget()
        layout = QGridLayout(panel)

        layout.addWidget(QLabel("API模式:"), 0, 0)
        self.sd_mode = QComboBox()
        self.sd_mode.addItems(["a1111", "comfyui"])
        self.sd_mode.setCurrentText(config.get("sd_webui", "api_mode", default="a1111"))
        layout.addWidget(self.sd_mode, 0, 1)

        layout.addWidget(QLabel("API地址:"), 1, 0)
        self.sd_url = QLineEdit(config.get("sd_webui", "api_url", default="http://127.0.0.1:7860"))
        self.sd_url.setPlaceholderText("http://127.0.0.1:7860")
        layout.addWidget(self.sd_url, 1, 1)

        layout.addWidget(QLabel("超时(秒):"), 2, 0)
        self.sd_timeout = QSpinBox()
        self.sd_timeout.setRange(10, 600)
        self.sd_timeout.setValue(config.get("sd_webui", "timeout", default=120))
        layout.addWidget(self.sd_timeout, 2, 1)

        layout.addWidget(QLabel("默认采样器:"), 3, 0)
        self.sd_sampler = QComboBox()
        self.sd_sampler.addItems([
            "DPM++ 2M Karras", "DPM++ SDE Karras", "Euler a", "Euler",
            "DDIM", "UniPC", "LMS", "Heun"
        ])
        self.sd_sampler.setCurrentText(config.get("sd_webui", "default_sampler", default="DPM++ 2M Karras"))
        layout.addWidget(self.sd_sampler, 3, 1)

        layout.addWidget(QLabel("默认步数:"), 4, 0)
        self.sd_steps = QSpinBox()
        self.sd_steps.setRange(1, 150)
        self.sd_steps.setValue(config.get("sd_webui", "default_steps", default=30))
        layout.addWidget(self.sd_steps, 4, 1)

        layout.addWidget(QLabel("默认CFG:"), 5, 0)
        self.sd_cfg = QDoubleSpinBox()
        self.sd_cfg.setRange(1, 30)
        self.sd_cfg.setSingleStep(0.5)
        self.sd_cfg.setValue(config.get("sd_webui", "default_cfg_scale", default=7.0))
        layout.addWidget(self.sd_cfg, 5, 1)

        # Hi-res Fix
        self.hires_check = QCheckBox("启用高清修复 (Hires.fix)")
        self.hires_check.setChecked(config.get("sd_webui", "hires_fix_enabled", default=False))
        layout.addWidget(self.hires_check, 6, 0, 1, 2)

        layout.addWidget(QLabel("放大倍率:"), 7, 0)
        self.hires_scale = QDoubleSpinBox()
        self.hires_scale.setRange(1.0, 4.0)
        self.hires_scale.setSingleStep(0.25)
        self.hires_scale.setValue(config.get("sd_webui", "hires_fix_scale", default=2.0))
        layout.addWidget(self.hires_scale, 7, 1)

        # 测试按钮
        test_btn = QPushButton("🔗 测试 SD 连接")
        test_btn.clicked.connect(self._test_sd)
        layout.addWidget(test_btn, 8, 0, 1, 2)

        self.sd_test_result = QLabel("")
        layout.addWidget(self.sd_test_result, 9, 0, 1, 2)

        # 刷新模型列表按钮
        refresh_btn = QPushButton("🔄 刷新模型/LoRA列表")
        refresh_btn.clicked.connect(self._refresh_sd_models)
        layout.addWidget(refresh_btn, 10, 0, 1, 2)

        self.refresh_result = QLabel("")
        layout.addWidget(self.refresh_result, 11, 0, 1, 2)

        return panel

    def _test_sd(self):
        # 更新配置再测试
        config.set("sd_webui", "api_url", self.sd_url.text())
        config.set("sd_webui", "api_mode", self.sd_mode.currentText())
        result = sd_api.check_connection()
        if result["connected"]:
            self.sd_test_result.setText(f"✅ 连接成功 - 模式: {result.get('mode', '')}")
            self.sd_test_result.setStyleSheet("color: #4caf50;")
        else:
            self.sd_test_result.setText(f"❌ {result.get('error', '连接失败')}")
            self.sd_test_result.setStyleSheet("color: #f44336;")

    def _refresh_sd_models(self):
        """刷新 SD 模型列表并保存到配置"""
        config.set("sd_webui", "api_url", self.sd_url.text())
        self.refresh_result.setText("正在获取模型列表...")
        self.refresh_result.setStyleSheet("color: #aaa;")

        self._model_list_thread = ModelListThread()
        self._model_list_thread.finished.connect(self._on_models_loaded)
        self._model_list_thread.start()

    def _on_models_loaded(self, models, loras, samplers):
        """模型列表加载完成"""
        # 保存到配置
        model_list = [m.get("model_name", m.get("title", "")) for m in models]
        lora_list = [l.get("alias", l.get("name", "")) for l in loras]
        sampler_list = [s.get("name", "") for s in samplers]

        config.set("available_models", "sd_models", model_list)
        config.set("available_models", "sd_loras", lora_list)

        msg = f"✅ 获取成功: {len(model_list)} 个模型, {len(lora_list)} 个 LoRA"
        self.refresh_result.setText(msg)
        self.refresh_result.setStyleSheet("color: #4caf50;")

    # ==================== MiMo API 设置 ====================

    def _create_mimo_tab(self) -> QWidget:
        panel = QWidget()
        layout = QGridLayout(panel)

        layout.addWidget(QLabel("API Key:"), 0, 0)
        self.mimo_key = QLineEdit(config.get("mimo_api", "api_key", default=""))
        self.mimo_key.setEchoMode(QLineEdit.Password)
        self.mimo_key.setPlaceholderText("在 platform.xiaomimimo.com 获取")
        layout.addWidget(self.mimo_key, 0, 1)

        show_key_btn = QPushButton("👁")
        show_key_btn.setFixedWidth(35)
        show_key_btn.setToolTip("显示/隐藏")
        show_key_btn.clicked.connect(lambda: self.mimo_key.setEchoMode(
            QLineEdit.Normal if self.mimo_key.echoMode() == QLineEdit.Password else QLineEdit.Password
        ))
        layout.addWidget(show_key_btn, 0, 2)

        layout.addWidget(QLabel("Base URL:"), 1, 0)
        self.mimo_url = QLineEdit(config.get("mimo_api", "base_url", default="https://api.xiaomimimo.com/v1"))
        self.mimo_url.setPlaceholderText("https://api.xiaomimimo.com/v1")
        layout.addWidget(self.mimo_url, 1, 1, 1, 2)

        layout.addWidget(QLabel("模型:"), 2, 0)
        self.mimo_model = QComboBox()
        self.mimo_model.setEditable(True)
        # 填充可用模型
        for model in mimo_api.get_available_models():
            label = f"{model['name']} ({model['id']})" if model.get("free") else f"{model['name']} ({model['id']})"
            self.mimo_model.addItem(label, model["id"])
        # 选中当前配置的模型
        current_model = config.get("mimo_api", "model", default="mimo-v2-flash")
        idx = self.mimo_model.findData(current_model)
        if idx >= 0:
            self.mimo_model.setCurrentIndex(idx)
        else:
            self.mimo_model.setEditText(current_model)
        layout.addWidget(self.mimo_model, 2, 1, 1, 2)

        layout.addWidget(QLabel("超时(秒):"), 3, 0)
        self.mimo_timeout = QSpinBox()
        self.mimo_timeout.setRange(10, 300)
        self.mimo_timeout.setValue(config.get("mimo_api", "timeout", default=60))
        layout.addWidget(self.mimo_timeout, 3, 1)

        layout.addWidget(QLabel("最大重试:"), 4, 0)
        self.mimo_retries = QSpinBox()
        self.mimo_retries.setRange(1, 10)
        self.mimo_retries.setValue(config.get("mimo_api", "max_retries", default=3))
        layout.addWidget(self.mimo_retries, 4, 1)

        # 测试连接
        test_btn = QPushButton("🔗 测试 MiMo 连接")
        test_btn.clicked.connect(self._test_mimo)
        layout.addWidget(test_btn, 5, 0, 1, 3)

        self.mimo_test_result = QLabel("")
        layout.addWidget(self.mimo_test_result, 6, 0, 1, 3)

        # 帮助信息
        help_label = QLabel(
            "📌 获取 API Key: 登录 platform.xiaomimimo.com → 控制台 → API Keys\n"
            "📌 MiMo-V2-Flash 限时免费，推荐使用\n"
            "📌 Base URL 格式: https://api.xiaomimimo.com/v1 (OpenAI 兼容)\n"
            "📌 也可以使用 Anthropic 兼容: https://api.xiaomimimo.com/anthropic"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #888; font-size: 11px; padding: 8px; "
                                 "background-color: #252525; border-radius: 4px;")
        layout.addWidget(help_label, 7, 0, 1, 3)

        layout.setRowStretch(8, 1)
        return panel

    def _test_mimo(self):
        """测试 MiMo API 连接"""
        # 先保存当前填写的配置
        config.set("mimo_api", "api_key", self.mimo_key.text())
        config.set("mimo_api", "base_url", self.mimo_url.text())
        model_data = self.mimo_model.currentData()
        config.set("mimo_api", "model", model_data if model_data else self.mimo_model.currentText())
        config.set("mimo_api", "timeout", self.mimo_timeout.value())
        config.set("mimo_api", "max_retries", self.mimo_retries.value())

        self.mimo_test_result.setText("⏳ 正在测试连接...")
        self.mimo_test_result.setStyleSheet("color: #aaa;")

        self._mimo_test_thread = MimoTestThread()
        self._mimo_test_thread.finished.connect(self._on_mimo_tested)
        self._mimo_test_thread.start()

    def _on_mimo_tested(self, result):
        if result["connected"]:
            model = result.get("model", "")
            resp = result.get("response", "")
            self.mimo_test_result.setText(f"✅ 连接成功 - 模型: {model}\n回复: {resp}")
            self.mimo_test_result.setStyleSheet("color: #4caf50;")
        else:
            self.mimo_test_result.setText(f"❌ {result.get('error', '连接失败')}")
            self.mimo_test_result.setStyleSheet("color: #f44336;")

    # ==================== 模型管理 ====================

    def _create_model_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 说明
        info_label = QLabel(
            "💡 推荐模型均为珠宝设计/写实摄影风格优化模型\n"
            "点击「下载」按钮自动下载到 SD models 目录\n"
            "下载完成后需在 SD WebUI 中刷新模型列表"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #c9a84c; padding: 8px; background-color: #252525; border-radius: 4px;")
        layout.addWidget(info_label)

        # 推荐模型列表
        model_group = QGroupBox("推荐 SD 模型")
        model_layout = QVBoxLayout(model_group)

        for m in RECOMMENDED_MODELS:
            row = QHBoxLayout()

            name_lbl = QLabel(f"<b>{m['name']}</b>")
            name_lbl.setFixedWidth(200)
            row.addWidget(name_lbl)

            desc_lbl = QLabel(f"{m['description']} ({m['size_gb']}GB)")
            desc_lbl.setStyleSheet("color: #888;")
            row.addWidget(desc_lbl, 1)

            dl_btn = QPushButton("⬇ 下载")
            dl_btn.setProperty("secondary", True)
            dl_btn.setFixedWidth(80)
            dl_btn.setProperty("model_info", m)
            dl_btn.clicked.connect(lambda checked, btn=dl_btn, info=m: self._download_model(btn, info))
            row.addWidget(dl_btn)

            status_lbl = QLabel("")
            status_lbl.setFixedWidth(120)
            dl_btn.setProperty("status_label", status_lbl)
            row.addWidget(status_lbl)

            model_layout.addLayout(row)

        layout.addWidget(model_group)

        # LoRA 提示
        lora_group = QGroupBox("LoRA 模型")
        lora_layout = QVBoxLayout(lora_group)
        lora_info = QLabel(
            "LoRA 模型建议自行训练（使用训练标签页）\n"
            "也可从 Civitai.com 搜索珠宝设计 LoRA 下载\n"
            "下载后放入 SD WebUI 的 models/Lora 目录"
        )
        lora_info.setWordWrap(True)
        lora_layout.addWidget(lora_info)

        # 手动导入 LoRA
        import_row = QHBoxLayout()
        import_btn = QPushButton("📂 手动导入 LoRA 文件")
        import_btn.clicked.connect(self._import_lora)
        import_row.addWidget(import_btn)
        self.import_result = QLabel("")
        import_row.addWidget(self.import_result, 1)
        lora_layout.addLayout(import_row)

        layout.addWidget(lora_group)

        # 本地模型查看
        local_group = QGroupBox("本地模型")
        local_layout = QVBoxLayout(local_group)

        sd_dir = config.get("sd_webui", "api_url", default="http://127.0.0.1:7860")
        local_info = QLabel(f"SD 模型目录: 请在 SD WebUI 的 models/Stable-diffusion 目录查看\n"
                           f"LoRA 目录: models/Lora")
        local_layout.addWidget(local_info)

        browse_btn = QPushButton("📁 打开本地模型目录")
        browse_btn.setProperty("secondary", True)
        browse_btn.clicked.connect(self._browse_models)
        local_layout.addWidget(browse_btn)

        layout.addWidget(local_group)

        layout.addStretch()
        return panel

    def _download_model(self, btn, info):
        """下载模型"""
        if not info.get("url"):
            self.import_result.setText("⚠️ 该模型需要手动下载")
            return

        # 确定保存路径
        model_dir = os.path.join(pm.get("models_sd"))
        os.makedirs(model_dir, exist_ok=True)
        save_path = os.path.join(model_dir, info["filename"])

        if os.path.exists(save_path):
            status_lbl = btn.property("status_label")
            status_lbl.setText("✅ 已存在")
            status_lbl.setStyleSheet("color: #4caf50;")
            return

        btn.setEnabled(False)
        btn.setText("下载中...")
        status_lbl = btn.property("status_label")
        status_lbl.setText("0%")
        status_lbl.setStyleSheet("color: #aaa;")

        thread = ModelDownloadThread(info["url"], save_path)
        thread.progress.connect(lambda dl, total: self._on_download_progress(btn, dl, total))
        thread.finished.connect(lambda fname, ok: self._on_download_finished(btn, info, ok))
        thread.error.connect(lambda err: self._on_download_error(btn, err))
        self._download_threads.append(thread)
        thread.start()

    def _on_download_progress(self, btn, downloaded, total):
        status_lbl = btn.property("status_label")
        if total > 0:
            pct = int(downloaded / total * 100)
            mb_dl = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            status_lbl.setText(f"{pct}% ({mb_dl:.0f}/{mb_total:.0f}MB)")
        else:
            status_lbl.setText(f"{downloaded / (1024*1024):.0f}MB")

    def _on_download_finished(self, btn, info, success):
        btn.setEnabled(True)
        btn.setText("⬇ 下载")
        status_lbl = btn.property("status_label")
        if success:
            status_lbl.setText("✅ 下载完成")
            status_lbl.setStyleSheet("color: #4caf50;")
        else:
            status_lbl.setText("❌ 下载失败")
            status_lbl.setStyleSheet("color: #f44336;")

    def _on_download_error(self, btn, error):
        status_lbl = btn.property("status_label")
        status_lbl.setText(f"❌ {error[:30]}")
        status_lbl.setStyleSheet("color: #f44336;")
        btn.setEnabled(True)
        btn.setText("⬇ 下载")

    def _import_lora(self):
        """手动导入 LoRA 文件到 SD 目录"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 LoRA 文件", "",
            "模型文件 (*.safetensors *.pt *.ckpt)"
        )
        if not path:
            return

        import shutil
        target_dir = os.path.join(pm.get("models_lora"))
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, os.path.basename(path))

        if os.path.exists(target_path):
            self.import_result.setText(f"⚠️ 文件已存在: {os.path.basename(path)}")
            return

        try:
            shutil.copy2(path, target_path)
            self.import_result.setText(f"✅ 已导入: {os.path.basename(path)}")
            self.import_result.setStyleSheet("color: #4caf50;")
        except Exception as e:
            self.import_result.setText(f"❌ 导入失败: {e}")
            self.import_result.setStyleSheet("color: #f44336;")

    def _browse_models(self):
        """打开本地模型目录"""
        import subprocess
        model_dir = pm.get("models")
        os.makedirs(model_dir, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(model_dir)
            else:
                subprocess.Popen(["xdg-open", model_dir])
        except Exception:
            pass

    # ==================== 训练设置 ====================

    def _create_train_tab(self) -> QWidget:
        panel = QWidget()
        layout = QGridLayout(panel)

        layout.addWidget(QLabel("kohya_ss路径:"), 0, 0)
        kohya_layout = QHBoxLayout()
        self.kohya_path = QLineEdit(config.get("training", "kohya_ss_path", default=""))
        self.kohya_path.setPlaceholderText("kohya_ss 目录路径")
        kohya_layout.addWidget(self.kohya_path)
        kohya_btn = QPushButton("浏览")
        kohya_btn.setProperty("secondary", True)
        kohya_btn.clicked.connect(self._browse_kohya)
        kohya_layout.addWidget(kohya_btn)
        layout.addLayout(kohya_layout, 0, 1)

        layout.addWidget(QLabel("默认Rank:"), 1, 0)
        self.train_rank = QComboBox()
        self.train_rank.addItems(["4", "8", "16", "32", "64", "128", "256"])
        self.train_rank.setCurrentText(str(config.get("training", "default_rank", default=32)))
        layout.addWidget(self.train_rank, 1, 1)

        layout.addWidget(QLabel("默认优化器:"), 2, 0)
        self.train_optimizer = QComboBox()
        self.train_optimizer.addItems(["AdamW8bit", "Prodigy", "Lion", "SGD"])
        self.train_optimizer.setCurrentText(config.get("training", "default_optimizer", default="AdamW8bit"))
        layout.addWidget(self.train_optimizer, 2, 1)

        layout.addWidget(QLabel("混合精度:"), 3, 0)
        self.train_precision = QComboBox()
        self.train_precision.addItems(["fp16", "bf16", "no"])
        self.train_precision.setCurrentText(config.get("training", "default_mixed_precision", default="fp16"))
        layout.addWidget(self.train_precision, 3, 1)

        return panel

    def _browse_kohya(self):
        path = QFileDialog.getExistingDirectory(self, "选择kohya_ss目录")
        if path:
            self.kohya_path.setText(path)

    # ==================== 爬虫设置 ====================

    def _create_crawler_tab(self) -> QWidget:
        panel = QWidget()
        layout = QGridLayout(panel)

        layout.addWidget(QLabel("请求间隔(秒):"), 0, 0)
        interval_layout = QHBoxLayout()
        self.crawl_min = QDoubleSpinBox()
        self.crawl_min.setRange(0.5, 30)
        self.crawl_min.setValue(config.get("crawler", "request_interval_min", default=2.0))
        interval_layout.addWidget(self.crawl_min)
        interval_layout.addWidget(QLabel("~"))
        self.crawl_max = QDoubleSpinBox()
        self.crawl_max.setRange(1, 60)
        self.crawl_max.setValue(config.get("crawler", "request_interval_max", default=5.0))
        interval_layout.addWidget(self.crawl_max)
        layout.addLayout(interval_layout, 0, 1)

        layout.addWidget(QLabel("最小分辨率:"), 1, 0)
        res_layout = QHBoxLayout()
        self.crawl_min_w = QSpinBox()
        self.crawl_min_w.setRange(100, 4096)
        self.crawl_min_w.setValue(config.get("crawler", "min_resolution_width", default=800))
        res_layout.addWidget(self.crawl_min_w)
        res_layout.addWidget(QLabel("x"))
        self.crawl_min_h = QSpinBox()
        self.crawl_min_h.setRange(100, 4096)
        self.crawl_min_h.setValue(config.get("crawler", "min_resolution_height", default=600))
        res_layout.addWidget(self.crawl_min_h)
        layout.addLayout(res_layout, 1, 1)

        layout.addWidget(QLabel("每站最大数量:"), 2, 0)
        self.crawl_max_per = QSpinBox()
        self.crawl_max_per.setRange(10, 2000)
        self.crawl_max_per.setValue(config.get("crawler", "max_images_per_site", default=100))
        layout.addWidget(self.crawl_max_per, 2, 1)

        layout.addWidget(QLabel("启用代理:"), 3, 0)
        self.crawl_proxy = QCheckBox()
        self.crawl_proxy.setChecked(config.get("crawler", "proxy_enabled", default=False))
        layout.addWidget(self.crawl_proxy, 3, 1)

        layout.addWidget(QLabel("代理地址:"), 4, 0)
        self.crawl_proxy_url = QLineEdit(config.get("crawler", "proxy_url", default=""))
        self.crawl_proxy_url.setPlaceholderText("http://127.0.0.1:7890")
        layout.addWidget(self.crawl_proxy_url, 4, 1)

        return panel

    # ==================== 通用设置 ====================

    def _create_general_tab(self) -> QWidget:
        panel = QWidget()
        layout = QGridLayout(panel)

        layout.addWidget(QLabel("主题:"), 0, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(config.get("app", "theme", default="dark"))
        layout.addWidget(self.theme_combo, 0, 1)

        layout.addWidget(QLabel("数据根目录:"), 1, 0)
        layout.addWidget(QLabel(pm.root), 1, 1)

        layout.addWidget(QLabel("数据库路径:"), 2, 0)
        layout.addWidget(QLabel(pm.db_path()), 2, 1)

        layout.addWidget(QLabel("配置文件路径:"), 3, 0)
        layout.addWidget(QLabel(config.config_path), 3, 1)

        return panel

    # ==================== 保存 ====================

    def _save(self):
        """保存所有设置"""
        # SD
        config.set("sd_webui", "api_mode", self.sd_mode.currentText())
        config.set("sd_webui", "api_url", self.sd_url.text())
        config.set("sd_webui", "timeout", self.sd_timeout.value())
        config.set("sd_webui", "default_sampler", self.sd_sampler.currentText())
        config.set("sd_webui", "default_steps", self.sd_steps.value())
        config.set("sd_webui", "default_cfg_scale", self.sd_cfg.value())
        config.set("sd_webui", "hires_fix_enabled", self.hires_check.isChecked())
        config.set("sd_webui", "hires_fix_scale", self.hires_scale.value())

        # MiMo
        config.set("mimo_api", "api_key", self.mimo_key.text())
        config.set("mimo_api", "base_url", self.mimo_url.text())
        model_data = self.mimo_model.currentData()
        config.set("mimo_api", "model", model_data if model_data else self.mimo_model.currentText())
        config.set("mimo_api", "timeout", self.mimo_timeout.value())
        config.set("mimo_api", "max_retries", self.mimo_retries.value())

        # Training
        config.set("training", "kohya_ss_path", self.kohya_path.text())
        config.set("training", "default_rank", int(self.train_rank.currentText()))
        config.set("training", "default_optimizer", self.train_optimizer.currentText())
        config.set("training", "default_mixed_precision", self.train_precision.currentText())

        # Crawler
        config.set("crawler", "request_interval_min", self.crawl_min.value())
        config.set("crawler", "request_interval_max", self.crawl_max.value())
        config.set("crawler", "min_resolution_width", self.crawl_min_w.value())
        config.set("crawler", "min_resolution_height", self.crawl_min_h.value())
        config.set("crawler", "max_images_per_site", self.crawl_max_per.value())
        config.set("crawler", "proxy_enabled", self.crawl_proxy.isChecked())
        config.set("crawler", "proxy_url", self.crawl_proxy_url.text())

        # General
        config.set("app", "theme", self.theme_combo.currentText())

        # 持久化到文件
        config.save()

        QMessageBox.information(self, "保存", "✅ 设置已保存")
        self.accept()
