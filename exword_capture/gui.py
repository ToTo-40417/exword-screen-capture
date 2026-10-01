"""Optional GUI. Pure-Python capture core and CLI do not import this module."""
from datetime import datetime
from pathlib import Path
import queue
import time

from PySide6.QtCore import QRectF, QSize, Qt, QTimer, QSettings
from PySide6.QtGui import QAction, QActionGroup, QImage, QKeySequence, QPainter
from PySide6.QtWidgets import (QComboBox, QFileDialog, QLabel, QMainWindow, QMessageBox,
                               QPushButton, QToolBar, QWidget, QScrollArea)
from . import __version__
from .i18n import LANGUAGES, tr
from .pixels import transform, write_png, FILTERS
from .usb_source import UsbSource
from .video import Recorder, MAX_SCALE


def rgb_bytes(image):
    image = image.convertToFormat(QImage.Format.Format_RGB888)
    raw, stride, row = bytes(image.constBits()), image.bytesPerLine(), image.width() * 3
    return b"".join(raw[y * stride:y * stride + row] for y in range(image.height()))


class Screen(QWidget):
    def __init__(self):
        super().__init__()
        self.image = QImage()
        self.scale = 1
        self.fullscreen_fit = False
        self.empty_text = tr("ja", "no_image")

    def geometry_changed(self):
        if self.fullscreen_fit or self.image.isNull():
            self.setMinimumSize(1, 1)
        else:
            dpr = self.devicePixelRatioF()
            self.setMinimumSize(int(self.image.width() * self.scale / dpr + .999),
                                int(self.image.height() * self.scale / dpr + .999))
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        if self.image.isNull():
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.empty_text)
            return
        dpr = self.devicePixelRatioF()
        cw, ch = int(self.width() * dpr), int(self.height() * dpr)
        factor = self.scale
        if self.fullscreen_fit:
            factor = max(1, min(MAX_SCALE, cw // self.image.width(), ch // self.image.height()))
        x = ((cw - self.image.width() * factor) // 2) / dpr
        y = ((ch - self.image.height() * factor) // 2) / dpr
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawImage(QRectF(x, y, self.image.width() * factor / dpr,
                                self.image.height() * factor / dpr), self.image)


class Window(QMainWindow):
    def __init__(self, replay=None, preferences=False):
        super().__init__()
        self.settings = QSettings("ToTo-40417", "EXwordScreenCapture") if preferences else None
        self.language = self.preference("language", "ja")
        if self.language not in LANGUAGES:
            self.language = "ja"
        self.filter_name = self.preference("filter", "none")
        if self.filter_name not in FILTERS:
            self.filter_name = "none"
        self.output = Path(self.preference("output", str(Path.home() / "Pictures" / "EX-word Captures")))
        self.setWindowTitle(f"EX-word Screen Capture {__version__}")
        self.screen = Screen()
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.screen)
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setStyleSheet("QScrollArea { background: black; border: none; }")
        self.setCentralWidget(self.scroll)
        self.resize(1120, 740)
        self.full_image = QImage()
        self.source = None
        self.last_sequence = 0
        self.last_received = None
        self.recorder = None
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        self.connect_button = QPushButton()
        self.connect_button.clicked.connect(self.connect_device)
        self.toolbar.addWidget(self.connect_button)
        self.view = QComboBox()
        for key in ("all", "upper", "lower"):
            self.view.addItem("", key)
        self.view.currentIndexChanged.connect(self.refresh_view)
        self.toolbar.addWidget(self.view)
        self.scale = QComboBox()
        for factor in range(1, 11):
            self.scale.addItem(f"x{factor}", factor)
        try:
            self.scale.setCurrentIndex(max(0, min(9, int(self.preference("scale", 1)) - 1)))
        except (ValueError, TypeError):
            pass
        self.scale.currentIndexChanged.connect(self.scale_changed)
        self.toolbar.addWidget(self.scale)
        self.save_button = QPushButton()
        self.save_button.clicked.connect(self.save_image)
        self.toolbar.addWidget(self.save_button)
        self.record_button = QPushButton()
        self.record_button.clicked.connect(self.toggle_record)
        self.toolbar.addWidget(self.record_button)
        self.menu = self.menuBar().addMenu("")
        self.folder_action = self.menu.addAction("")
        self.folder_action.triggered.connect(self.choose_folder)
        self.filter_menu = self.menu.addMenu("")
        self.filter_actions = {}
        group = QActionGroup(self)
        for name in FILTERS:
            action = self.filter_menu.addAction("")
            action.setCheckable(True)
            action.setChecked(name == self.filter_name)
            action.triggered.connect(lambda checked=False, value=name: self.set_filter(value))
            group.addAction(action)
            self.filter_actions[name] = action
        self.open_action = self.menu.addAction("")
        self.record_format = str(self.preference("record_format", "h264"))
        if self.record_format not in ("h264", "ffv1"):
            self.record_format = "h264"
        try:
            self.record_scale = max(1, min(10, int(self.preference("record_scale", 1))))
        except (ValueError, TypeError):
            self.record_scale = 1
        self.record_format_menu = self.menu.addMenu("")
        self.record_format_actions = {}
        group = QActionGroup(self)
        for codec, label in (("h264", "H.264 / MP4"), ("ffv1", "FFV1 / MKV")):
            action = self.record_format_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(codec == self.record_format)
            action.triggered.connect(lambda checked=False, value=codec: self.set_record_option("record_format", value))
            group.addAction(action)
            self.record_format_actions[codec] = action
        self.record_scale_menu = self.menu.addMenu("")
        group = QActionGroup(self)
        for factor in range(1, 11):
            action = self.record_scale_menu.addAction(f"x{factor}")
            action.setCheckable(True)
            action.setChecked(factor == self.record_scale)
            action.triggered.connect(lambda checked=False, value=factor: self.set_record_option("record_scale", value))
            group.addAction(action)
        self.open_action.triggered.connect(self.open_image)
        self.license_action = self.menu.addAction("")
        self.license_action.triggered.connect(self.show_licenses)
        self.fullscreen_action = QAction(self)
        self.fullscreen_action.setShortcut(QKeySequence("F11"))
        self.fullscreen_action.triggered.connect(self.toggle_fullscreen)
        self.menuBar().addAction(self.fullscreen_action)
        self.language_menu = self.menuBar().addMenu("")
        self.language_actions = {}
        group = QActionGroup(self)
        for language, name in LANGUAGES.items():
            action = self.language_menu.addAction(name)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, value=language: self.set_language(value))
            group.addAction(action)
            self.language_actions[language] = action
        for shortcut, callback in (("F8", self.save_image), ("F9", self.toggle_record), ("Escape", self.exit_fullscreen)):
            action = QAction(self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(callback)
            self.addAction(action)
        self.freshness = QLabel()
        self.statusBar().addPermanentWidget(self.freshness)
        self.retranslate()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(50)
        if replay:
            self.load_image(replay)
        self.scale_changed()

    def preference(self, key, default):
        return self.settings.value(key, default) if self.settings else default

    def persist(self, key, value):
        if self.settings:
            self.settings.setValue(key, value)

    def text(self, key, **values):
        return tr(self.language, key, **values)

    def retranslate(self):
        self.menu.setTitle(self.text("settings"))
        self.folder_action.setText(self.text("folder"))
        self.filter_menu.setTitle(self.text("filter"))
        self.open_action.setText(self.text("open"))
        self.license_action.setText(self.text("licenses"))
        self.record_format_menu.setTitle(self.text("record_format"))
        self.record_scale_menu.setTitle(self.text("record_scale"))
        self.fullscreen_action.setText(self.text("fullscreen"))
        self.language_menu.setTitle(self.text("language"))
        for language, action in self.language_actions.items():
            action.setChecked(language == self.language)
        for name, action in self.filter_actions.items():
            action.setText(self.text(name))
        for index, key in enumerate(("all", "upper", "lower")):
            self.view.setItemText(index, self.text(key))
        self.view.setToolTip(self.text("view_hint"))
        self.scale.setItemText(0, self.text("scale"))
        self.scale.setToolTip(self.text("scale_hint"))
        self.save_button.setText(self.text("screenshot"))
        self.record_button.setText(self.text("record_stop" if self.recorder else "record"))
        self.screen.empty_text = self.text("no_image")
        self.screen.update()
        self.update_connection_button()
        self.statusBar().showMessage(self.text("idle"))
        self.refresh_view()

    def show_licenses(self):
        import html
        url = "https://github.com/ToTo-40417/exword-screen-capture"
        text = html.escape(self.text("licenses_text")).replace("\n", "<br>")
        text = text.replace(url, f'<a href="{url}">{url}</a>')
        box = QMessageBox(self)
        box.setWindowTitle(self.text("licenses"))
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        box.setText(text)
        for label in box.findChildren(QLabel):
            label.setOpenExternalLinks(True)
        box.exec()

    def set_record_option(self, name, value):
        setattr(self, name, value)
        self.persist(name, value)

    def set_language(self, language):
        self.language = language
        self.persist("language", language)
        self.retranslate()

    def update_connection_button(self):
        state = self.source.connection_state() if self.source else "stopped"
        key = "disconnect" if state == "connected" else "waiting" if state == "waiting" else "connect"
        self.connect_button.setText(self.text(key))

    def connect_device(self):
        if self.source:
            self.source.stop()
            self.source = None
            self.update_connection_button()
            self.statusBar().showMessage(self.text("stopped"))
            return
        question = QMessageBox(QMessageBox.Icon.Question, self.text("mode_title"), self.text("mode_confirm"),
                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, self)
        question.button(QMessageBox.StandardButton.Yes).setText(self.text("yes"))
        question.button(QMessageBox.StandardButton.Cancel).setText(self.text("cancel"))
        if question.exec() != QMessageBox.StandardButton.Yes:
            return
        self.source = UsbSource()
        self.last_sequence = 0
        self.source.start()
        self.update_connection_button()

    def poll(self):
        if self.source:
            while True:
                try:
                    key, values = self.source.messages.get_nowait()
                    if key == "error_detail":
                        values["detail"] = self.text(values["detail"])
                    self.statusBar().showMessage(self.text(key, **values))
                except queue.Empty:
                    break
            sequence, latest = self.source.snapshot()
            if sequence != self.last_sequence and latest:
                self.last_sequence = sequence
                self.last_received = time.monotonic()
                w, h, rgb = latest
                self.full_image = QImage(rgb, w, h, w * 3, QImage.Format.Format_RGB888).copy()
                self.refresh_view()
            if not self.source.thread.is_alive():
                self.source = None
            self.update_connection_button()
        if self.recorder and not self.recorder.thread.is_alive():
            self.finish_record()
        if self.last_received is not None:
            self.freshness.setText(self.text("received", width=self.full_image.width(), height=self.full_image.height(),
                                             age=int(time.monotonic() - self.last_received)))

    def scale_changed(self):
        self.screen.scale = self.scale.currentData()
        self.screen.geometry_changed()
        self.persist("scale", self.screen.scale)

    def set_filter(self, name):
        self.filter_name = name
        self.persist("filter", name)
        self.refresh_view()

    def refresh_view(self):
        if self.full_image.isNull():
            return
        dual = self.full_image.size() == QSize(528, 432)
        for index in (1, 2):
            self.view.model().item(index).setEnabled(dual)
        if not dual and self.view.currentIndex() != 0:
            self.view.setCurrentIndex(0)
        w, h, rgb = transform(self.full_image.width(), self.full_image.height(), rgb_bytes(self.full_image),
                              self.view.currentData(), self.filter_name)
        self.screen.image = QImage(rgb, w, h, w * 3, QImage.Format.Format_RGB888).copy()
        self.screen.geometry_changed()
        if self.last_received is None:
            self.freshness.setText(self.text("image_info", width=w, height=h))
        if self.recorder:
            if (w, h) != (self.recorder.width, self.recorder.height):
                self.finish_record()
                self.statusBar().showMessage(self.text("size_changed"))
            else:
                self.recorder.update(rgb)

    def choose_folder(self):
        directory = QFileDialog.getExistingDirectory(self, self.text("folder"), str(self.output))
        if directory:
            self.output = Path(directory)
            self.persist("output", str(self.output))

    def open_image(self):
        if self.recorder or self.source:
            return
        path, _ = QFileDialog.getOpenFileName(self, self.text("open"), "", "Images (*.png *.ppm *.bmp)")
        if path:
            try:
                self.load_image(path)
            except Exception as error:
                QMessageBox.warning(self, self.text("error"), self.text(str(error)))

    def load_image(self, path):
        image = QImage(str(path))
        if image.isNull():
            raise ValueError("image_open_failed")
        self.full_image = image
        self.refresh_view()

    def destination(self, suffix):
        self.output.mkdir(parents=True, exist_ok=True)
        return self.output / ("EXWORD_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + suffix)

    def save_image(self):
        image = self.screen.image
        if image.isNull():
            return
        try:
            path = self.destination(".png")
            write_png(path, image.width(), image.height(), rgb_bytes(image), self.scale.currentData())
            self.statusBar().showMessage(self.text("saved", path=path))
        except Exception as error:
            QMessageBox.warning(self, self.text("error"), self.text(str(error)))

    def toggle_record(self):
        if self.recorder:
            self.finish_record()
            return
        image = self.screen.image
        if image.isNull():
            return
        try:
            factor = self.record_scale
            self.record_path = self.destination(".mp4" if self.record_format == "h264" else ".mkv")
            self.recorder = Recorder(self.record_path, image.width(), image.height(), rgb_bytes(image),
                                     canvas=(image.width() * factor, image.height() * factor), codec=self.record_format)
            self.record_button.setText(self.text("record_stop"))
            self.view.setEnabled(False)
            self.scale.setEnabled(False)
            self.filter_menu.setEnabled(False)
            self.record_format_menu.setEnabled(False)
            self.record_scale_menu.setEnabled(False)
            self.statusBar().showMessage(self.text("recording", path=self.record_path))
        except Exception as error:
            QMessageBox.warning(self, self.text("error"), self.text(str(error)))

    def finish_record(self):
        recorder = self.recorder
        if recorder is None:
            return
        self.recorder = None
        recorder.stop()
        self.record_button.setText(self.text("record"))
        self.view.setEnabled(True)
        self.scale.setEnabled(True)
        self.filter_menu.setEnabled(True)
        self.record_format_menu.setEnabled(True)
        self.record_scale_menu.setEnabled(True)
        if recorder.error:
            QMessageBox.warning(self, self.text("error"), self.text(recorder.error))
        else:
            self.statusBar().showMessage(self.text("saved", path=self.record_path))

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.exit_fullscreen()
        else:
            self.screen.fullscreen_fit = True
            self.screen.geometry_changed()
            self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.toolbar.hide()
            self.menuBar().hide()
            self.statusBar().hide()
            self.showFullScreen()

    def exit_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.screen.fullscreen_fit = False
            self.screen.geometry_changed()
            self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.toolbar.show()
            self.menuBar().show()
            self.statusBar().show()

    def closeEvent(self, event):
        self.finish_record()
        if self.source:
            self.source.stop()
        event.accept()
