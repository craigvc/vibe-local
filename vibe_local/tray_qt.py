"""Qt-based system tray icon for KDE Wayland."""
import sys
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog, QVBoxLayout,
    QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, QTabWidget,
    QWidget, QComboBox, QFormLayout
)
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject

from .config import get_config


class SettingsDialog(QDialog):
    """Settings dialog for Vibe Local."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vibe Local Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._config = get_config()
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget()

        # Vocabulary tab
        vocab_tab = QWidget()
        vocab_layout = QVBoxLayout(vocab_tab)
        vocab_layout.addWidget(QLabel("Custom vocabulary (one term per line):"))
        vocab_layout.addWidget(QLabel("These terms will be preserved exactly as written."))
        self._vocab_edit = QTextEdit()
        self._vocab_edit.setPlaceholderText("GameDevBuddy\nC++\nUnreal Engine\nuseState")
        vocab_layout.addWidget(self._vocab_edit)
        tabs.addTab(vocab_tab, "Vocabulary")

        # Context tab
        context_tab = QWidget()
        context_layout = QFormLayout(context_tab)
        self._context_edit = QLineEdit()
        self._context_edit.setPlaceholderText("C++, Rust, React, Unreal Engine")
        context_layout.addRow("Programming context:", self._context_edit)
        context_layout.addRow("", QLabel("Helps the AI understand your domain"))

        self._style_combo = QComboBox()
        self._style_combo.addItems(["casual", "formal", "very_casual"])
        context_layout.addRow("Writing style:", self._style_combo)

        tabs.addTab(context_tab, "Context")

        # Whisper tab
        whisper_tab = QWidget()
        whisper_layout = QFormLayout(whisper_tab)
        self._model_combo = QComboBox()
        self._model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        whisper_layout.addRow("Whisper model:", self._model_combo)
        whisper_layout.addRow("", QLabel("Larger = more accurate but slower"))

        self._language_edit = QLineEdit()
        self._language_edit.setPlaceholderText("en")
        whisper_layout.addRow("Language:", self._language_edit)

        tabs.addTab(whisper_tab, "Whisper")

        layout.addWidget(tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _load_settings(self):
        """Load current settings into the UI."""
        # Vocabulary
        vocab = self._config.vocabulary
        self._vocab_edit.setPlainText("\n".join(vocab))

        # Context
        self._context_edit.setText(self._config.programming_context)

        # Style
        style = self._config.style
        index = self._style_combo.findText(style)
        if index >= 0:
            self._style_combo.setCurrentIndex(index)

        # Whisper
        model = self._config.whisper.get("model", "medium")
        index = self._model_combo.findText(model)
        if index >= 0:
            self._model_combo.setCurrentIndex(index)

        self._language_edit.setText(self._config.whisper.get("language", "en"))

    def _save_settings(self):
        """Save settings to config file."""
        # Vocabulary
        vocab_text = self._vocab_edit.toPlainText()
        vocab_list = [v.strip() for v in vocab_text.split("\n") if v.strip()]
        self._config._config["vocabulary"] = vocab_list

        # Context
        self._config._config["programming_context"] = self._context_edit.text()

        # Style
        self._config._config["style"] = self._style_combo.currentText()

        # Whisper
        self._config._config["whisper"]["model"] = self._model_combo.currentText()
        self._config._config["whisper"]["language"] = self._language_edit.text()

        # Save to file
        self._config.save()

        self.accept()


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

    def _open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog()
        dialog.exec()

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
        self._tray.setToolTip("Vibe Local - Ctrl+Shift to record")

        # Create menu
        menu = QMenu()
        menu.addAction("Vibe Local").setEnabled(False)
        menu.addSeparator()
        menu.addAction("Ctrl+Shift: Voice to text").setEnabled(False)
        menu.addSeparator()
        settings_action = menu.addAction("Settings...")
        settings_action.triggered.connect(self._open_settings)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self._quit)

        self._tray.setContextMenu(menu)
        self._tray.show()

        return self._app.exec()


def create_tray(on_quit=None) -> VibeTray:
    """Create a tray icon instance."""
    return VibeTray(on_quit)
