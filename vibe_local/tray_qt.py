"""Qt-based system tray icon for KDE Wayland."""
import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject


class TraySignals(QObject):
    """Signals for communicating with the tray from other threads."""
    set_recording = pyqtSignal(bool)
    show_message = pyqtSignal(str, str)  # title, message


class VibeTray:
    """System tray icon using Qt."""

    def __init__(self, on_quit=None):
        self._app = None
        self._tray = None
        self._on_quit = on_quit
        self._signals = TraySignals()
        self._signals.set_recording.connect(self._on_set_recording)
        self._signals.show_message.connect(self._on_show_message)

    def _create_icon(self, recording=False) -> QIcon:
        """Create the tray icon."""
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if recording:
            # Red circle when recording
            painter.setBrush(QBrush(QColor("#F44336")))
            painter.setPen(QColor("#B71C1C"))
            painter.drawEllipse(4, 4, size-8, size-8)
        else:
            # Green microphone when idle
            painter.setBrush(QBrush(QColor("#4CAF50")))
            painter.setPen(QColor("#2E7D32"))
            # Mic head
            painter.drawEllipse(16, 8, 32, 32)
            # Stem
            painter.drawRect(28, 40, 8, 12)
            # Base
            painter.drawRect(22, 52, 20, 4)

        painter.end()
        return QIcon(pixmap)

    def _on_set_recording(self, recording: bool):
        """Update icon based on recording state."""
        if self._tray:
            self._tray.setIcon(self._create_icon(recording))

    def _on_show_message(self, title: str, message: str):
        """Show a notification."""
        if self._tray:
            self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 2000)

    def set_recording(self, recording: bool):
        """Thread-safe method to set recording state."""
        self._signals.set_recording.emit(recording)

    def notify(self, message: str, title: str = "Vibe Local"):
        """Thread-safe method to show notification."""
        self._signals.show_message.emit(title, message)

    def _quit(self):
        """Handle quit action."""
        if self._on_quit:
            self._on_quit()
        if self._app:
            self._app.quit()

    def run(self):
        """Run the tray icon (blocking)."""
        self._app = QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)

        self._tray = QSystemTrayIcon()
        self._tray.setIcon(self._create_icon(False))
        self._tray.setToolTip("Vibe Local - Ctrl+Alt to record")

        # Create menu
        menu = QMenu()
        menu.addAction("Vibe Local").setEnabled(False)
        menu.addSeparator()
        menu.addAction("Ctrl+Alt: Voice to text").setEnabled(False)
        menu.addAction("Super+Shift+R: Rewrite").setEnabled(False)
        menu.addAction("Super+Shift+C: Context reply").setEnabled(False)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self._quit)

        self._tray.setContextMenu(menu)
        self._tray.show()

        return self._app.exec()


def create_tray(on_quit=None) -> VibeTray:
    """Create a tray icon instance."""
    return VibeTray(on_quit)
