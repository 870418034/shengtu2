# -*- coding: utf-8 -*-
"""
提示词编辑器组件 - 支持标签快速插入、字符计数、清空
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal


class PromptEditor(QWidget):
    """提示词编辑器，支持标签快速插入"""

    textChanged = Signal()

    def __init__(self, placeholder="输入提示词...", max_height=120):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(placeholder)
        self.text_edit.setMaximumHeight(max_height)
        self.text_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.text_edit)

        # 快速操作栏
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)

        self.char_count = QLabel("0 字符 | 0 标签")
        self.char_count.setProperty("color", "status")
        toolbar.addWidget(self.char_count)
        toolbar.addStretch()

        copy_btn = QPushButton("📋 复制")
        copy_btn.setProperty("secondary", True)
        copy_btn.setMaximumWidth(60)
        copy_btn.clicked.connect(self._copy_text)
        toolbar.addWidget(copy_btn)

        clear_btn = QPushButton("清空")
        clear_btn.setProperty("secondary", True)
        clear_btn.setMaximumWidth(50)
        clear_btn.clicked.connect(self.text_edit.clear)
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)

    def _on_text_changed(self):
        text = self.text_edit.toPlainText()
        tag_count = len([t.strip() for t in text.split(",") if t.strip()]) if text.strip() else 0
        self.char_count.setText(f"{len(text)} 字符 | {tag_count} 标签")
        self.textChanged.emit()

    def _copy_text(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.text_edit.toPlainText())

    def get_text(self) -> str:
        return self.text_edit.toPlainText().strip()

    def set_text(self, text: str):
        self.text_edit.setPlainText(text)

    def insert_tag(self, tag: str):
        """在末尾追加标签"""
        current = self.text_edit.toPlainText().strip()
        if current:
            self.text_edit.setPlainText(f"{current}, {tag}")
        else:
            self.text_edit.setPlainText(tag)
        # 滚动到底部
        sb = self.text_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def insert_at_cursor(self, text: str):
        """在光标处插入文本"""
        self.text_edit.insertPlainText(text)

    def clear(self):
        self.text_edit.clear()


class TagBar(QWidget):
    """标签快速插入栏"""

    tagClicked = Signal(str)

    def __init__(self, tags: list = None):
        """
        tags: [("显示名", "实际标签"), ...]
        """
        super().__init__()
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)

        if tags:
            self.set_tags(tags)

    def set_tags(self, tags: list):
        """设置标签按钮列表"""
        # 清除旧按钮
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for display, value in tags:
            btn = QPushButton(display)
            btn.setProperty("secondary", True)
            btn.setMaximumHeight(26)
            btn.setToolTip(value)
            btn.clicked.connect(lambda checked, v=value: self.tagClicked.emit(v))
            self._layout.addWidget(btn)

        self._layout.addStretch()
