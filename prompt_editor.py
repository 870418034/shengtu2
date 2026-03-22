# -*- coding: utf-8 -*-
"""
智能助手界面 - 文字描述转设计图、草图转设计、风格迁移、客户需求分析
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QSlider,
    QCheckBox, QGroupBox, QScrollArea, QFileDialog, QProgressBar,
    QListWidget, QListWidgetItem, QTabWidget, QMessageBox, QStackedWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor

from core.config_manager import config
from core.sd_api import sd_api
from core.mimo_api import mimo_api
from core.database import db
from core.image_utils import save_image, load_image
from utils.path_manager import pm
from utils.logger import logger


class DesignFromTextThread(QThread):
    """文字描述生成设计线程"""
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, prompt, negative, params):
        super().__init__()
        self.prompt = prompt
        self.negative = negative
        self.params = params

    def run(self):
        try:
            p = {
                "prompt": self.prompt,
                "negative_prompt": self.negative,
                "sampler_name": self.params.get("sampler", "DPM++ 2M Karras"),
                "steps": self.params.get("steps", 30),
                "cfg_scale": self.params.get("cfg_scale", 7.0),
                "seed": -1,
                "width": self.params.get("width", 512),
                "height": self.params.get("height", 512),
                "batch_size": self.params.get("batch_size", 1),
            }
            result = sd_api.txt2img(p)
            self.finished.emit(result.get("images", []))
        except Exception as e:
            self.error.emit(str(e))


class SketchToDesignThread(QThread):
    """草图转设计线程"""
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, sketch_path, prompt, params):
        super().__init__()
        self.sketch_path = sketch_path
        self.prompt = prompt
        self.params = params

    def run(self):
        try:
            import base64
            with open(self.sketch_path, "rb") as f:
                sketch_b64 = base64.b64encode(f.read()).decode()

            p = {
                "prompt": self.prompt,
                "negative_prompt": "low quality, blurry, deformed",
                "sampler_name": "DPM++ 2M Karras",
                "steps": 30,
                "cfg_scale": 7.0,
                "seed": -1,
                "width": self.params.get("width", 512),
                "height": self.params.get("height", 512),
                "alwayson_scripts": {
                    "controlnet": {
                        "args": [{
                            "input_image": sketch_b64,
                            "module": "scribble",
                            "model": "control_v11p_sd15_scribble",
                            "weight": 1.0,
                            "enabled": True,
                        }]
                    }
                }
            }
            result = sd_api.txt2img(p)
            self.finished.emit(result.get("images", []))
        except Exception as e:
            self.error.emit(str(e))


class SimpleSketchpad(QWidget):
    """简易画板"""

    def __init__(self):
        super().__init__()
        self._drawing = False
        self._last_pos = None
        self._pen_color = QColor(255, 255, 255)
        self._pen_width = 3
        self._image = None
        self.setMinimumSize(400, 400)
        self.setStyleSheet("background-color: #1a1a1a; border: 1px solid #444;")
        self.clear()

    def clear(self):
        self._image = QPixmap(self.width(), self.height())
        self._image.fill(QColor(26, 26, 26))
        self.update()

    def set_pen_width(self, w):
        self._pen_width = w

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drawing = True
            self._last_pos = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self._drawing and self._last_pos:
            painter = QPainter(self._image)
            pen = QPen(self._pen_color, self._pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(self._last_pos, event.position().toPoint())
            painter.end()
            self._last_pos = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        self._drawing = False
        self._last_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._image)

    def save_sketch(self, path):
        self._image.save(path, "PNG")
        return path


class AssistantTab(QWidget):
    """智能助手标签页"""

    def __init__(self):
        super().__init__()
        self._generated_images = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # 子标签页
        sub_tabs = QTabWidget()

        # 文字转设计
        sub_tabs.addTab(self._create_text_to_design(), "✍️ 文字转设计")
        # 草图转设计
        sub_tabs.addTab(self._create_sketch_to_design(), "✏️ 草图转设计")
        # 客户需求分析
        sub_tabs.addTab(self._create_customer_need(), "👤 客户需求")
        # 风格迁移
        sub_tabs.addTab(self._create_style_transfer(), "🎨 风格迁移")

        layout.addWidget(sub_tabs)

        # 底部结果预览
        result_group = QGroupBox("生成结果")
        result_layout = QVBoxLayout(result_group)

        self.result_label = QLabel("生成结果将在这里显示")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setMinimumHeight(300)
        self.result_label.setStyleSheet(
            "background-color: #252525; border: 1px solid #333; border-radius: 8px;"
        )
        result_layout.addWidget(self.result_label)

        save_btn = QPushButton("💾 保存到图库")
        save_btn.clicked.connect(self._save_result)
        result_layout.addWidget(save_btn)

        layout.addWidget(result_group, 1)

    def _create_text_to_design(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("输入设计描述（中文）:"))
        self.text_desc = QTextEdit()
        self.text_desc.setPlaceholderText(
            "例：18K白金四爪镶嵌冰种翡翠蛋面戒指，戒臂带小钻副石，简约现代风格"
        )
        self.text_desc.setMaximumHeight(100)
        layout.addWidget(self.text_desc)

        # MiMo优化
        optimize_row = QHBoxLayout()
        optimize_btn = QPushButton("🤖 AI优化提示词")
        optimize_btn.clicked.connect(self._optimize_prompt)
        optimize_row.addWidget(optimize_btn)
        self.optimize_status = QLabel("")
        optimize_row.addWidget(self.optimize_status)
        layout.addLayout(optimize_row)

        layout.addWidget(QLabel("优化后的英文提示词:"))
        self.optimized_prompt = QTextEdit()
        self.optimized_prompt.setPlaceholderText("AI优化后的英文提示词将显示在这里，可手动编辑")
        self.optimized_prompt.setMaximumHeight(100)
        layout.addWidget(self.optimized_prompt)

        # 常用模板
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("常用模板:"))
        templates = [
            "四爪镶嵌翡翠戒指",
            "包镶翡翠吊坠",
            "轨道镶钻石手链",
            "钉镶红宝石耳环",
            "新中式翡翠发簪",
        ]
        for t in templates:
            btn = QPushButton(t)
            btn.setProperty("secondary", True)
            btn.setMaximumHeight(28)
            btn.clicked.connect(lambda checked, text=t: self.text_desc.setPlainText(text))
            template_layout.addWidget(btn)
        layout.addLayout(template_layout)

        # 生成按钮
        gen_btn = QPushButton("🎨 生成设计图")
        gen_btn.setProperty("gold", True)
        gen_btn.clicked.connect(self._generate_from_text)
        layout.addWidget(gen_btn)

        layout.addStretch()
        return panel

    def _create_sketch_to_design(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 画板
        layout.addWidget(QLabel("在画板上绘制草图:"))
        self.sketchpad = SimpleSketchpad()
        layout.addWidget(self.sketchpad, 1)

        # 工具栏
        tool_layout = QHBoxLayout()
        tool_layout.addWidget(QLabel("画笔粗细:"))
        self.pen_width = QSpinBox()
        self.pen_width.setRange(1, 20)
        self.pen_width.setValue(3)
        self.pen_width.valueChanged.connect(self.sketchpad.set_pen_width)
        tool_layout.addWidget(self.pen_width)

        clear_btn = QPushButton("🗑️ 清空")
        clear_btn.setProperty("secondary", True)
        clear_btn.clicked.connect(self.sketchpad.clear)
        tool_layout.addWidget(clear_btn)

        upload_btn = QPushButton("📂 上传草图")
        upload_btn.setProperty("secondary", True)
        upload_btn.clicked.connect(self._upload_sketch)
        tool_layout.addWidget(upload_btn)

        layout.addLayout(tool_layout)

        # 提示词
        layout.addWidget(QLabel("描述草图内容:"))
        self.sketch_prompt = QLineEdit()
        self.sketch_prompt.setPlaceholderText("如：jadeite ring with prong setting")
        layout.addWidget(self.sketch_prompt)

        gen_btn = QPushButton("🎨 草图转设计")
        gen_btn.setProperty("gold", True)
        gen_btn.clicked.connect(self._sketch_to_design)
        layout.addWidget(gen_btn)

        return panel

    def _create_customer_need(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("输入客户需求描述:"))
        self.customer_need = QTextEdit()
        self.customer_need.setPlaceholderText(
            "例：想要一个送妈妈的生日礼物，预算2万，喜欢绿色，妈妈今年50岁"
        )
        self.customer_need.setMaximumHeight(120)
        layout.addWidget(self.customer_need)

        analyze_btn = QPushButton("🤖 AI分析需求")
        analyze_btn.clicked.connect(self._analyze_need)
        layout.addWidget(analyze_btn)

        layout.addWidget(QLabel("AI设计方案:"))
        self.plan_text = QTextEdit()
        self.plan_text.setReadOnly(True)
        self.plan_text.setMaximumHeight(200)
        layout.addWidget(self.plan_text)

        gen_btn = QPushButton("🎨 生成设计方案")
        gen_btn.setProperty("gold", True)
        gen_btn.clicked.connect(self._generate_from_need)
        layout.addWidget(gen_btn)

        layout.addStretch()
        return panel

    def _create_style_transfer(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("参考图（要迁移的风格）:"))
        self.ref_image_label = QLabel("未选择")
        self.ref_image_label.setAlignment(Qt.AlignCenter)
        self.ref_image_label.setMinimumHeight(150)
        self.ref_image_label.setStyleSheet(
            "background-color: #252525; border: 2px dashed #444; border-radius: 8px;"
        )
        layout.addWidget(self.ref_image_label)

        select_ref_btn = QPushButton("选择参考图")
        select_ref_btn.clicked.connect(self._select_ref_image)
        layout.addWidget(select_ref_btn)

        layout.addWidget(QLabel("源设计图:"))
        self.src_image_label = QLabel("未选择")
        self.src_image_label.setAlignment(Qt.AlignCenter)
        self.src_image_label.setMinimumHeight(150)
        self.src_image_label.setStyleSheet(
            "background-color: #252525; border: 2px dashed #444; border-radius: 8px;"
        )
        layout.addWidget(self.src_image_label)

        select_src_btn = QPushButton("选择源图")
        select_src_btn.clicked.connect(self._select_src_image)
        layout.addWidget(select_src_btn)

        # 风格强度
        str_layout = QHBoxLayout()
        str_layout.addWidget(QLabel("风格强度:"))
        self.style_strength = QSlider(Qt.Horizontal)
        self.style_strength.setRange(10, 100)
        self.style_strength.setValue(60)
        str_layout.addWidget(self.style_strength)
        layout.addLayout(str_layout)

        transfer_btn = QPushButton("🎨 应用风格迁移")
        transfer_btn.setProperty("gold", True)
        transfer_btn.clicked.connect(self._style_transfer)
        layout.addWidget(transfer_btn)

        layout.addStretch()
        return panel

    def _optimize_prompt(self):
        """AI优化提示词"""
        desc = self.text_desc.toPlainText().strip()
        if not desc:
            return
        try:
            self.optimize_status.setText("优化中...")
            prompt = mimo_api.generate_design_description(desc)
            self.optimized_prompt.setPlainText(prompt)
            self.optimize_status.setText("✅ 优化完成")
        except Exception as e:
            self.optimize_status.setText(f"❌ {e}")

    def _generate_from_text(self):
        """从文字生成设计"""
        prompt = self.optimized_prompt.toPlainText().strip()
        if not prompt:
            prompt = self.text_desc.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "提示", "请输入设计描述")
            return

        if not sd_api.check_connection()["connected"]:
            QMessageBox.warning(self, "连接错误", "SD WebUI未连接")
            return

        params = {"width": 512, "height": 512, "batch_size": 1}
        negative = "low quality, blurry, deformed, ugly, watermark, text"

        self.result_label.setText("生成中...")

        self._text_thread = DesignFromTextThread(prompt, negative, params)
        self._text_thread.finished.connect(self._on_result)
        self._text_thread.error.connect(self._on_error)
        self._text_thread.start()

    def _upload_sketch(self):
        """上传草图"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择草图", "", "图片 (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            pixmap = QPixmap(path)
            self.sketchpad._image = pixmap.scaled(
                self.sketchpad.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.sketchpad.update()

    def _sketch_to_design(self):
        """草图转设计"""
        prompt = self.sketch_prompt.text().strip()
        if not prompt:
            prompt = "jadeite jewelry design, professional photo, 8k detailed"

        # 保存草图
        sketch_path = os.path.join(pm.get("cache"), "sketch.png")
        self.sketchpad.save_sketch(sketch_path)

        if not sd_api.check_connection()["connected"]:
            QMessageBox.warning(self, "连接错误", "SD WebUI未连接")
            return

        self.result_label.setText("生成中...")
        self._sketch_thread = SketchToDesignThread(sketch_path, prompt, {"width": 512, "height": 512})
        self._sketch_thread.finished.connect(self._on_result)
        self._sketch_thread.error.connect(self._on_error)
        self._sketch_thread.start()

    def _analyze_need(self):
        """分析客户需求"""
        need = self.customer_need.toPlainText().strip()
        if not need:
            return
        try:
            plans = mimo_api.analyze_customer_need(need)
            text = ""
            for i, plan in enumerate(plans, 1):
                text += f"【方案{i}: {plan.get('name', '')}】\n"
                text += f"描述: {plan.get('description', '')}\n"
                text += f"预算: {plan.get('budget_range', '')}\n\n"
            self.plan_text.setPlainText(text)
            self._need_plans = plans
        except Exception as e:
            self.plan_text.setPlainText(f"分析失败: {e}")

    def _generate_from_need(self):
        """从客户需求生成设计"""
        if not hasattr(self, "_need_plans") or not self._need_plans:
            QMessageBox.warning(self, "提示", "请先分析客户需求")
            return

        if not sd_api.check_connection()["connected"]:
            QMessageBox.warning(self, "连接错误", "SD WebUI未连接")
            return

        prompt = self._need_plans[0].get("sd_prompt", "")
        self.result_label.setText("生成中...")
        params = {"width": 512, "height": 512}
        self._need_thread = DesignFromTextThread(prompt, "low quality, blurry", params)
        self._need_thread.finished.connect(self._on_result)
        self._need_thread.error.connect(self._on_error)
        self._need_thread.start()

    def _select_ref_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择参考图", "", "图片 (*.png *.jpg)")
        if path:
            self._ref_path = path
            pixmap = QPixmap(path).scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.ref_image_label.setPixmap(pixmap)

    def _select_src_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择源图", "", "图片 (*.png *.jpg)")
        if path:
            self._src_path = path
            pixmap = QPixmap(path).scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.src_image_label.setPixmap(pixmap)

    def _style_transfer(self):
        """风格迁移"""
        if not hasattr(self, "_src_path"):
            QMessageBox.warning(self, "提示", "请先选择源图")
            return

        if not sd_api.check_connection()["connected"]:
            QMessageBox.warning(self, "连接错误", "SD WebUI未连接")
            return

        strength = self.style_strength.value() / 100
        src_img = load_image(self._src_path)

        self.result_label.setText("迁移中...")
        try:
            result = sd_api.img2img(src_img, {
                "prompt": "same design, new style, professional jewelry photo, 8k detailed",
                "negative_prompt": "low quality, blurry, deformed",
                "sampler_name": "DPM++ 2M Karras",
                "steps": 30,
                "cfg_scale": 7.0,
                "denoising_strength": strength,
                "width": src_img.width,
                "height": src_img.height,
            })
            self._on_result(result.get("images", []))
        except Exception as e:
            self._on_error(str(e))

    def _on_result(self, images):
        """显示生成结果"""
        if images:
            self._generated_images = images
            img = images[0]
            display = img.copy()
            display.thumbnail((500, 500))
            data = display.tobytes("raw", "RGB")
            qimg = QImage(data, display.width, display.height, QImage.Format.Format_RGB888)
            self.result_label.setPixmap(QPixmap.fromImage(qimg))
            self.result_label.setAlignment(Qt.AlignCenter)

    def _on_error(self, msg):
        self.result_label.setText(f"错误: {msg}")

    def _save_result(self):
        """保存结果"""
        if self._generated_images:
            for img in self._generated_images:
                filepath = save_image(img, pm.get("outputs_designs"), prefix="assistant")
                db.insert_design({
                    "filename": os.path.basename(filepath),
                    "filepath": filepath,
                    "prompt": "",
                    "parameters": {},
                })
            QMessageBox.information(self, "保存", f"已保存 {len(self._generated_images)} 张图片")
        else:
            QMessageBox.information(self, "保存", "没有可保存的图片")
