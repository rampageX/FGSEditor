"""Persist Qt geometry in the existing settings.json (Qt uses logical pixels)."""
from PySide6.QtCore import QObject, QEvent, QByteArray, Qt
from PySide6.QtGui import QGuiApplication
from .settings_manager import get_setting, set_setting

class WindowState(QObject):
    def __init__(self, window, key):
        super().__init__(window)
        self.window, self.key = window, "window_" + key
        self.restored = False
        window.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show and not self.restored:
            self.restored = True
            saved = get_setting(self.key, "")
            if isinstance(saved, str) and saved:
                obj.restoreGeometry(QByteArray.fromBase64(saved.encode("ascii")))
                obj.setWindowState(obj.windowState() & ~Qt.WindowMinimized)
            screens = QGuiApplication.screens()
            rect = obj.frameGeometry()
            screen = max(screens, key=lambda s: (s.availableGeometry().intersected(rect).width() * s.availableGeometry().intersected(rect).height())) if screens else None
            if screen and not obj.isMaximized():
                area = screen.availableGeometry()
                obj.setMinimumSize(min(obj.minimumWidth(), area.width()),
                                   min(obj.minimumHeight(), area.height()))
                obj.resize(min(obj.width(), area.width()), min(obj.height(), area.height()))
                obj.move(max(area.left(), min(obj.x(), area.right()-obj.width()+1)),
                         max(area.top(), min(obj.y(), area.bottom()-obj.height()+1)))
        if self.restored and event.type() in (QEvent.Move, QEvent.Resize, QEvent.Hide, QEvent.Close):
            if not obj.isMinimized():
                set_setting(self.key, bytes(obj.saveGeometry().toBase64()).decode("ascii"))
        return False

def remember_window(window, key):
    window._window_state = WindowState(window, key)
