# -*- coding: utf-8 -*-
"""
翡翠珠宝镶嵌托设计AI辅助系统 - 主入口
"""
import sys
import os

# 确保项目目录在Python路径中
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from PySide6.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QTimer

from utils.path_manager import init_paths
from utils.logger import logger


def create_splash() -> QSplashScreen:
    """创建启动画面"""
    pixmap = QPixmap(600, 300)
    pixmap.fill(QColor(26, 26, 26))

    painter = QPainter(pixmap)
    painter.setPen(QColor(201, 168, 76))  # 金色
    font = QFont("Microsoft YaHei", 24, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "翡翠珠宝镶嵌托设计\nAI辅助系统")
    painter.setPen(QColor(100, 100, 100))
    font2 = QFont("Microsoft YaHei", 12)
    painter.setFont(font2)
    painter.drawText(0, 230, 600, 50, Qt.AlignCenter, "正在初始化...")
    painter.end()

    splash = QSplashScreen(pixmap)
    splash.show()
    return splash


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("翡翠珠宝镶嵌托设计AI辅助系统")
    app.setStyle("Fusion")

    # 启动画面
    splash = create_splash()
    app.processEvents()

    try:
        # 1. 初始化路径
        splash.showMessage("正在初始化目录结构...", Qt.AlignBottom | Qt.AlignHCenter,
                           QColor(200, 200, 200))
        app.processEvents()
        pm = init_paths()
        logger.info(f"数据根目录: {pm.root}")

        # 2. 检查F盘路径（在Windows上）
        if sys.platform == "win32":
            if not os.path.exists("F:\\"):
                QMessageBox.warning(None, "路径警告",
                                    "F盘不存在！\n所有数据需要存储在 F:\\shengtu2 目录下。\n"
                                    "请确保F盘可用，或修改 path_manager.py 中的 ROOT_DIR。")

        # 3. 初始化数据库
        splash.showMessage("正在初始化数据库...", Qt.AlignBottom | Qt.AlignHCenter,
                           QColor(200, 200, 200))
        app.processEvents()
        from core.database import db
        logger.info("数据库初始化完成")

        # 4. 加载配置
        splash.showMessage("正在加载配置...", Qt.AlignBottom | Qt.AlignHCenter,
                           QColor(200, 200, 200))
        app.processEvents()
        from core.config_manager import config
        logger.info("配置加载完成")

        # 5. 创建主窗口
        splash.showMessage("正在加载界面...", Qt.AlignBottom | Qt.AlignHCenter,
                           QColor(200, 200, 200))
        app.processEvents()
        from ui.main_window import MainWindow
        window = MainWindow()

        # 关闭启动画面，显示主窗口
        QTimer.singleShot(500, lambda: (splash.close(), window.show()))

        logger.info("应用程序启动完成")
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"启动失败: {e}", exc_info=True)
        QMessageBox.critical(None, "启动错误", f"应用程序启动失败:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
