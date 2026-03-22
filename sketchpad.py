# -*- coding: utf-8 -*-
"""
主窗口 - 深色专业主题，类似Figma/Blender暗色工作区
"""
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QToolBar, QStatusBar, QMenuBar, QMenu, QLabel, QPushButton,
    QSplitter, QFrame, QApplication, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence, QPixmap

from core.config_manager import config
from core.sd_api import sd_api
from core.database import db
from utils.path_manager import pm
from utils.logger import logger

from ui.generate_tab import GenerateTab
from ui.train_tab import TrainTab
from ui.crawl_tab import CrawlTab
from ui.variant_tab import VariantTab
from ui.assistant_tab import AssistantTab
from ui.gallery_tab import GalleryTab
from ui.batch_tab import BatchTab
from ui.settings_dialog import SettingsDialog


# 样式表
DARK_STYLESHEET = """
QMainWindow {
    background-color: #1a1a1a;
    color: #e0e0e0;
}
QWidget {
    background-color: #1a1a1a;
    color: #e0e0e0;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #333;
    background-color: #1e1e1e;
}
QTabBar::tab {
    background-color: #2a2a2a;
    color: #aaa;
    padding: 8px 16px;
    border: 1px solid #333;
    border-bottom: none;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #1e1e1e;
    color: #c9a84c;
    border-bottom: 2px solid #c9a84c;
}
QTabBar::tab:hover {
    background-color: #333;
    color: #e0e0e0;
}
QPushButton {
    background-color: #2d5a3d;
    color: #e0e0e0;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #3a7250;
}
QPushButton:pressed {
    background-color: #1e3d29;
}
QPushButton:disabled {
    background-color: #444;
    color: #666;
}
QPushButton[secondary="true"] {
    background-color: #333;
    border: 1px solid #555;
}
QPushButton[secondary="true"]:hover {
    background-color: #444;
}
QPushButton[gold="true"] {
    background-color: #8b6914;
}
QPushButton[gold="true"]:hover {
    background-color: #a67d1a;
}
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #252525;
    color: #e0e0e0;
    border: 1px solid #444;
    padding: 6px 10px;
    border-radius: 4px;
}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #2d5a3d;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #252525;
    color: #e0e0e0;
    selection-background-color: #2d5a3d;
}
QSlider::groove:horizontal {
    background: #333;
    height: 6px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #2d5a3d;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #3a7250;
}
QProgressBar {
    background-color: #333;
    border-radius: 4px;
    text-align: center;
    color: #e0e0e0;
}
QProgressBar::chunk {
    background-color: #2d5a3d;
    border-radius: 4px;
}
QGroupBox {
    border: 1px solid #444;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    color: #c9a84c;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QScrollArea {
    border: none;
}
QScrollBar:vertical {
    background: #1a1a1a;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #444;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #555;
}
QLabel[color="gold"] {
    color: #c9a84c;
    font-weight: bold;
}
QLabel[color="green"] {
    color: #2d5a3d;
}
QLabel[color="status"] {
    color: #888;
    font-size: 11px;
}
QStatusBar {
    background-color: #111;
    color: #888;
    border-top: 1px solid #333;
}
QMenuBar {
    background-color: #1a1a1a;
    color: #e0e0e0;
    border-bottom: 1px solid #333;
}
QMenuBar::item:selected {
    background-color: #2d5a3d;
}
QMenu {
    background-color: #252525;
    color: #e0e0e0;
    border: 1px solid #444;
}
QMenu::item:selected {
    background-color: #2d5a3d;
}
QToolBar {
    background-color: #1a1a1a;
    border-bottom: 1px solid #333;
    spacing: 4px;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #555;
    border-radius: 3px;
    background-color: #252525;
}
QCheckBox::indicator:checked {
    background-color: #2d5a3d;
    border-color: #2d5a3d;
}
QToolTip {
    background-color: #333;
    color: #e0e0e0;
    border: 1px solid #555;
    padding: 4px;
}
"""


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("翡翠珠宝镶嵌托设计AI辅助系统")
        self.setMinimumSize(1200, 800)
        self.resize(1600, 900)

        # 应用样式
        self.setStyleSheet(DARK_STYLESHEET)

        # 初始化UI
        self._init_ui()
        self._init_menu()
        self._init_toolbar()
        self._init_statusbar()
        self._init_shortcuts()

        # 启动时检测
        QTimer.singleShot(500, self._startup_check)

    def _init_ui(self):
        """初始化主界面"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标签页
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        layout.addWidget(self.tabs)

        # 创建各个功能标签页
        self.generate_tab = GenerateTab()
        self.train_tab = TrainTab()
        self.crawl_tab = CrawlTab()
        self.variant_tab = VariantTab()
        self.assistant_tab = AssistantTab()
        self.gallery_tab = GalleryTab()
        self.batch_tab = BatchTab()

        self.tabs.addTab(self.generate_tab, "🎨 AI生图")
        self.tabs.addTab(self.train_tab, "🧠 模型训练")
        self.tabs.addTab(self.crawl_tab, "🕷️ 素材爬虫")
        self.tabs.addTab(self.variant_tab, "🔄 变体生成")
        self.tabs.addTab(self.assistant_tab, "💡 智能助手")
        self.tabs.addTab(self.gallery_tab, "🖼️ 设计图库")
        self.tabs.addTab(self.batch_tab, "📦 批量生产")

    def _init_menu(self):
        """初始化菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        new_action = QAction("新建设计(&N)", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self.generate_tab.new_design)
        file_menu.addAction(new_action)

        save_action = QAction("保存(&S)", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._save_current)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        export_action = QAction("导出设计(&E)", self)
        export_action.triggered.connect(self._export_design)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence("Alt+F4"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")

        undo_action = QAction("撤销(&U)", self)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        edit_menu.addAction(undo_action)

        copy_prompt_action = QAction("复制提示词(&C)", self)
        copy_prompt_action.setShortcut(QKeySequence("Ctrl+D"))
        copy_prompt_action.triggered.connect(self.generate_tab.copy_prompt)
        edit_menu.addAction(copy_prompt_action)

        # 生成菜单
        gen_menu = menubar.addMenu("生成(&G)")

        generate_action = QAction("开始生成(&G)", self)
        generate_action.setShortcut(QKeySequence("Ctrl+G"))
        generate_action.triggered.connect(self.generate_tab.start_generation)
        gen_menu.addAction(generate_action)

        preview_action = QAction("预览大图(&P)", self)
        preview_action.setShortcut(QKeySequence("Space"))
        gen_menu.addAction(preview_action)

        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")

        settings_action = QAction("设置(&S)", self)
        settings_action.triggered.connect(self._open_settings)
        tools_menu.addAction(settings_action)

        tools_menu.addSeparator()

        check_sd_action = QAction("检测SD连接", self)
        check_sd_action.triggered.connect(self._check_sd_connection)
        tools_menu.addAction(check_sd_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_toolbar(self):
        """初始化工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        # 生成按钮
        gen_btn = QPushButton("🎨 生成")
        gen_btn.setProperty("gold", True)
        gen_btn.setToolTip("开始生成设计图 (Ctrl+G)")
        gen_btn.clicked.connect(self.generate_tab.start_generation)
        toolbar.addWidget(gen_btn)

        toolbar.addSeparator()

        # SD状态
        self.sd_status_label = QLabel("  SD WebUI: 检测中...")
        self.sd_status_label.setProperty("color", "status")
        toolbar.addWidget(self.sd_status_label)

        toolbar.addSeparator()

        # 主题切换
        theme_btn = QPushButton("🌙 切换主题")
        theme_btn.setProperty("secondary", True)
        theme_btn.setToolTip("切换深色/浅色主题")
        theme_btn.clicked.connect(self._toggle_theme)
        toolbar.addWidget(theme_btn)

    def _init_statusbar(self):
        """初始化状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # SD连接状态
        self.sd_status = QLabel("SD: 未连接")
        self.statusbar.addWidget(self.sd_status)

        # GPU使用率
        self.gpu_label = QLabel("GPU: --")
        self.statusbar.addWidget(self.gpu_label)

        # 存储空间
        self.storage_label = QLabel("存储: --")
        self.statusbar.addWidget(self.storage_label)

        # 当前任务
        self.task_label = QLabel("就绪")
        self.statusbar.addPermanentWidget(self.task_label)

    def _init_shortcuts(self):
        """初始化快捷键"""
        pass  # 已在菜单中定义

    def _startup_check(self):
        """启动时检测"""
        # 检测SD连接
        result = sd_api.check_connection()
        if result["connected"]:
            self.sd_status.setText(f"SD: 已连接 ({result.get('mode', 'unknown')})")
            self.sd_status_label.setText(f"  SD WebUI: ✅ 已连接")
            self.sd_status_label.setStyleSheet("color: #4caf50;")
        else:
            self.sd_status.setText("SD: 未连接")
            self.sd_status_label.setText(f"  SD WebUI: ❌ {result.get('error', '未连接')}")
            self.sd_status_label.setStyleSheet("color: #f44336;")

        # 更新存储信息
        self._update_storage()

    def _update_storage(self):
        """更新存储空间显示"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(pm.root)
            free_gb = free / (1024 ** 3)
            self.storage_label.setText(f"存储: {free_gb:.1f}GB 可用")
        except Exception:
            self.storage_label.setText("存储: --")

    def _save_current(self):
        """保存当前内容"""
        current_idx = self.tabs.currentIndex()
        if current_idx == 0:
            self.generate_tab.save_current_design()

    def _export_design(self):
        """导出设计"""
        QMessageBox.information(self, "导出", "请在设计图库中选择要导出的图片")

    def _open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self._startup_check()

    def _check_sd_connection(self):
        """手动检测SD连接"""
        result = sd_api.check_connection()
        if result["connected"]:
            QMessageBox.information(self, "SD连接",
                                    f"✅ 连接成功\n模式: {result.get('mode', 'unknown')}\n地址: {result.get('url', '')}")
        else:
            QMessageBox.warning(self, "SD连接",
                                f"❌ 连接失败\n{result.get('error', '未知错误')}")

    def _toggle_theme(self):
        """切换主题"""
        current = config.get("app", "theme", default="dark")
        if current == "dark":
            config.set("app", "theme", "light")
            # 浅色主题（简要实现）
        else:
            config.set("app", "theme", "dark")
            self.setStyleSheet(DARK_STYLESHEET)

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于",
                          "<h2>翡翠珠宝镶嵌托设计AI辅助系统</h2>"
                          "<p>版本: 1.0.0</p>"
                          "<p>基于Stable Diffusion + MiMo API的珠宝设计AI辅助工具</p>"
                          "<p>纯本地运行，保护您的设计隐私</p>")

    def closeEvent(self, event):
        """关闭窗口时的清理"""
        reply = QMessageBox.question(self, "确认退出", "确定要退出程序吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            db.close()
            event.accept()
        else:
            event.ignore()
