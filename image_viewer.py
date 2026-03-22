# -*- coding: utf-8 -*-
"""
训练界面 - LoRA微调可视化训练
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QLabel, QPushButton, QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QScrollArea, QFileDialog, QProgressBar, QListWidget,
    QListWidgetItem, QTabWidget, QMessageBox, QTableWidget, QTableWidgetItem
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QPixmap, QImage

from core.config_manager import config
from core.trainer import trainer
from core.database import db
from core.mimo_api import mimo_api
from utils.path_manager import pm
from utils.logger import logger


class ImportThread(QThread):
    """素材导入线程"""
    progress = Signal(int, int, str)
    finished = Signal(dict)

    def __init__(self, source_dir, project_name):
        super().__init__()
        self.source_dir = source_dir
        self.project_name = project_name

    def run(self):
        result = trainer.import_dataset(
            self.source_dir, self.project_name,
            callback=lambda c, t, f: self.progress.emit(c, t, f)
        )
        self.finished.emit(result)


class TagThread(QThread):
    """自动打标线程"""
    progress = Signal(int, int, str, str)
    finished = Signal(dict)

    def __init__(self, project_name):
        super().__init__()
        self.project_name = project_name

    def run(self):
        result = trainer.auto_tag(
            self.project_name,
            callback=lambda c, t, f, tags: self.progress.emit(c, t, f, tags)
        )
        self.finished.emit(result)


class TrainTab(QWidget):
    """训练标签页"""

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # 左侧：配置
        left = self._create_config_panel()
        left_scroll = QScrollArea()
        left_scroll.setWidget(left)
        left_scroll.setWidgetResizable(True)
        left_scroll.setFixedWidth(400)

        # 右侧：训练状态
        right = self._create_training_panel()

        layout.addWidget(left_scroll)
        layout.addWidget(right, 1)

    def _create_config_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        # 项目管理
        proj_group = QGroupBox("训练项目")
        proj_layout = QVBoxLayout(proj_group)

        proj_row = QHBoxLayout()
        proj_row.addWidget(QLabel("项目名:"))
        self.project_name_edit = QLineEdit()
        self.project_name_edit.setPlaceholderText("如：爪镶翡翠戒指")
        proj_row.addWidget(self.project_name_edit)
        proj_layout.addLayout(proj_row)

        # 素材导入
        import_btn = QPushButton("📁 导入素材")
        import_btn.clicked.connect(self._import_dataset)
        proj_layout.addWidget(import_btn)

        # 素材预览
        self.素材_count_label = QLabel("素材: 0 张")
        proj_layout.addWidget(self.素材_count_label)

        # 素材网格预览
        self.素材_grid = QListWidget()
        self.素材_grid.setViewMode(QListWidget.IconMode)
        self.素材_grid.setIconSize(QSize(80, 80))
        self.素材_grid.setResizeMode(QListWidget.Adjust)
        self.素材_grid.setMaximumHeight(200)
        proj_layout.addWidget(self.素材_grid)

        layout.addWidget(proj_group)

        # 自动打标
        tag_group = QGroupBox("自动打标")
        tag_layout = QVBoxLayout(tag_group)

        self.tag_btn = QPushButton("🏷️ WD14自动打标")
        self.tag_btn.clicked.connect(self._auto_tag)
        tag_layout.addWidget(self.tag_btn)

        self.tag_progress = QProgressBar()
        self.tag_progress.setVisible(False)
        tag_layout.addWidget(self.tag_progress)

        layout.addWidget(tag_group)

        # 训练参数
        param_group = QGroupBox("训练参数")
        param_layout = QGridLayout(param_group)

        param_layout.addWidget(QLabel("基础模型:"), 0, 0)
        self.base_model_combo = QComboBox()
        self.base_model_combo.addItem("加载中...")
        param_layout.addWidget(self.base_model_combo, 0, 1)

        param_layout.addWidget(QLabel("网络类型:"), 1, 0)
        self.network_type_combo = QComboBox()
        self.network_type_combo.addItems(["LoRA", "LoCon", "LyCORIS"])
        param_layout.addWidget(self.network_type_combo, 1, 1)

        param_layout.addWidget(QLabel("Rank:"), 2, 0)
        self.rank_combo = QComboBox()
        self.rank_combo.addItems(["4", "8", "16", "32", "64", "128", "256"])
        self.rank_combo.setCurrentText("32")
        param_layout.addWidget(self.rank_combo, 2, 1)

        param_layout.addWidget(QLabel("UNet学习率:"), 3, 0)
        self.lr_unet_edit = QLineEdit("1e-4")
        param_layout.addWidget(self.lr_unet_edit, 3, 1)

        param_layout.addWidget(QLabel("TE学习率:"), 4, 0)
        self.lr_te_edit = QLineEdit("5e-5")
        param_layout.addWidget(self.lr_te_edit, 4, 1)

        param_layout.addWidget(QLabel("Epoch数:"), 5, 0)
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 100)
        self.epochs_spin.setValue(10)
        param_layout.addWidget(self.epochs_spin, 5, 1)

        param_layout.addWidget(QLabel("Batch Size:"), 6, 0)
        self.batch_spin = QComboBox()
        self.batch_spin.addItems(["1", "2", "4", "8"])
        param_layout.addWidget(self.batch_spin, 6, 1)

        param_layout.addWidget(QLabel("分辨率:"), 7, 0)
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["512", "768", "自定义"])
        param_layout.addWidget(self.resolution_combo, 7, 1)

        param_layout.addWidget(QLabel("优化器:"), 8, 0)
        self.optimizer_combo = QComboBox()
        self.optimizer_combo.addItems(["AdamW8bit", "Prodigy", "Lion", "SGD"])
        param_layout.addWidget(self.optimizer_combo, 8, 1)

        param_layout.addWidget(QLabel("混合精度:"), 9, 0)
        self.precision_combo = QComboBox()
        self.precision_combo.addItems(["fp16", "bf16", "no"])
        param_layout.addWidget(self.precision_combo, 9, 1)

        param_layout.addWidget(QLabel("保存间隔(步):"), 10, 0)
        self.save_interval_spin = QSpinBox()
        self.save_interval_spin.setRange(50, 5000)
        self.save_interval_spin.setValue(500)
        param_layout.addWidget(self.save_interval_spin, 10, 1)

        layout.addWidget(param_group)

        # MiMo辅助
        mimo_group = QGroupBox("MiMo API 辅助")
        mimo_layout = QVBoxLayout(mimo_group)

        suggest_btn = QPushButton("💡 AI推荐参数")
        suggest_btn.clicked.connect(self._suggest_params)
        mimo_layout.addWidget(suggest_btn)

        trigger_btn = QPushButton("🔑 生成触发词")
        trigger_btn.clicked.connect(self._generate_triggers)
        mimo_layout.addWidget(trigger_btn)

        self.mimo_result_label = QLabel("")
        self.mimo_result_label.setWordWrap(True)
        mimo_layout.addWidget(self.mimo_result_label)

        layout.addWidget(mimo_group)

        layout.addStretch()
        return panel

    def _create_training_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 控制按钮
        ctrl_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ 开始训练")
        self.start_btn.setProperty("gold", True)
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self._start_training)
        ctrl_layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("⏸ 暂停")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._pause_training)
        ctrl_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_training)
        ctrl_layout.addWidget(self.stop_btn)

        layout.addLayout(ctrl_layout)

        # 进度
        self.train_progress = QProgressBar()
        layout.addWidget(self.train_progress)

        # 状态信息
        status_layout = QHBoxLayout()
        self.step_label = QLabel("步骤: 0/0")
        status_layout.addWidget(self.step_label)
        self.time_label = QLabel("耗时: 00:00:00")
        status_layout.addWidget(self.time_label)
        self.loss_label = QLabel("Loss: --")
        status_layout.addWidget(self.loss_label)
        layout.addLayout(status_layout)

        # Loss曲线（占位）
        self.loss_chart_label = QLabel("Loss曲线将在训练开始后显示")
        self.loss_chart_label.setAlignment(Qt.AlignCenter)
        self.loss_chart_label.setMinimumHeight(200)
        self.loss_chart_label.setStyleSheet(
            "background-color: #252525; border: 1px solid #333; border-radius: 8px;"
        )
        layout.addWidget(self.loss_chart_label, 1)

        # 预览图
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(QLabel("训练预览:"))
        self.preview_label = QLabel("训练过程中将生成预览图")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        self.preview_label.setStyleSheet(
            "background-color: #252525; border: 1px solid #333; border-radius: 8px;"
        )
        preview_layout.addWidget(self.preview_label)
        layout.addLayout(preview_layout)

        # 日志输出
        layout.addWidget(QLabel("训练日志:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("font-family: 'Consolas', monospace; font-size: 11px;")
        layout.addWidget(self.log_text)

        # 训练历史
        layout.addWidget(QLabel("训练历史:"))
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(
            ["项目", "模型", "Rank", "Epochs", "Loss", "时间"]
        )
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self._load_history()
        layout.addWidget(self.history_table)

        return panel

    def _load_history(self):
        """加载训练历史"""
        history = db.get_training_history(20)
        self.history_table.setRowCount(len(history))
        for i, record in enumerate(history):
            self.history_table.setItem(i, 0, QTableWidgetItem(record.get("project_name", "")))
            self.history_table.setItem(i, 1, QTableWidgetItem(record.get("base_model", "")))
            self.history_table.setItem(i, 2, QTableWidgetItem(str(record.get("rank", ""))))
            self.history_table.setItem(i, 3, QTableWidgetItem(str(record.get("epochs", ""))))
            self.history_table.setItem(i, 4, QTableWidgetItem(f"{record.get('final_loss', 0):.4f}"))
            self.history_table.setItem(i, 5, QTableWidgetItem(record.get("created_at", "")[:16]))

    def _import_dataset(self):
        """导入素材"""
        project_name = self.project_name_edit.text().strip()
        if not project_name:
            QMessageBox.warning(self, "提示", "请先输入项目名称")
            return

        dir_path = QFileDialog.getExistingDirectory(self, "选择素材文件夹")
        if not dir_path:
            return

        self._import_thread = ImportThread(dir_path, project_name)
        self._import_thread.progress.connect(self._on_import_progress)
        self._import_thread.finished.connect(self._on_import_finished)
        self._import_thread.start()

    def _on_import_progress(self, current, total, filename):
        self.素材_count_label.setText(f"导入中: {current}/{total}")

    def _on_import_finished(self, result):
        count = result.get("imported", 0)
        self.素材_count_label.setText(f"素材: {count} 张")
        QMessageBox.information(self, "导入完成", f"成功导入 {count} 张素材")

    def _auto_tag(self):
        """自动打标"""
        project_name = self.project_name_edit.text().strip()
        if not project_name:
            QMessageBox.warning(self, "提示", "请先输入项目名称")
            return

        self.tag_progress.setVisible(True)
        self.tag_progress.setRange(0, 0)
        self.tag_btn.setEnabled(False)

        self._tag_thread = TagThread(project_name)
        self._tag_thread.progress.connect(self._on_tag_progress)
        self._tag_thread.finished.connect(self._on_tag_finished)
        self._tag_thread.start()

    def _on_tag_progress(self, current, total, filename, tags):
        self.tag_progress.setRange(0, total)
        self.tag_progress.setValue(current)

    def _on_tag_finished(self, result):
        self.tag_progress.setVisible(False)
        self.tag_btn.setEnabled(True)
        count = result.get("tagged", 0)
        QMessageBox.information(self, "打标完成", f"成功打标 {count} 张图片")

    def _start_training(self):
        """开始训练"""
        project_name = self.project_name_edit.text().strip()
        if not project_name:
            QMessageBox.warning(self, "提示", "请先输入项目名称")
            return

        params = {
            "project_name": project_name,
            "base_model": self.base_model_combo.currentText(),
            "network_type": self.network_type_combo.currentText(),
            "rank": int(self.rank_combo.currentText()),
            "learning_rate_unet": float(self.lr_unet_edit.text()),
            "learning_rate_te": float(self.lr_te_edit.text()),
            "epochs": self.epochs_spin.value(),
            "batch_size": int(self.batch_spin.currentText()),
            "resolution": int(self.resolution_combo.currentText()),
            "optimizer": self.optimizer_combo.currentText(),
            "mixed_precision": self.precision_combo.currentText(),
            "save_every_n_steps": self.save_interval_spin.value(),
            "preview_every_n_steps": 100,
        }

        trainer.set_callback("log", lambda msg: self.log_text.append(msg))
        trainer.set_callback("progress", lambda c, t: self.train_progress.setValue(int(c / t * 100) if t else 0))
        trainer.set_callback("error", lambda msg: QMessageBox.critical(self, "训练错误", msg))

        try:
            trainer.start_training(params)
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "启动失败", str(e))

    def _pause_training(self):
        if trainer.is_paused:
            trainer.resume_training()
            self.pause_btn.setText("⏸ 暂停")
        else:
            trainer.pause_training()
            self.pause_btn.setText("▶ 继续")

    def _stop_training(self):
        trainer.stop_training()
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

    def _suggest_params(self):
        """AI推荐训练参数"""
        try:
            project_name = self.project_name_edit.text().strip()
            raw_dir = pm.get_dataset_dir(project_name, "raw") if project_name else ""
            img_count = 0
            if os.path.exists(raw_dir):
                exts = {".jpg", ".png", ".webp"}
                img_count = len([f for f in os.listdir(raw_dir) if os.path.splitext(f)[1].lower() in exts])

            info = {"image_count": img_count, "project_name": project_name}
            result = mimo_api.suggest_training_params(info)
            if result:
                self.rank_combo.setCurrentText(str(result.get("rank", 32)))
                self.lr_unet_edit.setText(str(result.get("learning_rate_unet", "1e-4")))
                self.lr_te_edit.setText(str(result.get("learning_rate_te", "5e-5")))
                self.epochs_spin.setValue(result.get("epochs", 10))
                notes = result.get("notes", "")
                self.mimo_result_label.setText(f"✅ 参数已应用\n{notes}")
        except Exception as e:
            self.mimo_result_label.setText(f"❌ {e}")

    def _generate_triggers(self):
        """生成触发词"""
        try:
            project_name = self.project_name_edit.text().strip()
            if not project_name:
                self.mimo_result_label.setText("请先输入项目名称")
                return
            result = mimo_api.generate_trigger_words([project_name])
            triggers = result.get("trigger_words", [])
            template = result.get("prompt_template", "")
            self.mimo_result_label.setText(
                f"触发词: {', '.join(triggers)}\n模板: {template}"
            )
        except Exception as e:
            self.mimo_result_label.setText(f"❌ {e}")
