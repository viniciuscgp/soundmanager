"""Exercise the real UI and media backend without changing normal preferences."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time
import uuid
from unittest.mock import patch

os.environ.setdefault("QT_SCALE_FACTOR", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import soundfile as sf
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaPlayer

from app import SoundManager, STYLE


app = QApplication([])
app.setStyleSheet(STYLE)
directory = ROOT / ".state" / "validation"
directory.mkdir(parents=True, exist_ok=True)
library = directory / "Biblioteca teste"
library.mkdir(exist_ok=True)
subfolder = library / "Subpasta"
subfolder.mkdir(exist_ok=True)
other_folder = library / "Outra pasta"
other_folder.mkdir(exist_ok=True)
nested_folder = subfolder / "Prefixo MeuTexto Sufixo"
nested_folder.mkdir(exist_ok=True)
rate = 48000
t = np.arange(rate * 4, dtype=np.float32) / rate
samples = .2 * np.sin(2 * np.pi * (220 * t + 140 * t * t))
fixture = library / "Som stereo.wav"
sf.write(str(fixture), np.column_stack((samples, -samples)), rate, subtype="FLOAT")
sf.write(str(subfolder / "Outro som.ogg"), samples[:rate], rate)
sf.write(str(other_folder / "Alvo DIRETO.wav"), samples[:rate], rate)
sf.write(str(nested_folder / "Disparo ESPECIAL.ogg"), samples[:rate], rate)
settings = directory / "settings.ini"
settings.unlink(missing_ok=True)
errors = []
window = SoundManager(settings, prompt=False)
window.show_error = lambda title, message: errors.append((title, message))
window.show()
window.output.setMuted(True)


def wait_until(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(20)
    raise AssertionError(f"Timed out. Player: {window.player.errorString()}; errors: {errors}")


try:
    window.set_base(library)
    assert window.files.topLevelItemCount() == 1
    assert not window.editor.isVisible()
    assert window.search.parent() is window.files.parent()
    assert window.folder_search.parent() is window.tree.parent()
    wait_until(lambda: window.folder_model.rowCount(window.tree.rootIndex()) >= 2)
    window.folder_search.setFocus()
    QTest.keyClicks(window.folder_search, "uBpA")
    wait_until(lambda: window.folder_scan_token is None and window.folder_index is not None)
    root = window.tree.rootIndex()
    other_index = window.folder_model.index(str(other_folder))
    sub_index = window.folder_model.index(str(subfolder))
    assert window.tree.isRowHidden(other_index.row(), other_index.parent())
    assert not window.tree.isRowHidden(sub_index.row(), sub_index.parent())
    window.folder_search.setText("tExTo")
    wait_until(lambda: not window.tree.isRowHidden(sub_index.row(), sub_index.parent()))
    nested_index = window.folder_model.index(str(nested_folder))
    wait_until(lambda: not window.tree.isRowHidden(nested_index.row(), nested_index.parent()))
    assert window.tree.isExpanded(sub_index)
    assert window.tree.isRowHidden(other_index.row(), other_index.parent())
    assert window.files.topLevelItemCount() == 1 and not window.files.topLevelItem(0).isHidden()
    window.search.setFocus()
    QTest.keyClicks(window.search, "TERE")
    assert not window.files.topLevelItem(0).isHidden(), "File filter must match text in the middle."
    assert window.folder_search.text() == "tExTo", "Filters must be independent."
    window.folder_search.setText("sem resultado [literal]")
    assert all(window.tree.isRowHidden(row, root) for row in range(window.folder_model.rowCount(root)))
    assert not window.files.topLevelItem(0).isHidden()
    window.folder_search.clear()
    assert not window.tree.isRowHidden(other_index.row(), other_index.parent())
    window.folder_search.setText("iReTo")
    assert not window.tree.isRowHidden(other_index.row(), other_index.parent()), "A file-name match must keep its folder visible."
    assert window.tree.isRowHidden(sub_index.row(), sub_index.parent())
    window.navigate(other_folder)
    assert window.folder_search.text() == "iReTo"
    window.search.setText("DiReTo")
    visible_names = [window.files.topLevelItem(row).text(1) for row in range(window.files.topLevelItemCount()) if not window.files.topLevelItem(row).isHidden()]
    assert visible_names == ["Alvo DIRETO.wav"]
    window.navigate(library)
    window.folder_search.setText("pEcIaL")
    wait_until(lambda: not window.tree.isRowHidden(nested_index.row(), nested_index.parent()))
    assert not window.tree.isRowHidden(sub_index.row(), sub_index.parent()), "Ancestors must remain visible for a nested file match."
    assert window.tree.isRowHidden(other_index.row(), other_index.parent())
    assert not window.files.topLevelItem(0).isHidden(), "Folder search must not also filter files on the right."
    window.search.setText("ESPECIAL")
    assert window.files.topLevelItem(0).isHidden(), "Right-hand search must not include files from subfolders."
    window.search.clear()
    window.folder_search.clear()
    window.search.setText("[literal]")
    assert window.files.topLevelItem(0).isHidden()
    window.search.clear()
    window.search.setText("STEREO")
    assert sum(not window.files.topLevelItem(i).isHidden() for i in range(window.files.topLevelItemCount())) == 1
    window.search.clear()
    window.navigate(subfolder)
    assert window.folder == subfolder.resolve()
    window.go_up()
    assert window.folder == library.resolve()

    # Real click on the inline play cell, going through the painted delegate.
    row = window.files.topLevelItem(0)
    rect = window.files.visualItemRect(row)
    QTest.mouseClick(window.files.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(25, rect.center().y()))
    wait_until(lambda: window.clip is not None)
    wait_until(lambda: window.player.position() > 100)
    assert window.clip.channels == 2
    assert not window.editor.isVisible(), "Playing must not expand the waveform."
    window.toggle_play()
    assert window.player.playbackState() == QMediaPlayer.PlaybackState.PausedState
    window.stop()

    # The recut action expands the editor as a child of this file's own row.
    QTest.mouseClick(window.files.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(80, rect.center().y()))
    app.processEvents()
    assert window.editor.isVisible() and window.editor_row is row
    assert row.childCount() == 1 and row.isExpanded()

    # Selection by dragging on the waveform, rather than calling the handler directly.
    waveform = window.waveform
    y = int(waveform.plot_rect().center().y())
    start_point, end_point = QPoint(round(waveform.x_at(.5)), y), QPoint(round(waveform.x_at(1.5)), y)
    QTest.mousePress(waveform, Qt.MouseButton.LeftButton, pos=start_point)
    QTest.mouseMove(waveform, end_point, delay=30)
    QTest.mouseRelease(waveform, Qt.MouseButton.LeftButton, pos=end_point)
    start, end = waveform.selection
    assert abs(start - .5) < .03 and abs(end - 1.5) < .03, waveform.selection
    window.start_spin.setValue(.5)
    window.end_spin.setValue(1.5)
    assert waveform.selection == (.5, 1.5)
    waveform.zoom(2)
    assert window.wave_scroll.isEnabled()
    window.wave_scroll.setValue(10000)
    assert waveform.view_start > 0
    waveform.show_all()
    assert not window.wave_scroll.isEnabled()

    QTest.mouseClick(window.play_selection_button, Qt.MouseButton.LeftButton)
    wait_until(lambda: window.selection_playback and window.selection_token is None)
    wait_until(lambda: window.player.position() > 100)
    assert sf.info(str(window.selection_preview)).frames == rate
    assert window.waveform.cursor >= .5
    wait_until(lambda: window.player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia)
    window.stop()

    # Copy survives replacing the original editor document.
    window.copy_selection()
    assert window.copied_clip.duration == 1
    assert QApplication.clipboard().mimeData().hasFormat("audio/wav")
    window.open_copied()
    wait_until(lambda: window.load_token is None and window.clip.duration == 1)
    window.set_selection(.1, .6)
    exported = directory / "recorte com espaços.flac"
    with patch("app.QFileDialog.getSaveFileName", return_value=(str(exported), "FLAC 24 bits (*.flac)")):
        window.save_selection()
    wait_until(lambda: not window.exporting)
    assert sf.info(str(exported)).frames == rate // 2
    assert not errors, errors

    # Loading a damaged file reports an error and leaves controls disabled.
    corrupt = directory / "corrompido.wav"
    corrupt.write_bytes(b"not audio")
    window.open_audio(corrupt)
    wait_until(lambda: window.load_token is None)
    assert len(errors) == 1 and not window.stop_button.isEnabled()
    errors.clear()

    # Rapid changes must discard stale results from the previous decode.
    window.open_audio(fixture)
    window.open_audio(subfolder / "Outro som.ogg")
    wait_until(lambda: window.load_token is None and window.clip is not None)
    assert window.clip.source == (subfolder / "Outro som.ogg").resolve()

    # A separate synthetic library keeps this validator independent of local sounds.
    screenshot_library = directory / "Biblioteca captura"
    screenshot_library.mkdir(exist_ok=True)
    for number in range(20):
        (screenshot_library / f"Pasta {number:02d}").mkdir(exist_ok=True)
    real = screenshot_library / "Pasta 00" / "Som demonstração.wav"
    sf.write(str(real), np.column_stack((samples, -samples)), rate, subtype="FLOAT")
    original_hash = hashlib.sha256(real.read_bytes()).hexdigest()
    window.set_base(screenshot_library)
    window.navigate(real.parent)
    window.toggle_editor(real)
    wait_until(lambda: window.load_token is None and window.clip is not None)
    assert window.clip.source == real.resolve()
    window.set_selection(window.clip.duration * .15, window.clip.duration * .65)
    wait_until(lambda: window.folder_model.rowCount(window.tree.rootIndex()) >= 20)
    QTest.qWait(150)
    window.resize(1240, 800)
    app.processEvents()
    assert window.grab().save(str(directory / "sound-manager.png"))
    window.resize(1100, 700)
    app.processEvents()
    assert window.grab().save(str(directory / "sound-manager-compact.png"))
    assert window.export_button.isEnabled()
    assert window.editor.layout().minimumSize().width() <= window.editor.width()
    assert hashlib.sha256(real.read_bytes()).hexdigest() == original_hash

    window.close_editor()
    app.processEvents()
    assert not window.editor.isVisible()
    assert window.grab().save(str(directory / "sound-manager-collapsed.png"))
    window.toggle_editor(real)
    app.processEvents()
    assert window.editor.isVisible(), "The shared editor must survive repeated opening."
    window.close_editor()

    # Native file URLs used by Explorer, followed by real Qt drop events to the folder tree.
    window.set_base(library)
    row = window.files.topLevelItem(0)
    row.setSelected(True)
    mime = window.files.file_mime_data()
    assert Path(mime.urls()[0].toLocalFile()).resolve() == fixture.resolve()
    assert bytes(mime.data('application/x-qt-windows-mime;value="Preferred DropEffect"')) == b"\x01\x00\x00\x00"
    wait_until(lambda: window.folder_model.rowCount(window.tree.rootIndex()) >= 1)
    target_index = window.folder_model.index(str(subfolder))
    window.tree.scrollTo(target_index)
    app.processEvents()
    drop_point = window.tree.visualRect(target_index).center()
    enter = QDragEnterEvent(drop_point, Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(window.tree.viewport(), enter)
    assert enter.isAccepted()
    move = QDragMoveEvent(drop_point, Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(window.tree.viewport(), move)
    assert move.isAccepted()
    drop = QDropEvent(QPointF(drop_point), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(window.tree.viewport(), drop)
    assert drop.isAccepted() and drop.dropAction() == Qt.DropAction.CopyAction
    wait_until(lambda: not window.copy_jobs)
    assert any(path.suffix == ".wav" and path.read_bytes() == fixture.read_bytes() for path in subfolder.iterdir())
    assert fixture.exists()
    assert not errors, errors

    # Copying a new file into a different folder updates an already built search index.
    fresh_name = f"NovoArquivoIndice_{uuid.uuid4().hex}"
    window.folder_search.setText(fresh_name)
    wait_until(lambda: window.folder_index is not None and window.folder_scan_token is None)
    assert window.tree.isRowHidden(other_index.row(), other_index.parent())
    copy_source = directory / f"{fresh_name}.wav"
    sf.write(str(copy_source), samples[:rate], rate)
    window.copy_to_folder([copy_source], other_folder)
    wait_until(lambda: not window.copy_jobs)
    wait_until(lambda: not window.tree.isRowHidden(other_index.row(), other_index.parent()))
    assert (other_folder / copy_source.name).read_bytes() == copy_source.read_bytes()
    window.set_base(screenshot_library)
    window.navigate(real.parent)

    window.volume.setValue(43)
    window.loop.setChecked(True)
    window.move(35, 45)
    window.persist()
    position = window.pos()
    size = window.size()
    window.close()
    restored = SoundManager(settings, prompt=False)
    restored.show()
    app.processEvents()
    assert restored.base == screenshot_library.resolve()
    assert restored.folder == real.parent.resolve()
    assert restored.volume.value() == 43 and restored.loop.isChecked()
    assert restored.size() == size
    assert (restored.pos() - position).manhattanLength() <= 2, (restored.pos(), position)
    restored.close()
    report = {"passed": True, "checks": ["independent folder and file filter boxes", "live substring filtering", "case-insensitive matching", "folder name or contained file match", "nested file matches keep ancestor path", "right filter limited to displayed folder", "new copied files update search index", "literal punctuation", "empty results and clear restore", "files-only right list", "inline play without waveform", "inline collapsible editor", "playback position", "pause and stop", "waveform drag", "numeric selection", "zoom and pan", "sample-accurate selection playback", "audio clipboard", "copied excerpt editor", "GUI export", "corrupt file", "stale load cancellation", "synthetic library read-only", "desktop and compact screenshots", "copy-only Explorer file MIME", "native folder drag and drop", "byte-identical file copy", "preferences restore"], "source_sha256": original_hash}
    (directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
finally:
    if window.isVisible():
        window.close()
