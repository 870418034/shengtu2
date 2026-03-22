# -*- coding: utf-8 -*-
"""
批量生产模式 - 参数矩阵批量生成（占位实现）
"""
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class BatchTab(QWidget):
    """批量生产标签页"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("批量生产模式 - 开发中")
        label.setAlignment(0x0084)  # Qt.AlignCenter
        layout.addWidget(label)
