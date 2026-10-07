"""Sound Manager — a portable desktop audio library and excerpt editor."""
from __future__ import annotations

import argparse
import io
import sys
import tempfile
import traceback
import uuid
from threading import Event
from pathlib import Path

import numpy as np
import soundfile as sf
from PySide6.QtCore import (
    Qt, QObject, Signal, Slot, QRunnable, QThreadPool, QSettings, QDir, QUrl,
    QTimer, QMimeData, QEvent, QRectF, QSize, QTranslator, QLibraryInfo, QLocale,
)
from PySide6.QtGui import QColor, QDesktopServices, QFont, QKeySequence, QPainter, QShortcut, QIcon
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QToolButton, QComboBox, QLineEdit, QTreeView, QFileSystemModel,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QSplitter, QFileDialog,
    QMessageBox, QDoubleSpinBox, QSlider, QScrollBar, QCheckBox,
    QAbstractItemView, QStyledItemDelegate, QFrame, QStyle, QScrollArea, QSizePolicy,
)

from audio_engine import AudioClip, EXTENSIONS, load_audio, write_preview, export_audio, save_audio, edit_selection, insert_clip, remove_selection
from waveform import Waveform, PlaybackBar, time_label
from editor_icons import editor_icon
from file_browser import FileList, FolderTree, FileActions, copy_files, index_library
from app_paths import APP_DIR, state_dir, default_library_dir
from i18n import Localizer, Message

STYLE = """
QWidget { background: #161e2a; color: #e4eaf3; font-family: 'Segoe UI'; font-size: 13px; }
QMainWindow, QStatusBar { background: #101722; }
QLabel#brand { font-size: 25px; font-weight: 700; }
QLabel#eyebrow { color: #62d6bf; font-size: 11px; font-weight: 700; letter-spacing: 2px; }
QLabel#muted { color: #92a1b5; }
QLabel#filename { font-size: 20px; font-weight: 600; }
QLabel#pill { color: #62d6bf; background: #1c3537; border-radius: 8px; padding: 5px 10px; }
QFrame#card { background: #1b2533; border: 1px solid #2b394d; border-radius: 10px; }
QFrame#card QLabel, QFrame#card QCheckBox { background: transparent; }
QPushButton, QToolButton { background: #253246; border: 1px solid #35465c; border-radius: 6px; padding: 6px 10px; }
QPushButton:hover, QToolButton:hover { background: #304159; border-color: #62d6bf; }
QPushButton:pressed, QToolButton:pressed { background: #3b526d; }
QPushButton:disabled, QToolButton:disabled { color: #68788f; background: #202b3b; border-color: #2c394b; }
QPushButton#primary { background: #62d6bf; color: #0f2627; border-color: #62d6bf; font-weight: 700; }
QPushButton#primary:hover { background: #83e5d2; }
QPushButton#primary:disabled { background: #254742; color: #71938c; border-color: #254742; }
QComboBox, QLineEdit, QDoubleSpinBox { background: #101822; border: 1px solid #35465c; border-radius: 6px; padding: 7px; selection-background-color: #327d76; }
QComboBox:focus, QLineEdit:focus, QDoubleSpinBox:focus { border-color: #62d6bf; }
QTreeView, QTreeWidget { background: #121a25; border: 1px solid #2b394d; border-radius: 7px; alternate-background-color: #17212e; }
QTreeView::item { padding: 6px; }
QTreeView::item:selected { background: #28423f; color: #d4fff3; }
QTreeView::item:hover { background: #223349; }
QHeaderView::section { background: #202c3c; color: #aab8ca; border: 0; border-bottom: 1px solid #35465c; padding: 9px; }
QSplitter::handle { background: #101722; }
QSlider::groove:horizontal { height: 4px; background: #35465c; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #62d6bf; border-radius: 2px; }
QSlider::handle:horizontal { background: #c4f6eb; border-radius: 6px; width: 12px; margin: -5px 0; }
QScrollBar:horizontal { height: 12px; background: #111822; }
QScrollBar::handle:horizontal { background: #35465c; min-width: 30px; border-radius: 5px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar:vertical { width: 10px; background: #111822; }
QScrollBar::handle:vertical { background: #35465c; min-height: 30px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QScrollArea { border: none; background: transparent; }
QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #526680; background: #111822; border-radius: 3px; }
QCheckBox::indicator:checked { background: #62d6bf; border-color: #62d6bf; }
QToolTip { color: #e4eaf3; background: #253246; border: 1px solid #526680; padding: 6px; }
"""


class WorkerSignals(QObject):
    finished = Signal(object, object, str)


class Worker(QRunnable):
    def __init__(self, token, function):
        super().__init__()
        self.token, self.function = token, function
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            result, error = self.function(), ""
        except Exception as exc:
            result, error = None, str(exc)
        self.signals.finished.emit(self.token, result, error)


class SoundManager(QMainWindow):
    def __init__(self, settings_path=None, prompt=True):
        super().__init__()
        self.setWindowTitle("Sound Manager")
        self.setWindowIcon(QIcon(str(APP_DIR / "assets" / "sound-manager.ico")))
        self.resize(1240, 900)
        self.setMinimumSize(1000, 600)
        settings_path = Path(settings_path or state_dir() / "settings.ini")
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
        self.i18n = Localizer(self.settings.value("language", "pt_BR"))
        self.qt_translator = QTranslator(self)
        self.apply_qt_language()
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        # Windows media backends can briefly retain preview handles during shutdown.
        self.temporary = tempfile.TemporaryDirectory(prefix="sound-manager-", ignore_cleanup_errors=True)
        self.clip = None
        self.copied_clip = None
        self.base = None
        self.folder = None
        self.load_token = None
        self.preview_path = None
        self.pending_play = False
        self.play_limit = None
        self.play_origin = 0.0
        self.selection_playback = False
        self.selection_token = None
        self.selection_preview = None
        self.exporting = False
        self.save_jobs = {}
        self.saved_clips = {}
        self.editor_row = None
        self.editor_child = None
        self.editor_host = None
        self.editor_path = None
        self.copy_jobs = set()
        self.jobs = {}
        self.undo_stack = []
        self.redo_stack = []
        self.modified = False
        self.edit_cache = {}
        self.edit_jobs = {}
        self.edit_token = None
        self.pending_document_state = None
        self.transport_row = self.transport_host = None
        self.transport_path = None
        self.known_durations = {}
        self.folder_index = None
        self.folder_scan_token = None
        self.folder_scan_cancel = Event()
        self.folder_filter_timer = QTimer(self)
        self.folder_filter_timer.setSingleShot(True)
        self.folder_filter_timer.setInterval(30)
        self.folder_filter_timer.timeout.connect(self.apply_folder_filter)
        self.player = QMediaPlayer(self)
        self.output = QAudioOutput(self)
        self.player.setAudioOutput(self.output)
        self.player.positionChanged.connect(self.on_position)
        self.player.playbackStateChanged.connect(self.on_playback_state)
        self.player.mediaStatusChanged.connect(self.on_media_status)
        self.player.errorOccurred.connect(self.on_player_error)
        self.build_ui()
        QApplication.instance().installEventFilter(self)
        self.restore_preferences()
        if not self.base and prompt:
            QTimer.singleShot(150, self.choose_base)

    def t(self, source, *values):
        return self.i18n.text(source, *values)

    def display_clip_name(self):
        name = self.clip.name
        if self.clip.source and name == self.clip.source.name:
            return name
        if name == "Trecho copiado":
            return Message(name)
        if name.endswith(" — trecho"):
            return Message("{0} — trecho", (name.removesuffix(" — trecho"),))
        return name

    def ui(self, target, method, source, *values, prefix=()):
        self.i18n.bind(target, method, source, *values, prefix=prefix)

    def apply_qt_language(self):
        application = QApplication.instance()
        application.removeTranslator(self.qt_translator)
        if self.i18n.language == "pt_BR":
            catalog = APP_DIR / "assets" / "qtbase_pt_BR.qm"
            if not catalog.is_file():
                catalog = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)) / catalog.name
            if self.qt_translator.load(str(catalog)):
                application.installTranslator(self.qt_translator)
        self.setLocale(QLocale("en_US" if self.i18n.language == "en" else "pt_BR"))

    def change_language(self, _index):
        language = self.language_combo.currentData()
        self.settings.setValue("language", language)
        self.settings.sync()
        self.i18n.set_language(language)
        self.apply_qt_language()
        self.waveform.update()
        for number in range(self.files.topLevelItemCount()):
            self.files.topLevelItem(number).setToolTip(0, self.t("▶ ouvir / pausar   ·   Recortar abre a onda nesta linha"))
        self.files.viewport().update()
        if self.editor_host is not None:
            self.editor_child.setSizeHint(0, QSize(0, self.editor.minimumSizeHint().height() + 20))

    def label(self, text, name=None):
        label = QLabel()
        self.ui(label, "setText", text)
        if name:
            label.setObjectName(name)
        return label

    def button(self, text, callback, primary=False):
        button = QPushButton()
        self.ui(button, "setText", text)
        if primary:
            button.setObjectName("primary")
        button.clicked.connect(callback)
        return button

    def action_button(self, icon, callback, tooltip, text="", primary=False):
        button = self.button(text, callback, primary)
        button.setIcon(editor_icon(icon, primary))
        button.setIconSize(QSize(18, 18))
        button.setFixedHeight(32)
        if not text:
            button.setFixedWidth(32)
        self.ui(button, 'setToolTip', tooltip)
        self.ui(button, 'setAccessibleName', tooltip)
        return button

    @staticmethod
    def toolbar_separator():
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFixedHeight(22)
        line.setStyleSheet("background: #35465c;")
        line.setFixedWidth(1)
        return line

    def build_ui(self):
        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(22, 18, 22, 12)
        outer.setSpacing(14)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(3)
        titles.addWidget(self.label("BIBLIOTECA LOCAL DE ÁUDIO", "eyebrow"))
        titles.addWidget(self.label("Sound Manager", "brand"))
        header.addLayout(titles)
        header.addStretch()
        header.addWidget(self.label("Ouça. Selecione. Salve.", "muted"))
        header.addSpacing(14)
        header.addWidget(self.label("Idioma", "muted"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("Português (BR)", "pt_BR")
        self.language_combo.addItem("English", "en")
        self.language_combo.setCurrentIndex(self.language_combo.findData(self.i18n.language))
        self.ui(self.language_combo, "setToolTip", "Escolha o idioma da interface. A escolha é salva automaticamente.")
        self.ui(self.language_combo, "setAccessibleName", "Idioma")
        self.language_combo.currentIndexChanged.connect(self.change_language)
        header.addWidget(self.language_combo)
        outer.addLayout(header)

        self.base_label = self.label("Escolha a pasta onde você guarda seus sons.", "muted")
        self.base_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.base_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        sidebar = QWidget()
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 0, 0, 0)
        sidebar.setMinimumWidth(240)
        side.addWidget(self.button("Escolher biblioteca…", self.choose_base, True))
        side.addWidget(self.button("Abrir arquivo…", self.open_file))
        side.addWidget(self.base_label)
        navigation = QHBoxLayout()
        self.up_button = self.button("↑ Subir", self.go_up)
        self.ui(self.up_button, 'setToolTip', "Subir uma pasta (Alt+↑)")
        navigation.addWidget(self.up_button)
        navigation.addWidget(self.button("Raiz", lambda: self.navigate(self.base) if self.base else None))
        navigation.addWidget(self.button("↻", self.refresh_folder))
        side.addLayout(navigation)
        self.folders_heading = self.label("PASTAS", "eyebrow")
        side.addWidget(self.folders_heading)
        self.folder_search = QLineEdit()
        self.ui(self.folder_search, 'setPlaceholderText', "Filtrar pastas ou arquivos…")
        self.folder_search.setClearButtonEnabled(True)
        self.ui(self.folder_search, 'setToolTip', "Mostra pastas com o texto no nome ou em nomes de arquivos dentro delas, inclusive em subpastas.")
        self.folder_search.textChanged.connect(self.filter_folders)
        side.addWidget(self.folder_search)
        self.folder_model = QFileSystemModel(self)
        self.folder_model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)
        self.folder_model.setReadOnly(True)
        self.folder_model.rowsInserted.connect(self.schedule_folder_filter)
        self.folder_model.rowsRemoved.connect(self.schedule_folder_filter)
        self.folder_model.layoutChanged.connect(self.schedule_folder_filter)
        self.tree = FolderTree(localizer=self.i18n)
        self.tree.setModel(self.folder_model)
        for column in (1, 2, 3):
            self.tree.hideColumn(column)
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.clicked.connect(self.folder_clicked)
        self.tree.copyRequested.connect(self.copy_to_folder)
        side.addWidget(self.tree)
        side.addWidget(self.label("Arraste arquivos para uma pasta\naqui ou no Explorer para copiar.", "muted"))
        self.splitter.addWidget(sidebar)

        main = QWidget()
        body = QVBoxLayout(main)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(10)
        self.folder_label = self.label("Biblioteca", "eyebrow")
        self.folder_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        file_heading = QHBoxLayout()
        file_heading.addWidget(self.folder_label, 1)
        self.search = QLineEdit()
        self.ui(self.search, 'setPlaceholderText', "Filtrar arquivos pelo nome…")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(260)
        self.search.setMaximumWidth(420)
        self.ui(self.search, 'setToolTip', "Mostra arquivos da pasta atual cujo nome contém o texto.")
        self.search.textChanged.connect(self.filter_rows)
        file_heading.addWidget(self.search, 1)
        body.addLayout(file_heading)

        self.files = FileList(localizer=self.i18n)
        self.files.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.ui(self.files, 'setHeaderLabels', ["Ouvir / editar", "Nome", "Arquivo", "Reprodução"])
        self.file_header = self.files.headerItem()
        self.files.setRootIsDecorated(False)
        self.files.setAlternatingRowColors(True)
        self.files.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.files.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.files.setMinimumHeight(155)
        self.files.header().setStretchLastSection(False)
        self.files.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.files.setColumnWidth(0, 145)
        self.files.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.files.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.files.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.files.setColumnWidth(3, 292)
        self.files.itemClicked.connect(self.file_clicked)
        self.files.itemDoubleClicked.connect(self.file_activated)
        self.delegate = FileActions(self.files, localizer=self.i18n)
        self.delegate.playRequested.connect(self.play_file)
        self.delegate.editorRequested.connect(self.toggle_editor)
        self.files.setItemDelegateForColumn(0, self.delegate)
        self.files.dragFinished.connect(lambda action: self.ui(self.statusBar(), 'showMessage', "Arraste concluído." if action == Qt.DropAction.CopyAction else "Arraste cancelado."))
        body.addWidget(self.files, 1)

        self.editor = QFrame()
        self.editor.setStyleSheet("QPushButton { padding: 4px 9px; } QDoubleSpinBox { padding: 4px; } QLabel#pill { padding: 4px 8px; }")
        self.editor.setObjectName("card")
        edit = QVBoxLayout(self.editor)
        edit.setContentsMargins(16, 14, 16, 14)
        edit.setSpacing(6)
        audio_header = QHBoxLayout()
        name_column = QVBoxLayout()
        self.name_label = self.label("Nenhum som aberto", "filename")
        self.name_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        name_column.addWidget(self.name_label)
        self.info_label = self.label("Selecione um som para ouvir e recortar.", "muted")
        self.info_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        name_column.addWidget(self.info_label)
        audio_header.addLayout(name_column, 1)
        self.source_button = self.action_button("folder", self.reveal_source, "Mostrar o arquivo original no Explorer.", "Mostrar arquivo")
        self.source_button.setEnabled(False)
        audio_header.addWidget(self.source_button)
        audio_header.addWidget(self.action_button("close", self.close_editor, "Fechar o editor deste som."))
        edit.addLayout(audio_header)
        self.waveform = Waveform(localizer=self.i18n)
        self.waveform.setMinimumHeight(125)
        self.waveform.selectionChanged.connect(self.set_selection)
        self.waveform.viewChanged.connect(self.update_scrollbar)
        edit.addWidget(self.waveform)
        self.playback_bar = PlaybackBar(localizer=self.i18n)
        self.playback_bar.seekRequested.connect(self.seek)
        edit.addWidget(self.playback_bar)
        self.wave_scroll = QScrollBar(Qt.Orientation.Horizontal)
        self.wave_scroll.setRange(0, 10000)
        self.wave_scroll.valueChanged.connect(lambda value: self.waveform.scroll_to(value / 10000))
        self.wave_scroll.setEnabled(False)
        edit.addWidget(self.wave_scroll)

        self.transport_parking = QWidget(container)
        self.transport_parking.hide()
        self.transport = QWidget(self.transport_parking)
        self.transport.setStyleSheet("QWidget { background: transparent; } QPushButton { padding: 2px 4px; } QLabel { font-size: 11px; }")
        transport = QHBoxLayout(self.transport)
        transport.setContentsMargins(3, 2, 5, 2)
        transport.setSpacing(5)
        self.stop_button = self.button("■", self.stop)
        self.stop_button.setFixedWidth(24)
        self.ui(self.stop_button, 'setToolTip', "Parar este som e voltar ao início.")
        self.play_selection_button = self.action_button("play", self.play_selection, "Reproduzir somente a seleção.", "Play", True)
        transport.addWidget(self.stop_button)
        self.loop = QCheckBox("↻")
        self.ui(self.loop, 'setToolTip', "Repetir este som ou o trecho em reprodução.")
        transport.addWidget(self.loop)
        self.position_label = self.label("00:00.000 / 00:00.000", "muted")
        transport.addWidget(self.position_label, 1)
        transport.addWidget(self.label("Vol.", "muted"))
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setFixedWidth(48)
        self.ui(self.volume, 'setToolTip', "Volume de reprodução; não altera as amostras do som.")
        self.volume.valueChanged.connect(lambda value: self.output.setVolume(value / 100))
        transport.addWidget(self.volume)
        self.transport.hide()
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        toolbar.addWidget(self.play_selection_button)
        toolbar.addSpacing(4)
        toolbar.addWidget(self.toolbar_separator())
        self.copy_button = self.action_button("copy", self.copy_selection, "Copiar seleção para a área temporária. Ctrl+C")
        self.paste_button = self.action_button("paste", self.paste_at_cursor, "Colar o trecho na posição da barra de reprodução. Ctrl+V")
        self.remove_button = self.action_button("trash", self.remove_selected, "Remover seleção e juntar as partes restantes. Ctrl+Z desfaz")
        self.remove_button.setObjectName("delete")
        self.remove_button.setStyleSheet("QPushButton:hover { background: #563438; border-color: #ffaaa3; }")
        self.undo_button = self.action_button("undo", lambda: self.change_history("undo"), "Desfazer a última edição. Ctrl+Z")
        self.redo_button = self.action_button("redo", lambda: self.change_history("redo"), "Refazer a edição. Ctrl+Y ou Ctrl+Shift+Z")
        for button in (self.copy_button, self.paste_button, self.remove_button):
            toolbar.addWidget(button)
        toolbar.addWidget(self.toolbar_separator())
        for button in (self.undo_button, self.redo_button):
            toolbar.addWidget(button)
        toolbar.addWidget(self.toolbar_separator())
        self.all_button = self.action_button("select_all", self.select_all, "Selecionar todo o áudio. Ctrl+A")
        self.reverse_button = self.action_button("reverse", lambda: self.apply_effect("reverse"), "Inverter áudio selecionado: tocar de trás para frente, mantendo os canais.")
        self.ui(self.reverse_button, 'setAccessibleName', "Inverter áudio selecionado")
        toolbar.addWidget(self.all_button)
        toolbar.addWidget(self.reverse_button)
        toolbar.addStretch()
        toolbar.addWidget(self.action_button("zoom_out", lambda: self.waveform.zoom(.5), "Diminuir zoom da onda."))
        toolbar.addWidget(self.action_button("zoom_in", lambda: self.waveform.zoom(2), "Ampliar onda."))
        toolbar.addWidget(self.action_button("fit", self.waveform.show_all, "Ver o áudio inteiro."))
        edit.addLayout(toolbar)

        selection = QHBoxLayout()
        selection.addWidget(self.label("Início"))
        self.start_spin = QDoubleSpinBox()
        self.end_spin = QDoubleSpinBox()
        for spin in (self.start_spin, self.end_spin):
            spin.setDecimals(4)
            spin.setSingleStep(.01)
            spin.setSuffix(" s")
            spin.setFixedWidth(110)
            spin.setFixedHeight(32)
            spin.setKeyboardTracking(False)
            selection.addWidget(spin)
            if spin is self.start_spin:
                selection.addWidget(self.label("Fim"))
        self.start_spin.valueChanged.connect(lambda value: self.change_selection_edge("start", value))
        self.end_spin.valueChanged.connect(lambda value: self.change_selection_edge("end", value))
        self.selection_label = self.label("Trecho: —", "pill")
        selection.addWidget(self.selection_label)
        selection.addStretch()
        edit.addLayout(selection)

        volume_edit = QHBoxLayout()
        volume_edit.setSpacing(6)
        volume_edit.addWidget(self.label("Volume"))
        self.gain_step = QDoubleSpinBox()
        self.gain_step.setRange(.1, 24)
        self.gain_step.setDecimals(1)
        self.gain_step.setValue(3)
        self.gain_step.setSuffix(" dB")
        self.gain_step.setFixedWidth(100)
        self.gain_step.setFixedHeight(32)
        volume_edit.addWidget(self.gain_step)
        self.volume_down_button = self.action_button("volume_down", lambda: self.apply_effect("gain", -self.gain_step.value()), "Diminuir o volume da seleção pelo valor em dB ao lado.")
        self.volume_up_button = self.action_button("volume_up", lambda: self.apply_effect("gain", self.gain_step.value()), "Aumentar o volume da seleção pelo valor em dB ao lado.")
        volume_edit.addWidget(self.volume_down_button)
        volume_edit.addWidget(self.volume_up_button)
        volume_edit.addSpacing(8)
        volume_edit.addWidget(self.toolbar_separator())
        volume_edit.addSpacing(8)
        volume_edit.addWidget(self.label("Fade"))
        self.fade_duration = QDoubleSpinBox()
        self.fade_duration.setRange(.0001, 36000)
        self.fade_duration.setDecimals(4)
        self.fade_duration.setValue(.25)
        self.fade_duration.setSingleStep(.05)
        self.fade_duration.setSuffix(" s")
        self.fade_duration.setFixedWidth(110)
        self.fade_duration.setFixedHeight(32)
        volume_edit.addWidget(self.fade_duration)
        self.fade_in_button = self.action_button("fade_in", lambda: self.apply_effect("fade_in", self.fade_duration.value()), "Fade in: aumentar suavemente no início da seleção pela duração indicada.")
        self.fade_out_button = self.action_button("fade_out", lambda: self.apply_effect("fade_out", self.fade_duration.value()), "Fade out: diminuir suavemente no final da seleção pela duração indicada.")
        volume_edit.addWidget(self.fade_in_button)
        volume_edit.addWidget(self.fade_out_button)
        volume_edit.addStretch()
        edit.addLayout(volume_edit)

        actions = QHBoxLayout()
        self.edit_state_label = self.label("Original", "pill")
        actions.addWidget(self.edit_state_label)
        self.clipboard_label = self.label("Cópia: vazia", "muted")
        self.clipboard_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        actions.addWidget(self.clipboard_label, 1)
        self.export_button = self.action_button("save", self.save_selection, "Salvar a seleção em um novo arquivo. Ctrl+Shift+S", "Salvar trecho…", True)
        self.export_all_button = self.action_button("save", self.save_current_audio, "Salvar todo o áudio no arquivo aberto, após confirmação. Ctrl+S", "Salvar áudio")
        actions.addWidget(self.export_all_button)
        actions.addWidget(self.export_button)
        edit.addLayout(actions)
        self.editor_parking = QWidget(container)
        self.editor_parking.hide()
        self.editor.setParent(self.editor_parking)
        self.editor.hide()
        self.splitter.addWidget(main)
        self.splitter.setSizes([290, 910])
        outer.addWidget(self.splitter, 1)
        self.setCentralWidget(container)
        self.ui(self.statusBar(), 'showMessage', "Pronto para explorar sua biblioteca.")
        self.shortcuts = []
        for key, action in [("Space", self.toggle_play), ("Ctrl+O", self.open_file), ("Ctrl+C", self.copy_selection),
                            ("Ctrl+Shift+S", self.save_selection), ("Ctrl+S", self.save_current_audio), ("Ctrl+V", self.paste_at_cursor), ("Alt+Up", self.go_up),
                            ("Ctrl+Z", lambda: self.change_history("undo")), ("Ctrl+Y", lambda: self.change_history("redo")),
                            ("Ctrl+Shift+Z", lambda: self.change_history("redo"))]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(action)
            self.shortcuts.append(shortcut)
        self.set_audio_enabled(False)

    def eventFilter(self, watched, event):
        # The editor is embedded inside the file list; intercept before that list
        # consumes Ctrl+A, including when it still has focus after opening a row.
        if (event.type() in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress)
                and isinstance(watched, QWidget) and watched.window() is self
                and self.editor.isVisible() and self.editor_path is not None
                and event.matches(QKeySequence.StandardKey.SelectAll)
                and not isinstance(QApplication.focusWidget(), QLineEdit)):
            if event.type() == QEvent.Type.KeyPress and self.clip and self.document_key() == self.editor_path:
                if self.load_token is None and self.edit_token is None:
                    self.select_all()
            event.accept()
            return True
        return super().eventFilter(watched, event)

    def set_audio_enabled(self, enabled):
        enabled = bool(enabled and self.clip and self.load_token is None and self.edit_token is None)
        for widget in (self.stop_button, self.play_selection_button, self.copy_button,
                       self.export_button, self.export_all_button, self.all_button, self.start_spin, self.end_spin,
                       self.waveform):
            widget.setEnabled(enabled)
        if self.exporting:
            self.export_button.setEnabled(False)
            self.export_all_button.setEnabled(False)
        self.update_edit_controls(enabled)
        self.update_file_actions()

    def update_edit_controls(self, enabled=None):
        ready = bool(self.clip and self.load_token is None and self.edit_token is None)
        if enabled is not None:
            ready = ready and enabled
        has_audio = bool(self.clip is not None and len(self.clip.samples))
        selected = has_audio and self.waveform.selection[1] > self.waveform.selection[0]
        for control in (self.gain_step, self.fade_duration, self.volume_down_button, self.volume_up_button,
                        self.reverse_button, self.fade_in_button, self.fade_out_button, self.remove_button,
                        self.copy_button):
            control.setEnabled(ready and selected)
        active_playback = self.player.playbackState() != QMediaPlayer.PlaybackState.StoppedState
        self.play_selection_button.setEnabled(ready and has_audio and (selected or active_playback))
        for control in (self.stop_button, self.all_button, self.start_spin, self.end_spin, self.playback_bar):
            control.setEnabled(ready and has_audio)
        self.export_button.setEnabled(ready and selected and not self.exporting)
        self.export_all_button.setEnabled(ready and has_audio and not self.exporting)
        self.paste_button.setEnabled(ready and self.copied_clip is not None)
        self.undo_button.setEnabled(ready and bool(self.undo_stack))
        self.redo_button.setEnabled(ready and bool(self.redo_stack))
        self.ui(self.edit_state_label, 'setText', "Alterado · salvar" if self.modified else "Original")

    def restore_preferences(self):
        self.volume.setValue(int(self.settings.value("volume", 80)))
        self.loop.setChecked(self.settings.value("loop", False, type=bool))
        if geometry := self.settings.value("geometry"):
            self.restoreGeometry(geometry)
            if not any(screen.availableGeometry().intersects(self.frameGeometry()) for screen in QApplication.screens()):
                self.move(QApplication.primaryScreen().availableGeometry().topLeft())
        if splitter := self.settings.value("splitter"):
            self.splitter.restoreState(splitter)
        base = self.settings.value("base", "")
        if base and Path(base).is_dir():
            self.set_base(Path(base), restore=True)

    def persist(self):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("splitter", self.splitter.saveState())
        self.settings.setValue("volume", self.volume.value())
        self.settings.setValue("loop", self.loop.isChecked())
        if self.base:
            self.settings.setValue("base", str(self.base))
        if self.folder:
            self.settings.setValue("folder", str(self.folder))
        self.settings.sync()

    def choose_base(self):
        start = str(self.base or default_library_dir())
        chosen = QFileDialog.getExistingDirectory(self, self.t("Escolha a pasta base da sua biblioteca de sons"), start, options=QFileDialog.Option.DontUseNativeDialog)
        if chosen:
            self.set_base(Path(chosen))

    def set_base(self, base, restore=False):
        self.folder_scan_cancel.set()
        self.folder_scan_cancel = Event()
        self.folder_scan_token = None
        self.folder_index = None
        self.folder_search.clear()
        self.base = base.resolve()
        self.ui(self.base_label, 'setText', 'Biblioteca: {0}', self.base.name)
        self.ui(self.base_label, 'setToolTip', str(self.base))
        self.folder_model.setRootPath(str(self.base))
        self.tree.setRootIndex(self.folder_model.index(str(self.base)))
        self.tree.setColumnWidth(0, 240)
        folder = self.base
        saved = self.settings.value("folder", "") if restore else ""
        if saved and Path(saved).is_dir() and Path(saved).resolve().is_relative_to(self.base):
            folder = Path(saved).resolve()
        self.navigate(folder)

    def folder_clicked(self, index):
        path = Path(self.folder_model.filePath(index)).resolve()
        if self.base and path.is_relative_to(self.base):
            self.navigate(path)

    def schedule_folder_filter(self, *_):
        if self.folder_search.text():
            self.folder_filter_timer.start()

    def filter_folders(self, text):
        self.apply_folder_filter()
        if text and self.base and self.folder_index is None and self.folder_scan_token is None:
            token = uuid.uuid4().hex
            self.folder_scan_token = token
            base, cancelled = self.base, self.folder_scan_cancel
            self.submit(token, lambda: index_library(base, cancelled), self.on_folders_indexed)

    @Slot(object, object, str)
    def on_folders_indexed(self, token, result, error):
        if token != self.folder_scan_token:
            return
        self.folder_scan_token = None
        if error:
            self.ui(self.statusBar(), 'showMessage', 'Não foi possível filtrar as pastas: {0}', error)
            return
        self.folder_index = result
        self.apply_folder_filter()

    def apply_folder_filter(self):
        if not self.base:
            return
        query = self.folder_search.text().casefold()
        searching = bool(query and self.folder_index is None)
        self.ui(self.folders_heading, 'setText', "PASTAS · buscando…" if searching else "PASTAS")
        allowed = set()
        if query and self.folder_index is not None:
            for path, file_names in self.folder_index.items():
                if query in path.name.casefold() or any(query in name for name in file_names):
                    allowed.add(path)
                    parent = path.parent
                    while parent != self.base and parent.is_relative_to(self.base):
                        allowed.add(parent)
                        self.tree.expand(self.folder_model.index(str(parent)))
                        parent = parent.parent
                    self.folder_model.index(str(path))

        def visit(parent):
            found = False
            for row in range(self.folder_model.rowCount(parent)):
                index = self.folder_model.index(row, 0, parent)
                path = Path(self.folder_model.filePath(index))
                child_matches = visit(index)
                visible = not query or query in path.name.casefold() or path in allowed or child_matches
                self.tree.setRowHidden(row, parent, not visible)
                if query and child_matches:
                    self.tree.expand(index)
                found = found or visible
            return found

        visit(self.tree.rootIndex())
        self.ui(self.tree, "empty_message", ("Buscando nas pastas e nos arquivos…" if searching else "Nenhuma pasta ou arquivo corresponde ao filtro.") if query else "Esta biblioteca não tem subpastas.")
        self.tree.viewport().update()

    def navigate(self, folder):
        try:
            entries = list(folder.iterdir())
        except OSError as exc:
            self.show_error("Não foi possível abrir a pasta", str(exc))
            return
        self.folder = folder.resolve()
        self.close_editor()
        self.detach_transport()
        self.search.clear()
        self.files.clear()
        sounds = 0
        entries.sort(key=lambda path: path.name.casefold())
        for path in entries:
            if path.name.startswith((".", "__")):
                continue
            try:
                if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                    continue
                size = self.size_label(path.stat().st_size)
                item = QTreeWidgetItem(["", path.name, f"{path.suffix[1:].upper()} · {size}", ""])
                item.setData(1, Qt.ItemDataRole.UserRole, str(path))
                item.setToolTip(1, str(path))
                item.setData(0, Qt.ItemDataRole.UserRole, str(path))
                item.setToolTip(0, self.t("▶ ouvir / pausar   ·   Recortar abre a onda nesta linha"))
                sounds += 1
                item.setSizeHint(0, QSize(42, 34))
                self.files.addTopLevelItem(item)
            except OSError:
                continue
        relative = self.folder.relative_to(self.base) if self.base and self.folder.is_relative_to(self.base) else self.folder
        self.ui(self.folder_label, 'setText', "{0}", self.base.name if str(relative) == "." else str(relative))
        self.ui(self.folder_label, 'setToolTip', str(self.folder))
        self.up_button.setEnabled(bool(self.base and self.folder.is_relative_to(self.base) and self.folder != self.base))
        self.ui(self.file_header, 'setToolTip', '{0} arquivo(s) de áudio · arraste pelo nome para copiar', sounds, prefix=(1,))
        self.ui(self.files, "empty_message", "Nenhum arquivo de áudio nesta pasta.\nEscolha outra pasta à esquerda.")
        if self.base and self.folder.is_relative_to(self.base):
            self.tree.setCurrentIndex(self.folder_model.index(str(self.folder)))
        self.update_file_actions()
        self.settings.setValue("folder", str(self.folder))
        if self.base:
            self.settings.setValue("base", str(self.base))
        self.settings.sync()

    @staticmethod
    def size_label(size):
        return f"{size / 1024 / 1024:.1f} MB" if size >= 1024 * 1024 else f"{size / 1024:.1f} KB"

    def refresh_folder(self):
        if self.folder:
            self.invalidate_folder_index()
            editor_path = self.editor_path
            self.navigate(self.folder)
            if editor_path and self.row_for_path(editor_path):
                self.toggle_editor(editor_path)

    def invalidate_folder_index(self):
        self.folder_scan_cancel.set()
        self.folder_scan_cancel = Event()
        self.folder_scan_token = None
        self.folder_index = None
        self.filter_folders(self.folder_search.text())

    def record_created_files(self, paths):
        if self.folder_scan_token is not None:
            self.invalidate_folder_index()
        elif self.folder_index is not None:
            for path in paths:
                if self.base and path.is_relative_to(self.base):
                    names = self.folder_index.setdefault(path.parent, [])
                    if path.name.casefold() not in names:
                        names.append(path.name.casefold())
            self.apply_folder_filter()

    def go_up(self):
        if self.base and self.folder and self.folder.is_relative_to(self.base) and self.folder != self.base:
            self.navigate(self.folder.parent)

    def filter_rows(self, text):
        shown = 0
        for row in range(self.files.topLevelItemCount()):
            item = self.files.topLevelItem(row)
            visible = text.casefold() in item.text(1).casefold()
            item.setHidden(not visible)
            shown += visible
        if text:
            self.ui(self.file_header, 'setToolTip', '{0} resultado(s) nesta pasta', shown, prefix=(1,))
            self.ui(self.files, "empty_message", "Nenhum arquivo corresponde ao filtro.")
        else:
            self.ui(self.file_header, 'setToolTip', '{0} arquivo(s) de áudio · arraste pelo nome para copiar', self.files.topLevelItemCount(), prefix=(1,))
            self.ui(self.files, "empty_message", "Nenhum arquivo de áudio nesta pasta.\nEscolha outra pasta à esquerda.")
        self.files.viewport().update()

    def file_clicked(self, item, column):
        pass  # Names select files and initiate native drags; only explicit actions load audio.

    def file_activated(self, item, column):
        path = item.data(1, Qt.ItemDataRole.UserRole)
        if path and column != 0:
            self.play_file(Path(path))

    def row_for_path(self, path):
        for number in range(self.files.topLevelItemCount()):
            row = self.files.topLevelItem(number)
            if Path(row.data(1, Qt.ItemDataRole.UserRole)).resolve() == path.resolve():
                return row
        return None

    def toggle_editor(self, path):
        row = self.row_for_path(path)
        if row is None:
            return
        if self.editor_row is row:
            self.close_editor()
            return
        self.close_editor()
        child = QTreeWidgetItem(row)
        child.setFirstColumnSpanned(True)
        child.setFlags(Qt.ItemFlag.ItemIsEnabled)
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(6, 8, 6, 12)
        layout.addWidget(self.editor)
        self.editor.show()
        height = self.editor.minimumSizeHint().height() + 20
        child.setSizeHint(0, QSize(0, height))
        self.files.setItemWidget(child, 0, host)
        self.editor_row, self.editor_child, self.editor_host = row, child, host
        self.editor_path = path.resolve()
        row.setExpanded(True)
        self.update_file_actions()
        self.open_audio(path)
        self.files.scrollToItem(row, QAbstractItemView.ScrollHint.PositionAtTop)

    def close_editor(self):
        if not self.editor_row:
            return
        row, child = self.editor_row, self.editor_child
        self.editor_host.hide()
        self.editor.hide()
        self.editor.setParent(self.editor_parking)
        self.files.removeItemWidget(child, 0)
        row.takeChild(row.indexOfChild(child))
        row.setExpanded(False)
        self.editor_row = self.editor_child = self.editor_host = self.editor_path = None
        self.update_file_actions()

    def play_file(self, path):
        if self.clip and self.clip.source == path.resolve() and self.clip.name == path.name and self.load_token is None:
            self.toggle_play()
        else:
            self.open_audio(path, True)

    def detach_transport(self):
        if self.transport_row is not None:
            self.transport_host.hide()
            self.transport.hide()
            self.transport.setParent(self.transport_parking)
            self.files.removeItemWidget(self.transport_row, 3)
            self.transport_row = self.transport_host = None

    def attach_transport(self):
        row = self.row_for_path(self.transport_path) if self.transport_path else None
        if row is self.transport_row:
            return
        self.detach_transport()
        if row is not None:
            host = QWidget()
            layout = QHBoxLayout(host)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.transport)
            self.files.setItemWidget(row, 3, host)
            self.transport_row, self.transport_host = row, host
            self.transport.show()

    def update_file_actions(self):
        if not hasattr(self, "transport"):
            return
        self.attach_transport()
        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        for number in range(self.files.topLevelItemCount()):
            row = self.files.topLevelItem(number)
            path = Path(row.data(1, Qt.ItemDataRole.UserRole))
            active = self.clip and self.clip.source == path.resolve() and self.clip.name == path.name
            row.setData(0, Qt.ItemDataRole.UserRole + 1, "playing" if active and playing else "")
            row.setData(0, Qt.ItemDataRole.UserRole + 2, row is self.editor_row)
            busy = self.transport_path == path.resolve() and (self.load_token is not None or self.edit_token is not None)
            row.setData(0, Qt.ItemDataRole.UserRole + 3, busy or bool(active and not len(self.clip.samples)))
            duration = self.edit_cache[path.resolve()]["clip"].duration if path.resolve() in self.edit_cache else self.known_durations.get(path.resolve())
            row.setText(3, f"00:00.000 / {time_label(duration)}" if duration is not None else "")
        self.files.viewport().update()

    def copy_to_folder(self, paths, folder):
        token = uuid.uuid4().hex
        self.copy_jobs.add(token)
        self.ui(self.statusBar(), 'showMessage', 'Copiando {0} arquivo(s) para {1}…', len(paths), folder)
        copy_label = "copy" if self.i18n.language == "en" else "cópia"
        self.submit(token, lambda: copy_files(paths, folder, copy_label), self.on_copied_files)

    @Slot(object, object, str)
    def on_copied_files(self, token, result, error):
        self.copy_jobs.discard(token)
        if error:
            self.show_error("Erro ao copiar arquivos", error)
        else:
            self.ui(self.statusBar(), 'showMessage', 'Copiado(s) {0} arquivo(s) para {1}', len(result), result[0].parent)
            if self.folder == result[0].parent:
                self.refresh_folder()
            else:
                self.record_created_files(result)

    def open_file(self):
        patterns = " ".join(f"*{extension}" for extension in sorted(EXTENSIONS))
        filename, _ = QFileDialog.getOpenFileName(self, self.t("Abrir som"), str(self.folder or default_library_dir()), self.t('Áudio ({0});;Todos os arquivos (*)', patterns), options=QFileDialog.Option.DontUseNativeDialog)
        if filename:
            path = Path(filename)
            if not self.base:
                self.set_base(path.parent)
            else:
                self.navigate(path.parent)
            self.toggle_editor(path)

    def submit(self, token, function, callback):
        worker = Worker(token, function)
        self.jobs[token] = worker
        worker.signals.finished.connect(callback)
        worker.signals.finished.connect(lambda token, *_: self.jobs.pop(token, None))
        self.pool.start(worker)

    def open_audio(self, path, autoplay=False):
        path = path.resolve()
        if self.edit_token and self.clip and self.clip.source == path:
            return
        if self.editor_path and path != self.editor_path:
            self.close_editor()
        if self.clip and self.clip.source == path and self.clip.name == path.name and self.load_token is None:
            if autoplay and len(self.clip.samples):
                self.selection_token = None
                self.player.pause()
                self.player.setSource(QUrl.fromLocalFile(str(self.preview_path)))
                self.play_origin, self.play_limit = 0.0, self.clip.duration
                self.selection_playback = False
                self.player.setPosition(0)
                self.player.play()
            return
        self.stash_current_document()
        self.edit_token = None
        self.pending_document_state = self.edit_cache.get(path)
        self.transport_path = path
        self.ui(self.position_label, 'setText', "Abrindo…")
        self.stop()
        self.player.setSource(QUrl())
        self.clip = None
        self.waveform.clip = None
        self.waveform.update()
        self.playback_bar.set_duration(0)
        self.source_button.setEnabled(False)
        self.set_audio_enabled(False)
        self.pending_play = autoplay
        token = uuid.uuid4().hex
        self.load_token = token
        self.ui(self.name_label, 'setText', 'Carregando {0}…', path.name)
        self.ui(self.info_label, 'setText', "Lendo o áudio e preparando a forma de onda…")
        self.ui(self.statusBar(), 'showMessage', 'Abrindo {0}…', path.name)
        pending_edit = next((token for token, state in self.edit_jobs.items() if state["key"] == path), None)
        if pending_edit is not None:
            self.load_token = None
            self.edit_token = pending_edit
            self.update_file_actions()
            self.ui(self.statusBar(), 'showMessage', 'Concluindo a edição de {0}…', path.name)
            return
        preview = Path(self.temporary.name) / f"{token}.wav"
        cached = self.pending_document_state
        def prepare():
            clip = cached["clip"] if cached else load_audio(path)
            write_preview(clip, preview)
            return clip, preview
        self.update_file_actions()
        self.submit(token, prepare, self.on_loaded)

    @Slot(object, object, str)
    def on_loaded(self, token, result, error):
        if token != self.load_token:
            if result:
                result[1].unlink(missing_ok=True)
            return
        self.load_token = None
        if error:
            self.ui(self.name_label, 'setText', "Não foi possível abrir o som")
            self.ui(self.info_label, 'setText', "Escolha outro arquivo na biblioteca.")
            self.ui(self.position_label, 'setText', "Erro ao abrir")
            self.update_file_actions()
            self.show_error("Erro ao abrir áudio", error)
            return
        clip, preview = result
        self.install_clip(clip, preview)
        if self.pending_document_state:
            self.restore_document_state(self.pending_document_state)
        self.pending_document_state = None
        if self.pending_play and len(clip.samples):
            self.play_origin, self.play_limit = 0.0, clip.duration
            self.selection_playback = False
            self.player.play()

    def install_clip(self, clip, preview):
        old_preview = self.preview_path
        self.player.stop()
        self.player.setSource(QUrl())
        self.clip, self.preview_path = clip, preview
        self.modified = False
        self.undo_stack = []
        self.redo_stack = []
        if len(clip.samples):
            self.player.setSource(QUrl.fromLocalFile(str(preview)))
        if old_preview and old_preview != preview:
            try:
                old_preview.unlink(missing_ok=True)
            except OSError:
                pass
        self.play_limit = None
        self.play_origin = 0.0
        self.selection_playback = False
        self.ui(self.name_label, 'setText', "{0}", self.display_clip_name())
        self.transport_path = clip.source if clip.source and clip.name == clip.source.name else None
        if self.transport_path:
            self.known_durations[self.transport_path] = clip.duration
        self.ui(self.name_label, 'setToolTip', "{0}", self.display_clip_name())
        source_format = clip.source.suffix[1:].upper() if clip.source else Message("ÁUDIO COPIADO")
        self.ui(self.info_label, 'setText', '{0}    ·    {1:,} Hz    ·    {2}    ·    {3}', time_label(clip.duration), clip.sample_rate, 'Mono' if clip.channels == 1 else Message('{0} canais', (clip.channels,)), source_format)
        self.source_button.setEnabled(bool(clip.source))
        for spin in (self.start_spin, self.end_spin):
            spin.blockSignals(True)
            spin.setRange(0, clip.duration)
            spin.blockSignals(False)
        self.waveform.set_clip(clip)
        self.playback_bar.set_duration(clip.duration)
        self.set_selection(0, clip.duration)
        self.set_audio_enabled(True)
        self.on_position(0)
        self.update_file_actions()
        self.ui(self.statusBar(), 'showMessage', "Som aberto. Use Recortar na linha para selecionar um trecho.")

    def document_snapshot(self):
        return {"clip": self.clip, "selection": self.waveform.selection, "cursor": self.waveform.cursor,
                "modified": self.modified, "view": (self.waveform.view_start, self.waveform.view_length)}

    def document_key(self):
        if self.clip and self.clip.source and self.clip.name == self.clip.source.name:
            return self.clip.source
        return None

    def stash_current_document(self):
        key = self.document_key()
        if key and (self.modified or self.undo_stack or self.redo_stack or key in self.saved_clips):
            state = self.document_snapshot()
            state.update(undo=list(self.undo_stack), redo=list(self.redo_stack))
            self.edit_cache[key] = state

    def restore_document_state(self, state):
        key = self.document_key()
        self.modified = self.clip is not self.saved_clips[key] if key in self.saved_clips else state["modified"]
        self.undo_stack, self.redo_stack = list(state.get("undo", [])), list(state.get("redo", []))
        self.set_selection(*state["selection"])
        start, length = state.get("view", (0, self.clip.duration))
        self.waveform.view_length = min(max(length, min(.02, self.clip.duration)), self.clip.duration)
        self.waveform.view_start = min(max(0, start), self.clip.duration - self.waveform.view_length)
        self.waveform.viewChanged.emit(self.waveform.view_start, self.waveform.view_length)
        self.seek(min(state["cursor"], self.clip.duration))
        self.ui(self.name_label, 'setText', '{0}{1}', self.display_clip_name(), Message(' · alterado' if self.modified else ''))
        self.update_edit_controls()

    @staticmethod
    def trim_history(history):
        history = list(history)
        while len(history) > 20 or (len(history) > 1 and sum(state["clip"].samples.nbytes for state in history) > 128 * 1024 * 1024):
            history.pop(0)
        return history

    def start_change(self, operation, label, history="edit", target=None):
        if not self.clip or self.load_token is not None or self.edit_token is not None:
            return
        before = self.document_snapshot()
        undo, redo = list(self.undo_stack), list(self.redo_stack)
        if history == "undo":
            undo = undo[:-1]
            redo.append(before)
        elif history == "redo":
            undo.append(before)
            redo = redo[:-1]
        else:
            undo.append(before)
            redo = []
        token = uuid.uuid4().hex
        context = {"key": self.document_key(), "label": label, "undo": self.trim_history(undo),
                   "redo": self.trim_history(redo), "before": before, "target": target}
        self.edit_jobs[token] = context
        self.edit_token = token
        self.stop()
        self.set_audio_enabled(False)
        self.ui(self.statusBar(), 'showMessage', '{0}…', Message(label))
        preview = Path(self.temporary.name) / f"edit-{token}.wav"
        def prepare():
            clip, selection, cursor = operation()
            write_preview(clip, preview)
            return clip, preview, selection, cursor
        self.submit(token, prepare, self.on_change_finished)

    @Slot(object, object, str)
    def on_change_finished(self, token, result, error):
        context = self.edit_jobs.pop(token, None)
        if not context:
            return
        active = token == self.edit_token
        if active:
            self.edit_token = None
        if error:
            if active:
                if self.clip is None and context["key"]:
                    self.open_audio(context["key"])
                else:
                    self.set_audio_enabled(bool(self.clip))
            self.show_error("Não foi possível editar o áudio", error)
            return
        clip, preview, selection, cursor = result
        target = context["target"]
        state = {"clip": clip, "selection": selection, "cursor": cursor,
                 "modified": target["modified"] if target else True,
                 "view": target["view"] if target else context["before"]["view"],
                 "undo": context["undo"], "redo": context["redo"]}
        if context["key"] in self.saved_clips:
            state["modified"] = clip is not self.saved_clips[context["key"]]
        if context["label"] in {"Colar trecho", "Remover seleção"}:
            state["view"] = (0, clip.duration)
        if context["key"]:
            self.edit_cache[context["key"]] = state
        if active:
            self.pending_document_state = None
            self.install_clip(clip, preview)
            self.restore_document_state(state)
            message = Message("{0}: concluído.", (Message(context["label"]),))
            if len(clip.samples) and np.max(np.abs(clip.samples)) > 1:
                message = Message("{0}{1}", (message, Message(" O pico ultrapassa o limite; diminua o volume para evitar distorção.")))
            self.ui(self.statusBar(), 'showMessage', message)
        else:
            preview.unlink(missing_ok=True)

    def apply_effect(self, effect, value=0):
        if not self.clip:
            return
        clip, selection, cursor = self.clip, self.waveform.selection, self.waveform.cursor
        labels = {"gain": "Aumentar volume" if value > 0 else "Diminuir volume", "reverse": "Inverter trecho",
                  "polarity": "Inverter polaridade", "fade_in": "Aplicar fade in", "fade_out": "Aplicar fade out"}
        self.start_change(lambda: (edit_selection(clip, *selection, effect, value), selection, cursor), labels[effect])

    def remove_selected(self):
        if not self.clip or self.waveform.selection[1] <= self.waveform.selection[0]:
            return
        clip, selection = self.clip, self.waveform.selection
        def remove():
            edited, join = remove_selection(clip, *selection)
            return edited, (join, join), join
        self.start_change(remove, "Remover seleção")

    def change_history(self, direction):
        focus = QApplication.focusWidget()
        if isinstance(focus, QLineEdit):
            focus.undo() if direction == "undo" else focus.redo()
            return
        history = self.undo_stack if direction == "undo" else self.redo_stack
        if not history:
            return
        target = history[-1]
        self.start_change(lambda: (target["clip"], target["selection"], target["cursor"]),
                          "Desfazer" if direction == "undo" else "Refazer", history=direction, target=target)

    def paste_at_cursor(self):
        focus = QApplication.focusWidget()
        if isinstance(focus, QLineEdit):
            focus.paste()
            return
        if not self.clip or not self.copied_clip:
            return
        clip, copied, position = self.clip, self.copied_clip, self.waveform.cursor
        def paste():
            edited, selection = insert_clip(clip, copied, position)
            return edited, selection, selection[0]
        self.start_change(paste, "Colar trecho")

    def set_selection(self, start, end):
        if not self.clip:
            return
        start = min(self.clip.duration, max(0, start))
        end = min(self.clip.duration, max(0, end))
        if end < start:
            return
        self.waveform.set_selection(start, end)
        for spin, value in ((self.start_spin, start), (self.end_spin, end)):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)
        self.ui(self.selection_label, 'setText', 'Trecho: {0:.4f} s', end - start)
        self.update_edit_controls()

    def change_selection_edge(self, edge, value):
        if not self.clip:
            return
        start, end = self.waveform.selection
        minimum = 1 / self.clip.sample_rate
        if edge == "start":
            start = max(0, min(value, end - minimum))
        else:
            end = min(self.clip.duration, max(value, start + minimum))
        self.set_selection(start, end)

    def select_all(self):
        if self.clip:
            self.set_selection(0, self.clip.duration)

    def update_scrollbar(self, start, length):
        if not self.waveform.clip:
            return
        duration = self.waveform.clip.duration
        available = max(0, duration - length)
        self.wave_scroll.blockSignals(True)
        self.wave_scroll.setEnabled(available > 1e-6)
        self.wave_scroll.setPageStep(max(1, int(length / max(available, .001) * 10000)))
        self.wave_scroll.setValue(int(start / available * 10000) if available else 0)
        self.wave_scroll.blockSignals(False)

    def toggle_play(self):
        if not self.clip or not len(self.clip.samples) or self.edit_token is not None or self.load_token is not None:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self.player.playbackState() != QMediaPlayer.PlaybackState.PausedState:
                self.selection_token = None
                if self.selection_playback:
                    self.player.setSource(QUrl.fromLocalFile(str(self.preview_path)))
                self.selection_playback = False
                self.play_origin, self.play_limit = 0.0, self.clip.duration
                if self.player.position() >= max(0, int(self.clip.duration * 1000) - 2):
                    self.player.setPosition(0)
            self.player.play()

    def play_selection(self):
        if not self.clip or self.edit_token is not None or self.load_token is not None:
            return
        state = self.player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            return
        if (state == QMediaPlayer.PlaybackState.PausedState and self.selection_playback
                and (self.play_origin, self.play_limit) == self.waveform.selection):
            self.player.play()
            return
        if self.selection_token is not None:
            return
        try:
            clip = self.selection_clip()
        except ValueError as exc:
            self.show_error("Trecho inválido", str(exc))
            return
        self.stop()
        token = uuid.uuid4().hex
        self.selection_token = token
        start, end = self.waveform.selection
        preview = Path(self.temporary.name) / f"selection-{token}.wav"
        self.ui(self.statusBar(), 'showMessage', "Preparando a reprodução do trecho…")
        def prepare():
            write_preview(clip, preview)
            return preview, start, end
        self.submit(token, prepare, self.on_selection_ready)

    @Slot(object, object, str)
    def on_selection_ready(self, token, result, error):
        if token != self.selection_token:
            if result:
                result[0].unlink(missing_ok=True)
            return
        self.selection_token = None
        if error:
            self.show_error("Erro ao reproduzir trecho", error)
            return
        preview, start, end = result
        old_preview = self.selection_preview
        self.player.setSource(QUrl())
        self.selection_preview = preview
        self.selection_playback = True
        self.play_origin, self.play_limit = start, end
        self.player.setSource(QUrl.fromLocalFile(str(preview)))
        if old_preview:
            try:
                old_preview.unlink(missing_ok=True)
            except OSError:
                pass
        self.player.play()
        self.ui(self.statusBar(), 'showMessage', 'Reproduzindo trecho: {0:.4f} s — {1:.4f} s', start, end)

    def stop(self):
        self.selection_token = None
        self.play_limit = None
        self.player.stop()
        if self.selection_playback and self.preview_path:
            self.player.setSource(QUrl.fromLocalFile(str(self.preview_path)))
        self.selection_playback = False
        self.waveform.set_cursor(0)
        self.playback_bar.set_cursor(0)

    def seek(self, seconds):
        if self.clip:
            seconds = min(self.clip.duration, max(0, seconds))
            self.selection_token = None
            if self.selection_playback:
                was_playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
                self.player.setSource(QUrl.fromLocalFile(str(self.preview_path)))
                if was_playing:
                    self.player.play()
            self.selection_playback = False
            self.play_origin, self.play_limit = 0, self.clip.duration
            self.player.setPosition(round(seconds * 1000))
            self.waveform.set_cursor(seconds)
            self.playback_bar.set_cursor(seconds)

    def on_position(self, milliseconds):
        if not self.clip:
            return
        seconds = min(self.clip.duration, max(0, milliseconds / 1000 + (self.play_origin if self.selection_playback else 0)))
        self.waveform.set_cursor(seconds)
        self.playback_bar.set_cursor(seconds)
        self.ui(self.position_label, 'setText', '{0} / {1}', time_label(seconds), time_label(self.clip.duration))

    def on_playback_state(self, state):
        if hasattr(self, "play_selection_button"):
            playing = state == QMediaPlayer.PlaybackState.PlayingState
            self.ui(self.play_selection_button, 'setText', "Pausa" if playing else "Play")
            self.play_selection_button.setIcon(editor_icon("pause" if playing else "play", True))
            tooltip = "Pausar a reprodução. Espaço" if playing else "Reproduzir / retomar a seleção. Espaço"
            self.ui(self.play_selection_button, 'setToolTip', tooltip)
            self.ui(self.play_selection_button, 'setAccessibleName', tooltip)
            self.update_edit_controls()
        if hasattr(self, "files"):
            self.update_file_actions()

    def on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self.clip and self.loop.isChecked() and self.play_limit is not None:
            self.player.setPosition(0)
            self.player.play()

    def on_player_error(self, error, message):
        if error != QMediaPlayer.Error.NoError:
            self.ui(self.statusBar(), 'showMessage', 'Falha na reprodução: {0}', message)

    def selection_clip(self):
        if not self.clip:
            raise ValueError("Abra um som primeiro.")
        return self.clip.cut(*self.waveform.selection)

    def copy_selection(self):
        focus = QApplication.focusWidget()
        if isinstance(focus, QLineEdit) and focus.hasSelectedText():
            focus.copy()
            return
        if not self.clip:
            return
        try:
            self.copied_clip = self.selection_clip()
            payload = io.BytesIO()
            sf.write(payload, self.copied_clip.samples, self.copied_clip.sample_rate, format="WAV", subtype="PCM_24")
            mime = QMimeData()
            mime.setData("audio/wav", payload.getvalue())
            start, end = self.waveform.selection
            mime.setText(f"{self.clip.name} | {start:.4f}s — {end:.4f}s")
            QApplication.clipboard().setMimeData(mime)
            self.paste_button.setEnabled(True)
            self.ui(self.clipboard_label, 'setText', 'Cópia: {0:.4f} s', self.copied_clip.duration)
            self.ui(self.clipboard_label, 'setToolTip', '{0} · {1} Hz · {2:.4f} s — {3:.4f} s', self.clip.name, self.copied_clip.sample_rate, start, end)
            self.ui(self.paste_button, 'setToolTip', 'Colar {0:.4f} s na posição da barra de reprodução. Ctrl+V', self.copied_clip.duration)
            self.ui(self.statusBar(), 'showMessage', 'Trecho de {0:.4f} s copiado. Abra outro som, posicione a barra de reprodução e use o ícone Colar.', self.copied_clip.duration)
        except Exception as exc:
            self.show_error("Erro ao copiar trecho", str(exc))

    def open_copied(self):
        focus = QApplication.focusWidget()
        if isinstance(focus, QLineEdit):
            focus.paste()
            return
        if not self.copied_clip:
            return
        self.stash_current_document()
        self.edit_token = None
        self.pending_document_state = None
        self.stop()
        self.load_token = uuid.uuid4().hex
        self.pending_play = False
        self.set_audio_enabled(False)
        token = self.load_token
        preview = Path(self.temporary.name) / f"{token}.wav"
        clip = self.copied_clip
        def prepare():
            write_preview(clip, preview)
            return clip, preview
        self.submit(token, prepare, self.on_loaded)

    def save_current_audio(self):
        if not self.clip or self.exporting or self.load_token is not None or self.edit_token is not None:
            return
        key = self.document_key()
        if key is None:
            self.save_selection(whole=True)
            return
        clip = self.clip
        answer = QMessageBox.question(self, self.t("Salvar áudio?"),
                                     self.t('Deseja salvar as alterações neste arquivo?\n\n{0}\n\nO arquivo será substituído pelo áudio completo em edição.', key),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        token = uuid.uuid4().hex
        self.save_jobs[token] = (key, clip)
        self.exporting = True
        self.update_edit_controls()
        self.ui(self.statusBar(), 'showMessage', 'Salvando {0}…', key.name)
        self.submit(token, lambda: save_audio(clip), self.on_audio_saved)

    @Slot(object, object, str)
    def on_audio_saved(self, token, result, error):
        key, clip = self.save_jobs.pop(token)
        self.exporting = False
        if error:
            self.show_error("Erro ao salvar áudio", error)
        else:
            self.saved_clips[key] = clip
            if cached := self.edit_cache.get(key):
                cached["modified"] = cached["clip"] is not clip
            if self.document_key() == key:
                self.modified = self.clip is not clip
                self.ui(self.name_label, 'setText', '{0}{1}', self.display_clip_name(), Message(' · alterado' if self.modified else ''))
                self.stash_current_document()
            if row := self.row_for_path(key):
                try:
                    row.setText(2, f"{key.suffix[1:].upper()} · {self.size_label(key.stat().st_size)}")
                except OSError:
                    pass
            self.ui(self.statusBar(), 'showMessage', 'Salvo: {0}', result)
        self.update_edit_controls()

    def save_selection(self, checked=False, whole=False):
        if not self.clip or self.exporting or self.edit_token is not None:
            return
        try:
            clip = self.clip if whole else self.selection_clip()
        except ValueError as exc:
            self.show_error("Trecho inválido", str(exc))
            return
        default_folder = Path(self.settings.value("export_folder", str(self.folder or default_library_dir())))
        default_name = f"{Path(self.t(self.display_clip_name())).stem}{('-copy' if whole else '-selection') if self.i18n.language == 'en' else ('-copia' if whole else '-trecho')}.wav"
        filters = "WAV 24 bits (*.wav);;OGG Vorbis (*.ogg);;FLAC 24 bits (*.flac);;MP3 (*.mp3)"
        destination, selected_filter = QFileDialog.getSaveFileName(self, self.t("Salvar áudio como" if whole else "Salvar trecho como"), str(default_folder / default_name), filters, options=QFileDialog.Option.DontUseNativeDialog)
        if not destination:
            return
        path = Path(destination)
        if not path.suffix:
            suffix = {"WAV": ".wav", "OGG": ".ogg", "FLAC": ".flac", "MP3": ".mp3"}[selected_filter.split()[0]]
            path = path.with_suffix(suffix)
            if path.exists() and QMessageBox.question(self, self.t("Substituir arquivo?"), self.t('{0} já existe. Deseja substituir?', path.name), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
        self.exporting = True
        self.export_button.setEnabled(False)
        self.export_all_button.setEnabled(False)
        self.ui(self.statusBar(), 'showMessage', 'Salvando {0}…', path.name)
        self.submit(uuid.uuid4().hex, lambda: export_audio(clip, path), self.on_exported)

    @Slot(object, object, str)
    def on_exported(self, token, result, error):
        self.exporting = False
        self.set_audio_enabled(bool(self.clip))
        if error:
            self.show_error("Erro ao salvar áudio", error)
        else:
            self.settings.setValue("export_folder", str(result.parent))
            self.settings.sync()
            self.ui(self.statusBar(), 'showMessage', 'Salvo: {0}', result)
            if result.parent == self.folder:
                self.refresh_folder()
            else:
                self.record_created_files([result])

    def reveal_source(self):
        if self.clip and self.clip.source:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.clip.source.parent)))

    def show_error(self, title, message):
        message = self.i18n.error_message(message)
        self.ui(self.statusBar(), 'showMessage', message)
        QMessageBox.warning(self, self.t(title), self.t(message))

    def closeEvent(self, event):
        QApplication.instance().removeEventFilter(self)
        QApplication.instance().removeTranslator(self.qt_translator)
        self.folder_scan_cancel.set()
        self.folder_scan_token = None
        self.folder_filter_timer.stop()
        self.persist()
        self.player.stop()
        self.player.setSource(QUrl())
        self.load_token = None
        self.selection_token = None
        self.edit_token = None
        self.pool.waitForDone()
        self.temporary.cleanup()
        event.accept()


def main():
    parser = argparse.ArgumentParser(description="Sound Manager: biblioteca local de sons")
    parser.add_argument("--library", type=Path, help="Pasta base para abrir")
    parser.add_argument("--settings", type=Path, help="Arquivo de preferências alternativo")
    parser.add_argument("--self-test", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Sound Manager")
    app.setOrganizationName("SoundManager")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE)
    if args.self_test:
        from bundle_smoke import run
        return run(app, args.self_test)
    window = SoundManager(settings_path=args.settings, prompt=not args.library)
    if args.library:
        if not args.library.is_dir():
            parser.error("A pasta da biblioteca não existe.")
        window.set_base(args.library)
    window.show()
    return app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        details = traceback.format_exc()
        log = state_dir() / "startup-error.log"
        try:
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(details, encoding="utf-8")
            record = f"Registro: {log}"
        except OSError:
            record = "Não foi possível gravar o registro de erro."
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "Sound Manager — erro ao iniciar", f"Não foi possível iniciar o app.\n\n{details}\n\n{record}")
        sys.exit(1)
