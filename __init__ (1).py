# -*- coding: utf-8 -*-
"""
素材爬虫界面
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QSlider,
    QCheckBox, QGroupBox, QScrollArea, QFileDialog, QProgressBar,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QPixmap, QImage

from core.config_manager import config
from core.crawler import crawler
from core.mimo_api import mimo_api
from core.image_utils import load_image
from utils.path_manager import pm
from utils.logger import logger


class CrawlThread(QThread):
    progress = Signal(int, str)
    image_found = Signal(object, int)
    log = Signal(str)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, keywords, sites, max_total, source_image=None):
        super().__init__()
        self.keywords = keywords
        self.sites = sites
        self.max_total = max_total
        self.source_image = source_image

    def run(self):
        crawler.set_callback("log", lambda msg: self.log.emit(msg))
        crawler.set_callback("image_found", lambda r, c: self.image_found.emit(r, c))
        crawler.set_callback("finish", lambda results: self.finished.emit(results))
        crawler.set_callback("error", lambda msg: self.error.emit(msg))
        crawler.crawl_by_keywords(self.keywords, self.sites, self.max_total, self.source_image)


class CrawlTab(QWidget):
    """素材爬虫标签页"""

    def __init__(self):
        super().__init__()
        self._crawl_results = []
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # 左侧：配置
        left = self._create_config_panel()
        left_scroll = QScrollArea()
        left_scroll.setWidget(left)
        left_scroll.setWidgetResizable(True)
        left_scroll.setFixedWidth(350)

        # 右侧：结果
        right = self._create_result_panel()

        layout.addWidget(left_scroll)
        layout.addWidget(right, 1)

    def _create_config_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        # 搜索关键词
        kw_group = QGroupBox("搜索关键词")
        kw_layout = QVBoxLayout(kw_group)

        kw_layout.addWidget(QLabel("关键词（每行一个）:"))
        self.keyword_edit = QTextEdit()
        self.keyword_edit.setPlaceholderText("四爪镶嵌翡翠戒指\nprong setting jadeite ring")
        self.keyword_edit.setMaximumHeight(100)
        kw_layout.addWidget(self.keyword_edit)

        # MiMo生成关键词
        mimo_kw_layout = QHBoxLayout()
        self.source_image_path = ""
        self.source_label = QLabel("未选择源图")
        mimo_kw_layout.addWidget(self.source_label)
        select_btn = QPushButton("选择")
        select_btn.setProperty("secondary", True)
        select_btn.clicked.connect(self._select_source_image)
        mimo_kw_layout.addWidget(select_btn)
        kw_layout.addLayout(mimo_kw_layout)

        gen_kw_btn = QPushButton("🤖 AI生成关键词")
        gen_kw_btn.clicked.connect(self._generate_keywords)
        kw_layout.addWidget(gen_kw_btn)

        layout.addWidget(kw_group)

        # 目标网站
        site_group = QGroupBox("目标网站")
        site_layout = QVBoxLayout(site_group)

        self.site_checks = {}
        sites = [
            ("google_images", "Google 图片", True),
            ("bing_images", "Bing 图片", True),
            ("pinterest", "Pinterest", True),
            ("xhs", "小红书", False),
            ("taobao", "淘宝/天猫", False),
            ("etsy", "Etsy", True),
            ("behance", "Behance", True),
            ("dribbble", "Dribbble", False),
        ]
        for key, name, default in sites:
            cb = QCheckBox(name)
            cb.setChecked(default)
            self.site_checks[key] = cb
            site_layout.addWidget(cb)

        layout.addWidget(site_group)

        # 爬取配置
        cfg_group = QGroupBox("爬取配置")
        cfg_layout = QGridLayout(cfg_group)

        cfg_layout.addWidget(QLabel("最大数量:"), 0, 0)
        self.max_spin = QSpinBox()
        self.max_spin.setRange(10, 2000)
        self.max_spin.setValue(200)
        cfg_layout.addWidget(self.max_spin, 0, 1)

        cfg_layout.addWidget(QLabel("请求间隔(秒):"), 1, 0)
        interval_layout = QHBoxLayout()
        self.interval_min = QDoubleSpinBox()
        self.interval_min.setRange(0.5, 30)
        self.interval_min.setValue(2.0)
        interval_layout.addWidget(self.interval_min)
        interval_layout.addWidget(QLabel("~"))
        self.interval_max = QDoubleSpinBox()
        self.interval_max.setRange(1, 60)
        self.interval_max.setValue(5.0)
        interval_layout.addWidget(self.interval_max)
        cfg_layout.addLayout(interval_layout, 1, 1)

        cfg_layout.addWidget(QLabel("最小分辨率:"), 2, 0)
        res_layout = QHBoxLayout()
        self.min_w_spin = QSpinBox()
        self.min_w_spin.setRange(100, 4096)
        self.min_w_spin.setValue(800)
        res_layout.addWidget(self.min_w_spin)
        res_layout.addWidget(QLabel("x"))
        self.min_h_spin = QSpinBox()
        self.min_h_spin.setRange(100, 4096)
        self.min_h_spin.setValue(600)
        res_layout.addWidget(self.min_h_spin)
        cfg_layout.addLayout(res_layout, 2, 1)

        cfg_layout.addWidget(QLabel("相似度阈值:"), 3, 0)
        self.sim_spin = QSpinBox()
        self.sim_spin.setRange(0, 100)
        self.sim_spin.setValue(60)
        self.sim_spin.setSuffix("%")
        cfg_layout.addWidget(self.sim_spin, 3, 1)

        layout.addWidget(cfg_group)

        # 控制按钮
        ctrl_layout = QHBoxLayout()
        self.start_btn = QPushButton("🕷️ 开始爬取")
        self.start_btn.setProperty("gold", True)
        self.start_btn.clicked.connect(self._start_crawl)
        ctrl_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_crawl)
        ctrl_layout.addWidget(self.stop_btn)

        layout.addLayout(ctrl_layout)

        # 进度
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 日志
        layout.addWidget(QLabel("爬取日志:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("font-family: 'Consolas', monospace; font-size: 11px;")
        layout.addWidget(self.log_text)

        layout.addStretch()
        return panel

    def _create_result_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 工具栏
        toolbar = QHBoxLayout()
        self.result_count = QLabel("已爬取: 0 张")
        toolbar.addWidget(self.result_count)
        toolbar.addStretch()

        select_all_btn = QPushButton("全选")
        select_all_btn.setProperty("secondary", True)
        select_all_btn.clicked.connect(self._select_all)
        toolbar.addWidget(select_all_btn)

        deselect_btn = QPushButton("取消全选")
        deselect_btn.setProperty("secondary", True)
        deselect_btn.clicked.connect(self._deselect_all)
        toolbar.addWidget(deselect_btn)

        export_btn = QPushButton("📤 导出选中")
        export_btn.clicked.connect(self._export_selected)
        toolbar.addWidget(export_btn)

        layout.addLayout(toolbar)

        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels(
            ["选择", "缩略图", "来源", "尺寸", "相似度", "路径"]
        )
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.setIconSize(QSize(80, 80))
        self.result_table.verticalHeader().setDefaultSectionSize(80)
        layout.addWidget(self.result_table, 1)

        return panel

    def _select_source_image(self):
        """选择源图片（用于以图搜图）"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择源图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if path:
            self.source_image_path = path
            self.source_label.setText(os.path.basename(path))

    def _generate_keywords(self):
        """AI生成搜索关键词"""
        if not self.source_image_path:
            QMessageBox.warning(self, "提示", "请先选择源图片")
            return
        try:
            result = mimo_api.search_keywords_from_image(self.source_image_path)
            all_kw = []
            all_kw.extend(result.get("cn_keywords", []))
            all_kw.extend(result.get("en_keywords", []))
            if all_kw:
                self.keyword_edit.setPlainText("\n".join(all_kw))
        except Exception as e:
            QMessageBox.warning(self, "错误", f"生成关键词失败: {e}")

    def _start_crawl(self):
        """开始爬取"""
        text = self.keyword_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请输入搜索关键词")
            return

        keywords = [kw.strip() for kw in text.split("\n") if kw.strip()]
        sites = [key for key, cb in self.site_checks.items() if cb.isChecked()]

        if not sites:
            QMessageBox.warning(self, "提示", "请至少选择一个目标网站")
            return

        # 更新配置
        config.set("crawler", "request_interval_min", self.interval_min.value())
        config.set("crawler", "request_interval_max", self.interval_max.value())
        config.set("crawler", "min_resolution_width", self.min_w_spin.value())
        config.set("crawler", "min_resolution_height", self.min_h_spin.value())
        config.set("crawler", "similarity_threshold", self.sim_spin.value())

        source_img = None
        if self.source_image_path:
            source_img = load_image(self.source_image_path)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.log_text.clear()

        self._crawl_thread = CrawlThread(keywords, sites, self.max_spin.value(), source_img)
        self._crawl_thread.log.connect(self._on_crawl_log)
        self._crawl_thread.image_found.connect(self._on_image_found)
        self._crawl_thread.finished.connect(self._on_crawl_finished)
        self._crawl_thread.error.connect(self._on_crawl_error)
        self._crawl_thread.start()

    def _stop_crawl(self):
        """停止爬取"""
        crawler.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

    def _on_crawl_log(self, msg):
        self.log_text.append(msg)

    def _on_image_found(self, result, count):
        self._crawl_results.append(result)
        self.result_count.setText(f"已爬取: {count} 张")

        # 添加到表格
        row = self.result_table.rowCount()
        self.result_table.setRowCount(row + 1)

        # 选择框
        from PySide6.QtWidgets import QCheckBox as QCB
        cb = QCB()
        cb.setChecked(True)
        self.result_table.setCellWidget(row, 0, cb)

        # 缩略图
        try:
            from PIL import Image as PILImage
            img = PILImage.open(result.local_path).convert("RGB")
            img.thumbnail((75, 75))
            data = img.tobytes("raw", "RGB")
            qimg = QImage(data, img.width, img.height, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            thumb_label = QLabel()
            thumb_label.setPixmap(pixmap)
            thumb_label.setAlignment(Qt.AlignCenter)
            self.result_table.setCellWidget(row, 1, thumb_label)
        except Exception:
            pass

        self.result_table.setItem(row, 2, QTableWidgetItem(result.source_site))
        self.result_table.setItem(row, 3, QTableWidgetItem(f"{result.width}x{result.height}"))
        self.result_table.setItem(row, 4, QTableWidgetItem(f"{result.similarity:.1f}%"))
        self.result_table.setItem(row, 5, QTableWidgetItem(result.local_path))

    def _on_crawl_finished(self, results):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.log_text.append(f"爬取完成，共 {len(results)} 张图片")

    def _on_crawl_error(self, msg):
        self.log_text.append(f"错误: {msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

    def _select_all(self):
        for row in range(self.result_table.rowCount()):
            cb = self.result_table.cellWidget(row, 0)
            if cb:
                cb.setChecked(True)

    def _deselect_all(self):
        for row in range(self.result_table.rowCount()):
            cb = self.result_table.cellWidget(row, 0)
            if cb:
                cb.setChecked(False)

    def _export_selected(self):
        """导出选中的图片"""
        selected = []
        for row in range(self.result_table.rowCount()):
            cb = self.result_table.cellWidget(row, 0)
            if cb and cb.isChecked():
                path_item = self.result_table.item(row, 5)
                if path_item:
                    selected.append(path_item.text())

        if not selected:
            QMessageBox.information(self, "导出", "没有选中的图片")
            return

        export_dir = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not export_dir:
            return

        import shutil
        for src in selected:
            try:
                shutil.copy2(src, export_dir)
            except Exception as e:
                logger.error(f"导出失败 {src}: {e}")

        QMessageBox.information(self, "导出完成", f"已导出 {len(selected)} 张图片到:\n{export_dir}")
