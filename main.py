"""
muask（沐问） - Main entry point.
"""
import os
import sys
import traceback
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from app.main_window import MainWindow
from app.paths import resource_path
from app.styles import APP_STYLE


def excepthook(exc_type, exc_value, exc_tb):
    """Global exception handler so the UI doesn't die silently."""
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    sys.stderr.write(msg)
    try:
        QMessageBox.critical(None, "未捕获的异常", msg)
    except Exception:
        pass


def main():
    sys.excepthook = excepthook
    app = QApplication(sys.argv)
    app.setApplicationName("muask")
    # macOS takes the dock icon from the .app bundle, but Windows taskbar and
    # Linux window managers need it set explicitly.
    icon_path = resource_path("assets", "app_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    app.setStyleSheet(APP_STYLE)

    win = MainWindow()
    win.show()
    exit_code = app.exec()
    # A driver call blocked in connect() can outlive the waits in closeEvent.
    # Qt calls qFatal() if such a QThread is destroyed during interpreter
    # shutdown, aborting the process on close. Everything persistent is
    # fsynced before this point, so end the process directly instead of
    # letting Python tear down live worker threads.
    os._exit(exit_code if isinstance(exit_code, int) else 0)


if __name__ == '__main__':
    main()
