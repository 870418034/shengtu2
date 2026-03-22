# -*- coding: utf-8 -*-
"""
AI生图界面 - 核心生成模块UI
"""
import os
import yaml
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QLabel, QPushButton, QTextEdit, QLineEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QSlider, QCheckBox, QGroupBox, QScrollArea,
    QFileDialog, QTabWidget, QProgressBar, QListWidget, QListWidgetItem,
    QRadioButton, QButtonGroup, QFrame, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QPixmap, QImage

from core.config_manager import config
from core.sd_api import sd_api
from core.database import db
from core.image_utils import save_image, load_image
from utils.path_manager import pm
from utils.logger import logger


class GenerateThread(QThread):
    """生成线程"""
    progress = Signal(int, int)  # current, total
    finished = Signal(list)  # images
    error = Signal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        try:
            result = sd_api.txt2img(self.params)
            self.finished.emit(result.get("images", []))
        except Exception as e:
            self.error.emit(str(e))


class GenerateTab(QWidget):
    """AI生图标签页"""

    def __init__(self):
        super().__init__()
        self._generated_images = []
        self._current_image = None
        self._gen_thread = None
        self._load_prompt_templates()
        self._init_ui()

    def _load_prompt_templates(self):
        """加载提示词模板"""
        try:
            template_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "config", "prompt_templates.yaml"
            )
            if os.path.exists(template_path):
                with open(template_path, "r", encoding="utf-8") as f:
                    self._templates = yaml.safe_load(f)
            else:
                self._templates = {}
        except Exception as e:
            logger.error(f"加载提示词模板失败: {e}")
            self._templates = {}

    def _init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # 左侧：参数面板
        left_panel = self._create_param_panel()
        left_scroll = QScrollArea()
        left_scroll.setWidget(left_panel)
        left_scroll.setWidgetResizable(True)
        left_scroll.setFixedWidth(380)

        # 右侧：生成结果
        right_panel = self._create_result_panel()

        layout.addWidget(left_scroll)
        layout.addWidget(right_panel, 1)

    def _create_param_panel(self) -> QWidget:
        """创建参数面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        # ====== 提示词区 ======
        prompt_group = QGroupBox("提示词")
        prompt_layout = QVBoxLayout(prompt_group)

        # 模板选择
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("模板:"))
        self.template_combo = QComboBox()
        self.template_combo.addItem("手动输入", "")
        self._populate_templates()
        self.template_combo.currentIndexChanged.connect(self._on_template_selected)
        template_layout.addWidget(self.template_combo)
        prompt_layout.addLayout(template_layout)

        # 正向提示词
        prompt_layout.addWidget(QLabel("正向提示词:"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText(
            "输入设计描述，如：18K white gold prong setting jadeite ring..."
        )
        self.prompt_edit.setMaximumHeight(100)
        prompt_layout.addWidget(self.prompt_edit)

        # 负向提示词
        prompt_layout.addWidget(QLabel("负向提示词:"))
        self.negative_edit = QTextEdit()
        self.negative_edit.setPlaceholderText("输入要排除的内容...")
        self.negative_edit.setMaximumHeight(60)
        # 预设珠宝负向
        self.negative_edit.setText(
            "low quality, blurry, deformed, ugly, watermark, text, logo, "
            "bent metal, uneven prongs, asymmetric setting, dull gemstone, plastic look"
        )
        prompt_layout.addWidget(self.negative_edit)

        # 快速标签按钮
        tag_layout = QHBoxLayout()
        for name, data in [("爪镶", "prong setting"), ("包镶", "bezel setting"),
                           ("冰种翡翠", "icy jadeite"), ("18K白金", "18k white gold")]:
            btn = QPushButton(name)
            btn.setProperty("secondary", True)
            btn.setMaximumWidth(70)
            btn.clicked.connect(lambda checked, t=data: self._insert_tag(t))
            tag_layout.addWidget(btn)
        prompt_layout.addLayout(tag_layout)

        # 复制提示词按钮
        copy_btn = QPushButton("📋 复制提示词")
        copy_btn.setProperty("secondary", True)
        copy_btn.clicked.connect(self.copy_prompt)
        prompt_layout.addWidget(copy_btn)

        layout.addWidget(prompt_group)

        # ====== 模型选择 ======
        model_group = QGroupBox("模型")
        model_layout = QGridLayout(model_group)

        model_layout.addWidget(QLabel("基础模型:"), 0, 0)
        self.model_combo = QComboBox()
        self.model_combo.addItem("加载中...")
        model_layout.addWidget(self.model_combo, 0, 1)

        model_layout.addWidget(QLabel("LoRA:"), 1, 0)
        self.lora_combo = QComboBox()
        self.lora_combo.addItem("无", "")
        model_layout.addWidget(self.lora_combo, 1, 1)

        model_layout.addWidget(QLabel("LoRA权重:"), 2, 0)
        self.lora_weight_spin = QDoubleSpinBox()
        self.lora_weight_spin.setRange(0.0, 2.0)
        self.lora_weight_spin.setSingleStep(0.05)
        self.lora_weight_spin.setValue(0.7)
        model_layout.addWidget(self.lora_weight_spin, 2, 1)

        layout.addWidget(model_group)

        # ====== 采样参数 ======
        sampler_group = QGroupBox("采样参数")
        sampler_layout = QGridLayout(sampler_group)

        sampler_layout.addWidget(QLabel("采样器:"), 0, 0)
        self.sampler_combo = QComboBox()
        self.sampler_combo.addItems([
            "DPM++ 2M Karras", "DPM++ SDE Karras", "Euler a", "Euler",
            "DDIM", "UniPC", "LMS", "Heun"
        ])
        sampler_layout.addWidget(self.sampler_combo, 0, 1)

        sampler_layout.addWidget(QLabel("步数:"), 1, 0)
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(1, 150)
        self.steps_spin.setValue(30)
        sampler_layout.addWidget(self.steps_spin, 1, 1)

        sampler_layout.addWidget(QLabel("CFG Scale:"), 2, 0)
        self.cfg_spin = QDoubleSpinBox()
        self.cfg_spin.setRange(1.0, 30.0)
        self.cfg_spin.setSingleStep(0.5)
        self.cfg_spin.setValue(7.0)
        sampler_layout.addWidget(self.cfg_spin, 2, 1)

        sampler_layout.addWidget(QLabel("种子:"), 3, 0)
        seed_layout = QHBoxLayout()
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(-1, 2**31 - 1)
        self.seed_spin.setValue(-1)
        seed_layout.addWidget(self.seed_spin)
        rand_seed_btn = QPushButton("🎲")
        rand_seed_btn.setProperty("secondary", True)
        rand_seed_btn.setToolTip("随机种子")
        rand_seed_btn.clicked.connect(lambda: self.seed_spin.setValue(-1))
        seed_layout.addWidget(rand_seed_btn)
        sampler_layout.addLayout(seed_layout, 3, 1)

        layout.addWidget(sampler_group)

        # ====== 分辨率 ======
        res_group = QGroupBox("分辨率")
        res_layout = QGridLayout(res_group)

        res_layout.addWidget(QLabel("宽度:"), 0, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(256, 2048)
        self.width_spin.setSingleStep(64)
        self.width_spin.setValue(512)
        res_layout.addWidget(self.width_spin, 0, 1)

        res_layout.addWidget(QLabel("高度:"), 1, 0)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(256, 2048)
        self.height_spin.setSingleStep(64)
        self.height_spin.setValue(512)
        res_layout.addWidget(self.height_spin, 1, 1)

        # 快捷分辨率
        quick_res = QHBoxLayout()
        for label, w, h in [("512", 512, 512), ("768", 768, 768), ("1024", 1024, 1024)]:
            btn = QPushButton(label)
            btn.setProperty("secondary", True)
            btn.clicked.connect(lambda checked, ww=w, hh=h: (
                self.width_spin.setValue(ww), self.height_spin.setValue(hh)
            ))
            quick_res.addWidget(btn)
        res_layout.addLayout(quick_res, 2, 0, 1, 2)

        res_layout.addWidget(QLabel("批量:"), 3, 0)
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 16)
        self.batch_spin.setValue(1)
        res_layout.addWidget(self.batch_spin, 3, 1)

        layout.addWidget(res_group)

        # ====== 高级选项 ======
        adv_group = QGroupBox("高级选项")
        adv_layout = QVBoxLayout(adv_group)

        # Hi-res Fix
        self.hires_check = QCheckBox("高清修复 (Hires.fix)")
        self.hires_check.setToolTip("低分辨率生成后自动超分")
        adv_layout.addWidget(self.hires_check)

        hires_layout = QHBoxLayout()
        hires_layout.addWidget(QLabel("放大倍率:"))
        self.hires_scale_spin = QDoubleSpinBox()
        self.hires_scale_spin.setRange(1.0, 4.0)
        self.hires_scale_spin.setSingleStep(0.25)
        self.hires_scale_spin.setValue(2.0)
        hires_layout.addWidget(self.hires_scale_spin)
        adv_layout.addLayout(hires_layout)

        # ADetailer
        self.adetailer_check = QCheckBox("ADetailer 自动修复")
        self.adetailer_check.setToolTip("自动检测并修复细节区域")
        adv_layout.addWidget(self.adetailer_check)

        # ControlNet
        self.controlnet_check = QCheckBox("启用 ControlNet")
        adv_layout.addWidget(self.controlnet_check)

        cn_layout = QHBoxLayout()
        cn_layout.addWidget(QLabel("类型:"))
        self.cn_type_combo = QComboBox()
        self.cn_type_combo.addItems(["Canny", "Depth", "Scribble", "Lineart"])
        cn_layout.addWidget(self.cn_type_combo)
        adv_layout.addLayout(cn_layout)

        self.cn_image_path = ""
        cn_img_layout = QHBoxLayout()
        self.cn_image_label = QLabel("未选择图片")
        cn_img_layout.addWidget(self.cn_image_label)
        cn_select_btn = QPushButton("选择")
        cn_select_btn.setProperty("secondary", True)
        cn_select_btn.clicked.connect(self._select_cn_image)
        cn_img_layout.addWidget(cn_select_btn)
        adv_layout.addLayout(cn_img_layout)

        layout.addWidget(adv_group)

        # ====== 生成按钮 ======
        gen_layout = QHBoxLayout()

        self.gen_btn = QPushButton("🎨 开始生成")
        self.gen_btn.setProperty("gold", True)
        self.gen_btn.setMinimumHeight(45)
        self.gen_btn.clicked.connect(self.start_generation)
        gen_layout.addWidget(self.gen_btn)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_generation)
        gen_layout.addWidget(self.stop_btn)

        layout.addLayout(gen_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        layout.addStretch()
        return panel

    def _create_result_panel(self) -> QWidget:
        """创建结果面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("生成结果"))

        self.img_count_label = QLabel("共 0 张")
        toolbar.addWidget(self.img_count_label)
        toolbar.addStretch()

        save_btn = QPushButton("💾 保存选中")
        save_btn.setProperty("secondary", True)
        save_btn.clicked.connect(self.save_current_design)
        toolbar.addWidget(save_btn)

        save_all_btn = QPushButton("💾 全部保存")
        save_all_btn.setProperty("secondary", True)
        save_all_btn.clicked.connect(self._save_all)
        toolbar.addWidget(save_all_btn)

        layout.addLayout(toolbar)

        # 主图预览
        self.main_preview = QLabel("点击「开始生成」创建设计图")
        self.main_preview.setAlignment(Qt.AlignCenter)
        self.main_preview.setMinimumHeight(400)
        self.main_preview.setStyleSheet(
            "background-color: #252525; border: 1px solid #333; border-radius: 8px;"
        )
        layout.addWidget(self.main_preview, 1)

        # 缩略图列表
        self.thumb_list = QListWidget()
        self.thumb_list.setFlow(QListWidget.LeftToRight)
        self.thumb_list.setMaximumHeight(120)
        self.thumb_list.setIconSize(QSize(100, 100))
        self.thumb_list.itemClicked.connect(self._on_thumb_clicked)
        layout.addWidget(self.thumb_list)

        # 生成信息
        self.info_label = QLabel("")
        self.info_label.setProperty("color", "status")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        return panel

    def _populate_templates(self):
        """填充模板下拉框"""
        if not self._templates:
            return

        # 镶嵌工艺
        techniques = self._templates.get("setting_techniques", {})
        for key, val in techniques.items():
            self.template_combo.addItem(f"工艺: {val['cn']}", val.get("prompt", ""))

        # 金属材质
        metals = self._templates.get("metal_materials", {})
        for key, val in metals.items():
            self.template_combo.addItem(f"金属: {val['cn']}", val.get("prompt", ""))

        # 风格
        styles = self._templates.get("styles", {})
        for key, val in styles.items():
            self.template_combo.addItem(f"风格: {val['cn']}", val.get("prompt", ""))

    def _on_template_selected(self, index):
        """模板选择事件"""
        prompt = self.template_combo.itemData(index)
        if prompt:
            current = self.prompt_edit.toPlainText()
            if current:
                self.prompt_edit.setPlainText(f"{current}, {prompt}")
            else:
                self.prompt_edit.setPlainText(prompt)

    def _insert_tag(self, tag: str):
        """插入标签到提示词"""
        current = self.prompt_edit.toPlainText()
        if current:
            self.prompt_edit.setPlainText(f"{current}, {tag}")
        else:
            self.prompt_edit.setPlainText(tag)

    def _select_cn_image(self):
        """选择ControlNet参考图"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择ControlNet参考图", "",
            "图片文件 (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if path:
            self.cn_image_path = path
            self.cn_image_label.setText(os.path.basename(path))

    def _get_generation_params(self) -> dict:
        """获取生成参数"""
        prompt = self.prompt_edit.toPlainText().strip()
        negative = self.negative_edit.toPlainText().strip()

        params = {
            "prompt": prompt,
            "negative_prompt": negative,
            "sampler_name": self.sampler_combo.currentText(),
            "steps": self.steps_spin.value(),
            "cfg_scale": self.cfg_spin.value(),
            "seed": self.seed_spin.value(),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "batch_size": self.batch_spin.value(),
        }

        # LoRA
        lora_name = self.lora_combo.currentData()
        if lora_name:
            lora_weight = self.lora_weight_spin.value()
            params["prompt"] += f" <lora:{lora_name}:{lora_weight}>"

        # Hi-res Fix
        if self.hires_check.isChecked():
            params["enable_hr"] = True
            params["hr_scale"] = self.hires_scale_spin.value()
            params["hr_upscaler"] = config.get("sd_webui", "hires_fix_upscaler",
                                                default="4x-UltraSharp")
            params["denoising_strength"] = 0.4

        # ControlNet
        if self.controlnet_check.isChecked() and self.cn_image_path:
            import base64
            with open(self.cn_image_path, "rb") as f:
                cn_b64 = base64.b64encode(f.read()).decode()

            cn_type = self.cn_type_combo.currentText().lower()
            params["alwayson_scripts"] = {
                "controlnet": {
                    "args": [{
                        "input_image": cn_b64,
                        "module": cn_type,
                        "model": f"control_v11p_sd15_{cn_type}",
                        "weight": 1.0,
                        "enabled": True,
                    }]
                }
            }

        return params

    def start_generation(self):
        """开始生成"""
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "提示", "请输入提示词")
            return

        if not sd_api.check_connection()["connected"]:
            QMessageBox.warning(self, "连接错误", "SD WebUI未连接，请先启动SD WebUI")
            return

        params = self._get_generation_params()

        self.gen_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度

        self._gen_thread = GenerateThread(params)
        self._gen_thread.finished.connect(self._on_generation_finished)
        self._gen_thread.error.connect(self._on_generation_error)
        self._gen_thread.start()

    def stop_generation(self):
        """停止生成"""
        sd_api.interrupt()
        if self._gen_thread:
            self._gen_thread.terminate()
        self.gen_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

    def _on_generation_finished(self, images):
        """生成完成"""
        self._generated_images = images
        self.gen_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        # 显示图片
        self.thumb_list.clear()
        for i, img in enumerate(images):
            # 缩略图
            thumb = img.copy()
            thumb.thumbnail((100, 100))
            from PySide6.QtGui import QImage as QI
            data = thumb.tobytes("raw", "RGB")
            qimg = QI(data, thumb.width, thumb.height, QI.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)

            item = QListWidgetItem()
            item.setIcon(pixmap)
            item.setData(Qt.UserRole, i)
            self.thumb_list.addItem(item)

        if images:
            self._show_image(images[0])

        self.img_count_label.setText(f"共 {len(images)} 张")
        self.info_label.setText(f"生成完成: {len(images)} 张图片 | "
                                f"时间: {datetime.now():%H:%M:%S}")

    def _on_generation_error(self, error_msg):
        """生成错误"""
        self.gen_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "生成错误", f"生成失败:\n{error_msg}")

    def _on_thumb_clicked(self, item):
        """点击缩略图"""
        idx = item.data(Qt.UserRole)
        if 0 <= idx < len(self._generated_images):
            self._show_image(self._generated_images[idx])

    def _show_image(self, img):
        """显示图片到主预览区"""
        self._current_image = img
        display = img.copy()
        display.thumbnail((800, 800))
        data = display.tobytes("raw", "RGB")
        from PySide6.QtGui import QImage as QI
        qimg = QI(data, display.width, display.height, QI.Format.Format_RGB888)
        self.main_preview.setPixmap(QPixmap.fromImage(qimg))

    def copy_prompt(self):
        """复制提示词到剪贴板"""
        prompt = self.prompt_edit.toPlainText()
        QApplication.clipboard().setText(prompt)
        self.info_label.setText("提示词已复制到剪贴板")

    def save_current_design(self):
        """保存当前设计"""
        if self._current_image:
            filepath = save_image(
                self._current_image,
                pm.get("outputs_designs"),
                prefix="design"
            )
            # 记录到数据库
            db.insert_design({
                "filename": os.path.basename(filepath),
                "filepath": filepath,
                "prompt": self.prompt_edit.toPlainText(),
                "negative_prompt": self.negative_edit.toPlainText(),
                "parameters": self._get_generation_params(),
            })
            self.info_label.setText(f"已保存: {filepath}")
        else:
            QMessageBox.information(self, "保存", "没有可保存的设计图")

    def _save_all(self):
        """保存所有生成的图片"""
        for img in self._generated_images:
            filepath = save_image(img, pm.get("outputs_designs"), prefix="design")
            db.insert_design({
                "filename": os.path.basename(filepath),
                "filepath": filepath,
                "prompt": self.prompt_edit.toPlainText(),
                "negative_prompt": self.negative_edit.toPlainText(),
                "parameters": self._get_generation_params(),
            })
        self.info_label.setText(f"已保存 {len(self._generated_images)} 张图片")

    def new_design(self):
        """新建设计"""
        self.prompt_edit.clear()
        self._generated_images = []
        self._current_image = None
        self.thumb_list.clear()
        self.main_preview.setText("点击「开始生成」创建设计图")
        self.img_count_label.setText("共 0 张")
