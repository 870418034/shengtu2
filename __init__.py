# -*- coding: utf-8 -*-
"""
画板组件 - 支持鼠标/手绘板绘制草图，用于ControlNet Scribble模式
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QSlider, QColorDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor


class Sketchpad(QWidget):
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
