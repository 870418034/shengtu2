# -*- coding: utf-8 -*-
"""
图片查看器组件 - 支持缩放、拖拽、适应窗口
"""
from PySide6.QtWidgets import QLabel, QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage


class ImageViewer(QWidget):
    """图片查看器"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel("暂无图片")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background-color: #252525;")

        scroll = QScrollArea()
        scroll.setWidget(self.label)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        # 工具栏
        toolbar = QHBoxLayout()
        fit_btn = QPushButton("适应窗口")
        fit_btn.setProperty("secondary", True)
        toolbar.addWidget(fit_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

    def set_image(self, pixmap: QPixmap):
        """设置显示图片"""
        self.label.setPixmap(pixmap)
