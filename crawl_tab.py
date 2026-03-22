# -*- coding: utf-8 -*-
"""
设计图库管理界面 - SQLite数据库驱动
"""
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QComboBox, QSpinBox, QSlider, QCheckBox,
    QGroupBox, QScrollArea, QFileDialog, QListWidget, QListWidgetItem,
    QMessageBox, QHeaderView, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QSplitter, QFrame
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QImage

from core.config_manager import config
from core.database import db
from core.image_utils import load_image
from utils.path_manager import pm
from utils.logger import logger


class GalleryTab(QWidget):
    """设计图库标签页"""

    def __init__(self):
        super().__init__()
        self._designs = []
        self._current_design = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # 搜索栏
        search_layout = QHBoxLayout()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索关键词...")
        self.search_edit.returnPressed.connect(self._search)
        search_layout.addWidget(self.search_edit)

        search_btn = QPushButton("🔍 搜索")
        search_btn.clicked.connect(self._search)
        search_layout.addWidget(search_btn)

        search_layout.addWidget(QLabel("筛选:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "已收藏", "评分≥4", "评分≥3"])
        self.filter_combo.currentIndexChanged.connect(self._search)
        search_layout.addWidget(self.filter_combo)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["时间↓", "时间↑", "评分↓", "评分↑"])
        self.sort_combo.currentIndexChanged.connect(self._search)
        search_layout.addWidget(self.sort_combo)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setProperty("secondary", True)
        refresh_btn.clicked.connect(self._load_designs)
        search_layout.addWidget(refresh_btn)

        layout.addLayout(search_layout)

        # 主内容区：左侧网格 + 右侧详情
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：图库网格
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        self.gallery_grid = QListWidget()
        self.gallery_grid.setViewMode(QListWidget.IconMode)
        self.gallery_grid.setIconSize(QSize(180, 180))
        self.gallery_grid.setResizeMode(QListWidget.Adjust)
        self.gallery_grid.setSpacing(8)
        self.gallery_grid.itemClicked.connect(self._on_item_clicked)
        self.gallery_grid.itemDoubleClicked.connect(self._on_item_double_clicked)
        left_layout.addWidget(self.gallery_grid)

        # 分页
        page_layout = QHBoxLayout()
        self.page_label = QLabel("第 1 页")
        page_layout.addWidget(self.page_label)
        page_layout.addStretch()
        prev_btn = QPushButton("◀ 上一页")
        prev_btn.setProperty("secondary", True)
        prev_btn.clicked.connect(self._prev_page)
        page_layout.addWidget(prev_btn)
        next_btn = QPushButton("下一页 ▶")
        next_btn.setProperty("secondary", True)
        next_btn.clicked.connect(self._next_page)
        page_layout.addWidget(next_btn)
        left_layout.addLayout(page_layout)

        # 批量操作
        batch_layout = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        select_all_btn.setProperty("secondary", True)
        batch_layout.addWidget(select_all_btn)
        export_btn = QPushButton("📤 导出选中")
        export_btn.setProperty("secondary", True)
        export_btn.clicked.connect(self._export_selected)
        batch_layout.addWidget(export_btn)
        delete_btn = QPushButton("🗑️ 删除选中")
        delete_btn.setProperty("secondary", True)
        delete_btn.clicked.connect(self._delete_selected)
        batch_layout.addWidget(delete_btn)
        left_layout.addLayout(batch_layout)

        splitter.addWidget(left_widget)

        # 右侧：详情面板
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_widget.setFixedWidth(350)

        # 预览
        self.detail_preview = QLabel("点击图片查看详情")
        self.detail_preview.setAlignment(Qt.AlignCenter)
        self.detail_preview.setMinimumHeight(250)
        self.detail_preview.setStyleSheet(
            "background-color: #252525; border: 1px solid #333; border-radius: 8px;"
        )
        right_layout.addWidget(self.detail_preview)

        # 评分
        rating_layout = QHBoxLayout()
        rating_layout.addWidget(QLabel("评分:"))
        self.rating_buttons = []
        for i in range(1, 6):
            btn = QPushButton("★")
            btn.setProperty("secondary", True)
            btn.setFixedWidth(35)
            btn.clicked.connect(lambda checked, r=i: self._set_rating(r))
            rating_layout.addWidget(btn)
            self.rating_buttons.append(btn)
        right_layout.addLayout(rating_layout)

        # 收藏
        self.fav_btn = QPushButton("♡ 收藏")
        self.fav_btn.setProperty("secondary", True)
        self.fav_btn.clicked.connect(self._toggle_favorite)
        right_layout.addWidget(self.fav_btn)

        # 信息
        right_layout.addWidget(QLabel("提示词:"))
        self.detail_prompt = QTextEdit()
        self.detail_prompt.setReadOnly(True)
        self.detail_prompt.setMaximumHeight(100)
        right_layout.addWidget(self.detail_prompt)

        # 复制提示词
        copy_btn = QPushButton("📋 复制提示词")
        copy_btn.setProperty("secondary", True)
        copy_btn.clicked.connect(self._copy_prompt)
        right_layout.addWidget(copy_btn)

        # 标签
        right_layout.addWidget(QLabel("标签:"))
        self.detail_tags = QLineEdit()
        self.detail_tags.setPlaceholderText("用逗号分隔")
        self.detail_tags.editingFinished.connect(self._save_tags)
        right_layout.addWidget(self.detail_tags)

        # 参数信息
        self.detail_params = QLabel("")
        self.detail_params.setWordWrap(True)
        self.detail_params.setProperty("color", "status")
        right_layout.addWidget(self.detail_params)

        right_layout.addStretch()
        splitter.addWidget(right_widget)

        splitter.setSizes([800, 350])
        layout.addWidget(splitter, 1)

        # 统计信息
        self.stats_label = QLabel("")
        self.stats_label.setProperty("color", "status")
        layout.addWidget(self.stats_label)

        # 加载数据
        self._page = 0
        self._page_size = 50
        self._load_designs()

    def _load_designs(self):
        """加载设计图"""
        favorite = None
        min_rating = 0
        filter_text = self.filter_combo.currentText()
        if filter_text == "已收藏":
            favorite = 1
        elif filter_text == "评分≥4":
            min_rating = 4
        elif filter_text == "评分≥3":
            min_rating = 3

        sort_map = {"时间↓": ("created_at", "DESC"), "时间↑": ("created_at", "ASC"),
                    "评分↓": ("rating", "DESC"), "评分↑": ("rating", "ASC")}
        sort_by, sort_order = sort_map.get(self.sort_combo.currentText(), ("created_at", "DESC"))

        self._designs = db.search_designs(
            keyword=self.search_edit.text().strip(),
            favorite=favorite,
            min_rating=min_rating,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=self._page_size,
            offset=self._page * self._page_size,
        )

        self._show_gallery()
        self._update_stats()

    def _show_gallery(self):
        """显示图库网格"""
        self.gallery_grid.clear()
        for design in self._designs:
            item = QListWidgetItem()
            filepath = design.get("filepath", "")
            if os.path.exists(filepath):
                pixmap = QPixmap(filepath)
                pixmap = pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item.setIcon(pixmap)
            else:
                item.setText("文件缺失")
            item.setData(Qt.UserRole, design)
            item.setToolTip(design.get("filename", ""))

            # 收藏标记
            if design.get("favorite"):
                item.setText("⭐")

            self.gallery_grid.addItem(item)

    def _update_stats(self):
        """更新统计"""
        total = len(self._designs)
        fav_count = sum(1 for d in self._designs if d.get("favorite"))
        self.stats_label.setText(
            f"共 {total} 张设计 | 第 {self._page + 1} 页 | 收藏 {fav_count} 张"
        )
        self.page_label.setText(f"第 {self._page + 1} 页")

    def _on_item_clicked(self, item):
        """点击项目"""
        design = item.data(Qt.UserRole)
        if design:
            self._current_design = design
            self._show_detail(design)

    def _on_item_double_clicked(self, item):
        """双击放大预览"""
        design = item.data(Qt.UserRole)
        if design:
            filepath = design.get("filepath", "")
            if os.path.exists(filepath):
                QMessageBox.information(self, "预览", f"文件路径:\n{filepath}")

    def _show_detail(self, design):
        """显示详情"""
        filepath = design.get("filepath", "")
        if os.path.exists(filepath):
            pixmap = QPixmap(filepath).scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.detail_preview.setPixmap(pixmap)

        # 提示词
        prompt = design.get("prompt", "")
        self.detail_prompt.setPlainText(prompt)

        # 评分
        rating = design.get("rating", 0)
        for i, btn in enumerate(self.rating_buttons):
            btn.setText("★" if i < rating else "☆")

        # 收藏
        fav = design.get("favorite", 0)
        self.fav_btn.setText("♥ 已收藏" if fav else "♡ 收藏")

        # 标签
        tags = design.get("tags", [])
        if isinstance(tags, list):
            self.detail_tags.setText(", ".join(tags))

        # 参数
        params = design.get("parameters", {})
        if isinstance(params, dict):
            info_parts = []
            for key in ["sampler_name", "steps", "cfg_scale", "seed", "width", "height"]:
                if key in params:
                    info_parts.append(f"{key}: {params[key]}")
            self.detail_params.setText("\n".join(info_parts))

    def _search(self):
        self._page = 0
        self._load_designs()

    def _prev_page(self):
        if self._page > 0:
            self._page -= 1
            self._load_designs()

    def _next_page(self):
        self._page += 1
        self._load_designs()

    def _set_rating(self, rating):
        """设置评分"""
        if self._current_design:
            db.update_design(self._current_design["id"], {"rating": rating})
            self._current_design["rating"] = rating
            self._show_detail(self._current_design)

    def _toggle_favorite(self):
        """切换收藏"""
        if self._current_design:
            new_fav = 0 if self._current_design.get("favorite") else 1
            db.update_design(self._current_design["id"], {"favorite": new_fav})
            self._current_design["favorite"] = new_fav
            self._show_detail(self._current_design)

    def _save_tags(self):
        """保存标签"""
        if self._current_design:
            tags_text = self.detail_tags.text().strip()
            tags = [t.strip() for t in tags_text.split(",") if t.strip()]
            db.update_design(self._current_design["id"], {"tags": tags})

    def _copy_prompt(self):
        """复制提示词"""
        prompt = self.detail_prompt.toPlainText()
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(prompt)

    def _export_selected(self):
        """导出选中"""
        export_dir = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not export_dir:
            return
        import shutil
        count = 0
        for i in range(self.gallery_grid.count()):
            item = self.gallery_grid.item(i)
            design = item.data(Qt.UserRole)
            if design and design.get("filepath"):
                try:
                    shutil.copy2(design["filepath"], export_dir)
                    count += 1
                except Exception:
                    pass
        QMessageBox.information(self, "导出完成", f"已导出 {count} 张图片")

    def _delete_selected(self):
        """删除选中"""
        reply = QMessageBox.question(self, "确认删除", "确定要删除选中的设计图吗？")
        if reply != QMessageBox.Yes:
            return
        for i in range(self.gallery_grid.count()):
            item = self.gallery_grid.item(i)
            design = item.data(Qt.UserRole)
            if design:
                db.delete_design(design["id"])
        self._load_designs()
