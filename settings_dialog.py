# -*- coding: utf-8 -*-
"""
变体生成界面 - 从一张设计图批量生成多个变体
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QSlider, QCheckBox,
    QGroupBox, QScrollArea, QFileDialog, QProgressBar, QListWidget,
    QListWidgetItem, QMessageBox, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QPixmap, QImage

from core.config_manager import config
from core.sd_api import sd_api
from core.image_utils import save_image, load_image
from utils.path_manager import pm
from utils.logger import logger


class VariantThread(QThread):
    """变体生成线程"""
    progress = Signal(int, int)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, image, variant_type, params):
        super().__init__()
        self.image = image
        self.variant_type = variant_type
        self.params = params

    def run(self):
        try:
            results = []
            prompts = self.params.get("prompts", [self.params.get("prompt", "")])
            for i, prompt in enumerate(prompts):
                p = {
                    "prompt": prompt,
                    "negative_prompt": self.params.get("negative_prompt", ""),
                    "sampler_name": self.params.get("sampler", "DPM++ 2M Karras"),
                    "steps": self.params.get("steps", 30),
                    "cfg_scale": self.params.get("cfg_scale", 7.0),
                    "seed": -1,
                    "width": self.params.get("width", 512),
                    "height": self.params.get("height", 512),
                    "denoising_strength": self.params.get("strength", 0.5),
                }
                result = sd_api.img2img(self.image, p)
                if result.get("images"):
                    results.append({
                        "image": result["images"][0],
                        "prompt": prompt,
                        "variant_type": self.variant_type,
                    })
                self.progress.emit(i + 1, len(prompts))
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class VariantTab(QWidget):
    """变体生成标签页"""

    def __init__(self):
        super().__init__()
        self._source_image = None
        self._variant_results = []
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # 左侧
        left = self._create_config_panel()
        left_scroll = QScrollArea()
        left_scroll.setWidget(left)
        left_scroll.setWidgetResizable(True)
        left_scroll.setFixedWidth(350)

        # 右侧结果
        right = self._create_result_panel()

        layout.addWidget(left_scroll)
        layout.addWidget(right, 1)

    def _create_config_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        # 源图
        src_group = QGroupBox("源设计图")
        src_layout = QVBoxLayout(src_group)

        self.src_label = QLabel("点击「选择图片」加载源设计图")
        self.src_label.setAlignment(Qt.AlignCenter)
        self.src_label.setMinimumHeight(200)
        self.src_label.setStyleSheet(
            "background-color: #252525; border: 2px dashed #444; border-radius: 8px;"
        )
        src_layout.addWidget(self.src_label)

        select_btn = QPushButton("📂 选择源图片")
        select_btn.clicked.connect(self._select_source)
        src_layout.addWidget(select_btn)

        layout.addWidget(src_group)

        # 变体类型
        type_group = QGroupBox("变体类型")
        type_layout = QVBoxLayout(type_group)

        self.type_group = QButtonGroup()
        types = [
            ("material", "材质变体 - 同造型不同金属"),
            ("gemstone", "宝石变体 - 同托座不同主石"),
            ("style", "风格变体 - 同结构不同风格"),
            ("detail", "细节变体 - 微调细节元素"),
            ("color", "颜色变体 - 同款不同配色"),
        ]
        for i, (key, text) in enumerate(types):
            rb = QRadioButton(text)
            self.type_group.addButton(rb, i)
            if i == 0:
                rb.setChecked(True)
            type_layout.addWidget(rb)

        layout.addWidget(type_group)

        # 变体强度
        str_group = QGroupBox("变体强度")
        str_layout = QVBoxLayout(str_group)

        self.strength_slider = QSlider(Qt.Horizontal)
        self.strength_slider.setRange(5, 100)
        self.strength_slider.setValue(40)
        str_layout.addWidget(self.strength_slider)

        self.strength_label = QLabel("0.40")
        self.strength_slider.valueChanged.connect(
            lambda v: self.strength_label.setText(f"{v/100:.2f}")
        )
        str_layout.addWidget(self.strength_label)

        str_hint = QLabel("0.05=极微调  0.40=适中  1.0=大幅变化")
        str_hint.setProperty("color", "status")
        str_layout.addWidget(str_hint)

        layout.addWidget(str_group)

        # 变体数量
        num_group = QGroupBox("变体数量")
        num_layout = QHBoxLayout(num_group)
        self.count_combo = QComboBox()
        self.count_combo.addItems(["4 (2x2)", "9 (3x3)", "16 (4x4)"])
        num_layout.addWidget(self.count_combo)
        layout.addWidget(num_group)

        # 生成按钮
        self.gen_btn = QPushButton("🔄 生成变体")
        self.gen_btn.setProperty("gold", True)
        self.gen_btn.clicked.connect(self._generate_variants)
        layout.addWidget(self.gen_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        layout.addStretch()
        return panel

    def _create_result_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 工具栏
        toolbar = QHBoxLayout()
        self.result_label = QLabel("变体结果: 0 张")
        toolbar.addWidget(self.result_label)
        toolbar.addStretch()

        save_sel_btn = QPushButton("💾 保存选中")
        save_sel_btn.setProperty("secondary", True)
        save_sel_btn.clicked.connect(self._save_selected)
        toolbar.addWidget(save_sel_btn)

        save_all_btn = QPushButton("💾 全部保存")
        save_all_btn.setProperty("secondary", True)
        save_all_btn.clicked.connect(self._save_all)
        toolbar.addWidget(save_all_btn)

        layout.addLayout(toolbar)

        # 变体网格
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidget(self.grid_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, 1)

        return panel

    def _select_source(self):
        """选择源图片"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择源设计图", pm.get("outputs_designs"),
            "图片文件 (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self._source_image = load_image(path)
            pixmap = QPixmap(path).scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.src_label.setPixmap(pixmap)

    def _generate_variants(self):
        """生成变体"""
        if self._source_image is None:
            QMessageBox.warning(self, "提示", "请先选择源设计图")
            return

        if not sd_api.check_connection()["connected"]:
            QMessageBox.warning(self, "连接错误", "SD WebUI未连接")
            return

        # 确定变体数量
        count_text = self.count_combo.currentText()
        count = int(count_text.split()[0])

        # 变体类型
        btn = self.type_group.checkedButton()
        type_id = self.type_group.id(btn)
        variant_types = ["material", "gemstone", "style", "detail", "color"]
        variant_type = variant_types[type_id]

        # 生成变体提示词
        prompts = self._get_variant_prompts(variant_type, count)

        params = {
            "prompts": prompts,
            "negative_prompt": "low quality, blurry, deformed, ugly",
            "sampler": "DPM++ 2M Karras",
            "steps": 30,
            "cfg_scale": 7.0,
            "strength": self.strength_slider.value() / 100,
            "width": self._source_image.width,
            "height": self._source_image.height,
        }

        self.gen_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, count)

        self._variant_thread = VariantThread(self._source_image, variant_type, params)
        self._variant_thread.progress.connect(self._on_progress)
        self._variant_thread.finished.connect(self._on_finished)
        self._variant_thread.error.connect(self._on_error)
        self._variant_thread.start()

    def _get_variant_prompts(self, variant_type: str, count: int):
        """根据变体类型生成提示词"""
        base = "beautiful jadeite jewelry, professional product photo, 8k, detailed"
        variants = {
            "material": [
                f"{base}, 18k white gold setting",
                f"{base}, 18k yellow gold setting",
                f"{base}, 18k rose gold setting",
                f"{base}, platinum PT950 setting",
                f"{base}, sterling silver S925 setting",
                f"{base}, mixed gold tones",
                f"{base}, brushed gold finish",
                f"{base}, polished gold finish",
                f"{base}, matte gold finish",
                f"{base}, hammered gold texture",
                f"{base}, rhodium plated",
                f"{base}, antique gold patina",
                f"{base}, two-tone gold",
                f"{base}, rose and white gold",
                f"{base}, gold vermeil",
                f"{base}, gunmetal finish",
            ],
            "gemstone": [
                f"{base}, icy jadeite center stone",
                f"{base}, glassy jadeite center stone",
                f"{base}, diamond center stone",
                f"{base}, ruby center stone",
                f"{base}, sapphire center stone",
                f"{base}, emerald center stone",
                f"{base}, waxy jadeite stone",
                f"{base}, lavender jadeite",
                f"{base}, imperial green jadeite",
                f"{base}, red jadeite",
                f"{base}, yellow jadeite",
                f"{base}, white jadeite",
                f"{base}, black jade",
                f"{base}, pink sapphire",
                f"{base}, yellow diamond",
                f"{base}, tsavorite garnet",
            ],
            "style": [
                f"{base}, modern minimalist style",
                f"{base}, classical palace style",
                f"{base}, Art Deco style",
                f"{base}, neo-Chinese style",
                f"{base}, baroque ornate style",
                f"{base}, wabi-sabi Japanese style",
                f"{base}, light luxury style",
                f"{base}, contemporary abstract style",
                f"{base}, vintage retro style",
                f"{base}, geometric modern style",
                f"{base}, floral romantic style",
                f"{base}, industrial chic style",
                f"{base}, bohemian style",
                f"{base}, Scandinavian minimal",
                f"{base}, Victorian elegance",
                f"{base}, tribal ethnic style",
            ],
            "detail": [
                f"{base}, four-prong setting, smooth band",
                f"{base}, six-prong setting, diamond band",
                f"{base}, bezel setting, twisted band",
                f"{base}, pavé diamonds on band",
                f"{base}, channel set side stones",
                f"{base}, filigree details",
                f"{base}, milgrain edge detail",
                f"{base}, openwork gallery",
                f"{base}, cathedral setting",
                f"{base}, split shank band",
                f"{base}, halo setting",
                f"{base}, vintage engraving",
                f"{base}, knife edge band",
                f"{base}, comfort fit band",
                f"{base}, bypass shank",
                f"{base}, tension setting",
            ],
            "color": [
                f"{base}, warm golden tones",
                f"{base}, cool silver tones",
                f"{base}, rose pink tones",
                f"{base}, emerald green tones",
                f"{base}, sapphire blue tones",
                f"{base}, ruby red tones",
                f"{base}, neutral earth tones",
                f"{base}, monochrome black and white",
                f"{base}, pastel tones",
                f"{base}, vibrant saturated colors",
                f"{base}, muted desaturated",
                f"{base}, iridescent rainbow",
                f"{base}, aurora borealis colors",
                f"{base}, sunset orange tones",
                f"{base}, ocean blue green",
                f"{base}, midnight purple tones",
            ],
        }
        return variants.get(variant_type, [base] * count)[:count]

    def _on_progress(self, current, total):
        self.progress_bar.setValue(current)

    def _on_finished(self, results):
        self._variant_results = results
        self.gen_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.result_label.setText(f"变体结果: {len(results)} 张")
        self._show_grid(results)

    def _on_error(self, msg):
        self.gen_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "生成错误", msg)

    def _show_grid(self, results):
        """显示变体网格"""
        # 清空旧内容
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        cols = 4
        for idx, item in enumerate(results):
            img = item["image"]
            thumb = img.copy()
            thumb.thumbnail((180, 180))
            data = thumb.tobytes("raw", "RGB")
            qimg = QImage(data, thumb.width, thumb.height, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)

            label = QLabel()
            label.setPixmap(pixmap)
            label.setAlignment(Qt.AlignCenter)
            label.setToolTip(item.get("prompt", ""))
            label.setStyleSheet(
                "background-color: #252525; border: 1px solid #333; border-radius: 4px; padding: 4px;"
            )

            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(label, row, col)

    def _save_selected(self):
        """保存选中的变体"""
        # 简化实现：保存全部
        self._save_all()

    def _save_all(self):
        """保存所有变体"""
        if not self._variant_results:
            QMessageBox.information(self, "保存", "没有可保存的变体")
            return

        for item in self._variant_results:
            save_image(item["image"], pm.get("outputs_variants"), prefix="variant")

        QMessageBox.information(self, "保存完成",
                                f"已保存 {len(self._variant_results)} 张变体到:\n{pm.get('outputs_variants')}")
