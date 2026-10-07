"""Validate live translation, unchanged editing state and language persistence."""
from pathlib import Path
import json
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import soundfile as sf
from PySide6.QtCore import QSettings, Qt
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QDialogButtonBox
from app import SoundManager, STYLE
from file_browser import copy_files


application = QApplication.instance() or QApplication([])
application.setStyleSheet(STYLE)
directory = Path(__file__).resolve().parents[1] / ".state" / "validation-languages"
directory.mkdir(parents=True, exist_ok=True)
library = directory / "Biblioteca"
library.mkdir(exist_ok=True)
source = library / "Nome.wav"
sf.write(str(source), np.column_stack((np.sin(np.arange(96000) * .03) * .2,
                                     np.cos(np.arange(96000) * .04) * .3)), 48000, subtype="FLOAT")
settings = directory / "settings.ini"
settings.unlink(missing_ok=True)
errors, checks = [], []
window = SoundManager(settings, prompt=False)


def wait(predicate):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        application.processEvents()
        if errors:
            raise AssertionError(errors)
        if predicate():
            return
        QTest.qWait(15)
    raise AssertionError("Timed out")


def select(language):
    window.language_combo.setCurrentIndex(window.language_combo.findData(language))
    application.processEvents()


try:
    window.show_error = lambda title, message: errors.append((title, message))
    window.output.setMuted(True)
    window.set_base(library)
    window.show()
    window.toggle_editor(source)
    wait(lambda: window.clip is not None and window.load_token is None)
    assert window.i18n.language == "pt_BR"
    assert window.export_all_button.text() == "Salvar áudio"
    assert window.language_combo.currentData() == "pt_BR"
    assert window.qt_translator.translate("QPlatformTheme", "&Yes") == "&Sim"
    checks.append("Portuguese default and Qt dialog translation")

    window.set_selection(.25, 1.75)
    window.apply_effect("reverse")
    wait(lambda: window.edit_token is None)
    window.copy_selection()
    window.seek(.75)
    window.waveform.zoom(2)
    clip, copied = window.clip, window.copied_clip
    history = (list(window.undo_stack), list(window.redo_stack))
    selection = window.waveform.selection
    view = (window.waveform.view_start, window.waveform.view_length)
    select("en")
    assert window.export_all_button.text() == "Save audio"
    assert window.export_button.text() == "Save selection…"
    assert window.search.placeholderText() == "Filter files by name…"
    assert window.files.headerItem().text(0) == "Listen / edit"
    assert window.files.headerItem().toolTip(1).startswith("1 audio file(s)")
    assert window.row_for_path(source).toolTip(0).startswith("▶ play / pause")
    assert window.folder_label.text() == "Biblioteca"
    assert window.name_label.text() == "Nome.wav · modified"
    assert "2 channels" in window.info_label.text()
    assert window.selection_label.text() == "Selection: 1.5000 s"
    assert window.clipboard_label.text() == "Clipboard: 1.5000 s"
    assert window.copy_button.accessibleName().startswith("Copy the selection")
    assert window.waveform.toolTip().startswith("Drag to select audio")
    assert window.playback_bar.accessibleName() == "Playback position"
    assert window.clip is clip and window.copied_clip is copied and window.modified
    assert (window.undo_stack, window.redo_stack) == history
    assert window.waveform.selection == selection
    assert (window.waveform.view_start, window.waveform.view_length) == view
    assert abs(window.waveform.cursor - .75) < .001
    assert QSettings(str(settings), QSettings.Format.IniFormat).value("language") == "en"
    checks.append("live English translation preserves edits, history, clipboard, cursor and zoom")

    captured = []
    with patch("app.QMessageBox.question", side_effect=lambda *args: captured.append(args) or QMessageBox.StandardButton.No):
        window.save_current_audio()
    assert captured[0][1] == "Save audio?"
    assert str(source.resolve()) in captured[0][2] and "entire audio" in captured[0][2]
    assert window.modified
    # Exercise the actual Qt standard buttons as well as the app's translated message.
    dialog = QMessageBox(window)
    dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    assert "Yes" in dialog.button(QMessageBox.StandardButton.Yes).text()
    captured.clear()
    with patch("app.QFileDialog.getSaveFileName", side_effect=lambda *args, **kwargs: captured.append((args, kwargs)) or ("", "")):
        window.save_selection()
    assert captured[0][0][1] == "Save selection as"
    assert captured[0][0][2].endswith("Nome-selection.wav")
    checks.append("English save confirmation, standard buttons and export dialog")

    window.play_selection()
    wait(lambda: window.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)
    assert window.play_selection_button.text() == "Pause"
    select("pt_BR")
    assert window.play_selection_button.text() == "Pausa"
    assert window.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
    assert window.waveform.selection == selection
    assert window.name_label.text() == "Nome.wav · alterado"
    assert "2 canais" in window.info_label.text()
    assert window.files.headerItem().text(0) == "Ouvir / editar"
    assert window.copy_button.accessibleName().startswith("Copiar seleção")
    assert window.playback_bar.toolTip().startswith("Clique ou arraste")
    window.stop()
    checks.append("switch back to Portuguese while playing without changing the selection")

    window.search.setText("missing")
    select("en")
    assert window.files.empty_message == "No files match the filter."
    window.search.clear()
    for name, width, height in (("english-desktop.png", 1240, 900), ("english-compact.png", 1000, 650)):
        window.resize(width, height)
        window.files.scrollToItem(window.editor_row)
        QTest.qWait(100)
        assert window.grab().save(str(directory / name))
    select("pt_BR")
    window.resize(1240, 900)
    QTest.qWait(100)
    assert window.grab().save(str(directory / "portuguese-desktop.png"))
    select("en")
    window.close()
    window = SoundManager(settings, prompt=False)
    assert window.language_combo.currentData() == "en"
    assert window.export_all_button.text() == "Save audio"
    assert window.base == library.resolve()
    select("pt_BR")
    window.close()
    window = SoundManager(settings, prompt=False)
    assert window.language_combo.currentData() == "pt_BR"
    assert window.export_all_button.text() == "Salvar áudio"
    checks.append("both languages persist after reopening; translated empty state and screenshots")

    destination = directory / "copies"
    destination.mkdir(exist_ok=True)
    copy_files([source], destination)
    copied_path = copy_files([source], destination, "copy")[0]
    assert "(copy" in copied_path.name and copied_path.read_bytes() == source.read_bytes()
    checks.append("English duplicate filename suffix preserves audio bytes")
    assert not errors
    report = {"passed": True, "checks": checks}
    (directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
finally:
    window.close()
