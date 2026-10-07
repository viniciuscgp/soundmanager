"""Validate editor actions, playback, selection, exports and confirmed fixture saves."""
from pathlib import Path
import hashlib
import json
import sys
import time
from threading import Event
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import soundfile as sf
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtMultimedia import QMediaPlayer
from app import SoundManager, STYLE
from audio_engine import edit_selection, load_audio, save_audio

app = QApplication([])
app.setStyleSheet(STYLE)
directory = ROOT / ".state" / "validation-editor"
directory.mkdir(parents=True, exist_ok=True)
rate = 48000
t = np.arange(rate * 2, dtype=np.float32) / rate
samples = np.column_stack((.2 * np.sin(2 * np.pi * 230 * t), .3 * np.cos(2 * np.pi * 330 * t)))
source = directory / "Som A stereo.wav"
target = directory / "Som B mono.wav"
sf.write(str(source), samples, rate, subtype="FLOAT")
mono = np.full((44100, 1), .1, dtype=np.float32)
sf.write(str(target), mono, 44100, subtype="FLOAT")
hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (source, target)}
settings = directory / "settings.ini"
settings.unlink(missing_ok=True)
window = SoundManager(settings, prompt=False)
errors = []
window.show_error = lambda title, detail: errors.append((title, detail))
window.show()
window.activateWindow()
window.output.setMuted(True)


def wait(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError(f"Timeout; errors={errors}; status={window.statusBar().currentMessage()}")


def open_editor(path):
    if window.editor_path != path.resolve():
        window.toggle_editor(path)
    else:
        window.open_audio(path)
    wait(lambda: window.load_token is None and window.edit_token is None and window.clip is not None)
    assert window.clip.source == path.resolve()


def action(button):
    window.files.verticalScrollBar().setValue(window.files.verticalScrollBar().maximum())
    app.processEvents()
    button.setFocus()
    assert button.isEnabled(), button.text()
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    assert window.edit_token is not None, button.text()
    wait(lambda: window.edit_token is None)
    assert not errors, errors


try:
    window.set_base(directory)
    open_editor(source)
    original = window.clip.samples.copy()
    window.set_selection(.25, .75)
    assert window.play_selection_button.text() == "Play"
    # Ctrl+A belongs to the open audio editor even if its containing list has focus.
    selected_files = window.files.selectedItems()
    for control in (window.files, window.play_selection_button, window.waveform, window.playback_bar):
        window.set_selection(.25, .75)
        control.setFocus()
        QTest.keyClick(control, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        assert window.waveform.selection == (0, window.clip.duration)
        assert window.files.selectedItems() == selected_files
    window.search.setText("Som")
    window.search.setFocus()
    QTest.keyClick(window.search, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    assert window.search.selectedText() == "Som"
    window.search.clear()

    # Real media backend: one button plays, pauses, and resumes without restarting.
    window.set_selection(.25, 1.75)
    QTest.mouseClick(window.play_selection_button, Qt.MouseButton.LeftButton)
    wait(lambda: window.player.position() > 120)
    assert window.play_selection_button.text() == "Pausa"
    preview = window.selection_preview
    QTest.mouseClick(window.play_selection_button, Qt.MouseButton.LeftButton)
    assert window.player.playbackState() == QMediaPlayer.PlaybackState.PausedState
    assert window.play_selection_button.text() == "Play"
    paused_position = window.player.position()
    QTest.qWait(100)
    assert window.player.position() == paused_position
    assert window.waveform.cursor > .25
    window.grab().save(str(directory / "editor-playhead-paused.png"))
    QTest.mouseClick(window.play_selection_button, Qt.MouseButton.LeftButton)
    wait(lambda: window.player.position() > paused_position + 100)
    assert window.selection_preview == preview and window.play_selection_button.text() == "Pausa"
    wait(lambda: window.player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia)
    assert window.play_selection_button.text() == "Play"
    window.stop()
    assert window.play_selection_button.text() == "Play"
    window.set_selection(.25, .75)
    for button in (window.remove_button, window.undo_button, window.redo_button):
        assert not button.text() and not button.icon().isNull() and button.toolTip()
        assert button.geometry().center().y() == window.play_selection_button.geometry().center().y()

    # A click or selection-handle drag in the waveform cannot reposition playback.
    window.seek(.9)
    QTest.qWait(40)
    window.seek(.9)
    cursor_before = window.waveform.cursor
    point = QPoint(round(window.waveform.x_at(.5)), round(window.waveform.plot_rect().center().y()))
    QTest.mouseClick(window.waveform, Qt.MouseButton.LeftButton, pos=point)
    assert window.waveform.cursor == cursor_before and window.waveform.selection == (.25, .75)
    start = QPoint(round(window.waveform.x_at(.25)), point.y())
    end = QPoint(round(window.waveform.x_at(.3)), point.y())
    QTest.mousePress(window.waveform, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(window.waveform, end, delay=10)
    QTest.mouseRelease(window.waveform, Qt.MouseButton.LeftButton, pos=end)
    assert abs(window.waveform.selection[0] - .3) < .003
    assert window.waveform.cursor == cursor_before
    window.set_selection(.25, .75)

    # The lower bar seeks independently, including dragging and keyboard positioning.
    selection_before = window.waveform.selection
    start = QPoint(round(window.playback_bar.x_at(.1)), window.playback_bar.height() // 2)
    end = QPoint(round(window.playback_bar.x_at(.4)), start.y())
    QTest.mousePress(window.playback_bar, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(window.playback_bar, end, delay=10)
    QTest.mouseRelease(window.playback_bar, Qt.MouseButton.LeftButton, pos=end)
    assert abs(window.waveform.cursor - .4) < .003
    assert window.waveform.selection == selection_before
    QTest.keyClick(window.playback_bar, Qt.Key.Key_End)
    assert window.waveform.cursor == 2
    QTest.keyClick(window.playback_bar, Qt.Key.Key_Home)
    assert window.waveform.cursor == 0
    window.waveform.zoom(2)
    QTest.mouseClick(window.playback_bar, Qt.MouseButton.LeftButton, pos=end)
    assert abs(window.waveform.cursor - .4) < .003, "The playback bar must cover the full document even when the waveform is zoomed."
    assert window.waveform.selection == selection_before
    window.waveform.show_all()
    window.seek(0)
    window.gain_step.setValue(6)
    action(window.volume_up_button)
    boosted = window.clip.samples.copy()
    np.testing.assert_allclose(boosted[12000:36000], original[12000:36000] * 10 ** .3, rtol=1e-6)
    np.testing.assert_array_equal(boosted[:12000], original[:12000])
    np.testing.assert_array_equal(boosted[36000:], original[36000:])
    assert window.modified and window.undo_button.isEnabled()
    preview, _ = sf.read(str(window.preview_path), dtype="float32", always_2d=True)
    np.testing.assert_allclose(preview, boosted, atol=4e-5)
    action(window.undo_button)
    np.testing.assert_array_equal(window.clip.samples, original)
    assert not window.modified and window.redo_button.isEnabled()
    action(window.redo_button)
    np.testing.assert_array_equal(window.clip.samples, boosted)
    action(window.volume_down_button)
    np.testing.assert_allclose(window.clip.samples, original, atol=1e-7)
    before_reverse = window.clip.samples.copy()
    action(window.reverse_button)
    np.testing.assert_array_equal(window.clip.samples[12000:36000], before_reverse[12000:36000][::-1])

    window.fade_duration.setValue(.1)
    action(window.fade_in_button)
    np.testing.assert_array_equal(window.clip.samples[12000], [0, 0])
    action(window.fade_out_button)
    np.testing.assert_array_equal(window.clip.samples[35999], [0, 0])
    edited_a = window.clip.samples.copy()
    window.copy_button.setFocus()
    QTest.mouseClick(window.copy_button, Qt.MouseButton.LeftButton)
    copied = window.copied_clip.samples.copy()
    assert copied.shape == (24000, 2) and window.paste_button.isEnabled()

    # Cross-file paste after a real click on the separate playback position bar.
    open_editor(target)
    assert window.copied_clip.samples.shape == copied.shape
    assert not window.undo_button.isEnabled()
    window.files.scrollToItem(window.editor_row)
    app.processEvents()
    selection_before_seek = window.waveform.selection
    point = QPoint(round(window.playback_bar.x_at(.4)), window.playback_bar.height() // 2)
    QTest.mouseClick(window.playback_bar, Qt.MouseButton.LeftButton, pos=point)
    assert window.waveform.selection == selection_before_seek
    insertion = round(window.waveform.cursor * 44100)
    assert abs(window.waveform.cursor - .4) < .003
    action(window.paste_button)
    pasted = window.clip.samples.copy()
    assert pasted.shape == (66150, 1)
    np.testing.assert_array_equal(pasted[:insertion], mono[:insertion])
    np.testing.assert_array_equal(pasted[insertion + 22050:], mono[insertion:])
    assert abs(window.waveform.selection[0] - insertion / 44100) < 1e-8
    assert abs(window.waveform.selection[1] - window.waveform.selection[0] - .5) < 1e-8
    np.testing.assert_array_equal(window.copied_clip.samples, copied)
    action(window.undo_button)
    np.testing.assert_array_equal(window.clip.samples, mono)
    action(window.redo_button)
    np.testing.assert_array_equal(window.clip.samples, pasted)

    # Ctrl+V inserts into the current document; Ctrl+Z restores the previous edit.
    window.files.setFocus()
    QTest.keyClick(window.files, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
    wait(lambda: window.edit_token is None and window.clip.duration == 2)
    QTest.keyClick(window.files, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    wait(lambda: window.edit_token is None and window.clip.duration == 1.5)
    np.testing.assert_array_equal(window.clip.samples, pasted)
    action(window.reverse_button)
    assert not window.redo_button.isEnabled(), "A new change must clear redo history."
    edited_b = window.clip.samples.copy()

    # Reopening a file restores its edits and history, rather than decoding the original again.
    open_editor(source)
    np.testing.assert_array_equal(window.clip.samples, edited_a)
    assert window.undo_button.isEnabled() and window.modified
    open_editor(target)
    np.testing.assert_array_equal(window.clip.samples, edited_b)
    assert window.undo_button.isEnabled() and window.modified
    exported = directory / "Resultado editado.flac"
    with patch("app.QFileDialog.getSaveFileName", return_value=(str(exported), "FLAC 24 bits (*.flac)")):
        window.save_selection(whole=True)
    wait(lambda: not window.exporting)
    np.testing.assert_allclose(load_audio(exported).samples, edited_b, atol=2e-7)

    # Switch files while a worker is running, then return before it completes.
    open_editor(source)
    selection = window.waveform.selection
    started, release = Event(), Event()
    def delayed(*args):
        started.set()
        assert release.wait(3)
        return edit_selection(*args)
    with patch("app.edit_selection", side_effect=delayed):
        window.apply_effect("reverse")
        wait(started.is_set)
        open_editor(target)
        window.toggle_editor(source)
        assert window.edit_token is not None and window.clip is None
        release.set()
        wait(lambda: window.edit_token is None and window.clip is not None)
    expected_a = load_audio(source)
    expected_a.samples[:] = edited_a
    first, last = window.clip.selection_frames(*selection)
    expected_a.samples[first:last] = edited_a[first:last][::-1]
    np.testing.assert_array_equal(window.clip.samples, expected_a.samples)
    assert window.clip.source == source.resolve()

    # Failed operations must keep the current document and history usable.
    before_failure = window.clip.samples.copy()
    history_count = len(window.undo_stack)
    with patch("app.edit_selection", side_effect=ValueError("simulated editing failure")):
        window.apply_effect("gain", 3)
        wait(lambda: window.edit_token is None)
    assert len(errors) == 1
    errors.clear()
    np.testing.assert_array_equal(window.clip.samples, before_failure)
    assert len(window.undo_stack) == history_count and window.volume_up_button.isEnabled()

    # Removal joins the exact remaining frames, collapses the selection at the join,
    # updates the inline duration and participates in the same undo/redo history.
    window.set_selection(.25, .75)
    before_remove = window.clip.samples.copy()
    action(window.remove_button)
    removed = np.concatenate((before_remove[:12000], before_remove[36000:]))
    np.testing.assert_array_equal(window.clip.samples, removed)
    assert window.clip.duration == 1.5
    assert sf.info(str(window.preview_path)).frames == 72000
    np.testing.assert_array_equal(window.copied_clip.samples, copied)
    assert window.waveform.selection == (.25, .25)
    assert abs(window.waveform.cursor - .25) < .002
    assert not window.remove_button.isEnabled() and not window.copy_button.isEnabled()
    assert "00:01.500" in window.position_label.text()
    assert window.transport_row is window.row_for_path(source)
    assert window.files.itemWidget(window.transport_row, 3) is window.transport_host
    assert window.files.viewport().isAncestorOf(window.transport)
    assert not hasattr(window, "now_playing_label") and not hasattr(window, "count_label")
    action(window.undo_button)
    np.testing.assert_array_equal(window.clip.samples, before_remove)
    assert window.waveform.selection == (.25, .75)
    action(window.redo_button)
    np.testing.assert_array_equal(window.clip.samples, removed)
    open_editor(target)
    assert window.transport_row is window.row_for_path(target)
    open_editor(source)
    np.testing.assert_array_equal(window.clip.samples, removed)

    # Full removal stays editable: an empty document supports undo and paste.
    window.select_all()
    action(window.remove_button)
    assert window.clip.samples.shape == (0, 2) and window.clip.duration == 0
    assert not window.stop_button.isEnabled() and not window.export_all_button.isEnabled()
    assert window.undo_button.isEnabled() and window.paste_button.isEnabled()
    window.waveform.zoom(2)
    window.waveform.show_all()
    window.grab().save(str(directory / "editor-empty.png"))
    action(window.undo_button)
    np.testing.assert_array_equal(window.clip.samples, removed)
    action(window.redo_button)
    assert window.clip.duration == 0
    action(window.paste_button)
    np.testing.assert_array_equal(window.clip.samples, copied)
    action(window.undo_button)
    assert window.clip.duration == 0
    action(window.undo_button)
    np.testing.assert_array_equal(window.clip.samples, removed)
    window.set_selection(.2, .7)

    # Refreshing and clearing the list must keep the shared transport alive.
    window.refresh_folder()
    wait(lambda: window.load_token is None)
    assert window.transport_row is window.row_for_path(source)
    assert window.transport.isVisible()
    window.close_editor()
    assert window.transport.isVisible(), "Playback controls must work with the waveform collapsed."
    window.files.scrollToItem(window.row_for_path(source))
    app.processEvents()
    rect = window.files.visualItemRect(window.row_for_path(source))
    QTest.mouseClick(window.files.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(25, rect.center().y()))
    wait(lambda: window.player.position() > 80)
    assert not window.editor.isVisible()
    assert "00:01.500" in window.position_label.text()
    QTest.mouseClick(window.stop_button, Qt.MouseButton.LeftButton)
    wait(lambda: window.player.position() == 0)
    shortened_export = directory / "Remocao resultado.wav"
    with patch("app.QFileDialog.getSaveFileName", return_value=(str(shortened_export), "WAV 24 bits (*.wav)")):
        window.save_selection(whole=True)
    wait(lambda: not window.exporting)
    np.testing.assert_allclose(load_audio(shortened_export).samples, removed, atol=2e-7)
    window.toggle_editor(source)

    window.resize(1240, 900)
    window.files.scrollToItem(window.editor_row)
    QTest.qWait(60)
    assert window.editor.layout().minimumSize().width() <= window.editor.width()
    window.grab().save(str(directory / "editor-effects.png"))
    window.resize(1100, 700)
    QTest.qWait(60)
    window.files.verticalScrollBar().setValue(window.files.verticalScrollBar().maximum())
    QTest.qWait(60)
    assert window.editor.layout().minimumSize().width() <= window.editor.width()
    assert window.files.viewport().rect().contains(window.export_button.mapTo(window.files.viewport(), window.export_button.rect().center())), "Compact layout must allow scrolling to the editor controls."
    window.grab().save(str(directory / "editor-effects-compact.png"))
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in hashes.items())

    # Only synthetic fixtures are overwritten, never the real sound library.
    export_folder = directory / "Exportacoes separadas"
    window.settings.setValue("export_folder", str(export_folder))
    original_bytes = source.read_bytes()
    with patch("app.QFileDialog.getSaveFileName", side_effect=AssertionError("Save must not ask for a destination")), \
            patch("app.QMessageBox.question", return_value=QMessageBox.StandardButton.No) as confirmation:
        QTest.mouseClick(window.export_all_button, Qt.MouseButton.LeftButton)
        assert confirmation.call_count == 1
        assert str(source.resolve()) in confirmation.call_args.args[2]
    assert not window.exporting and source.read_bytes() == original_bytes
    assert window.modified

    # A failed save leaves the disk and edited document unchanged.
    with patch("app.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
            patch("app.save_audio", side_effect=RuntimeError("simulated save failure")):
        window.save_current_audio()
        wait(lambda: not window.exporting)
    assert len(errors) == 1 and window.modified and source.read_bytes() == original_bytes
    errors.clear()

    # Saving a snapshot while switching files must mark only that snapshot clean.
    saving_clip = window.clip
    started, release = Event(), Event()
    def delayed_save(clip):
        started.set()
        assert release.wait(3)
        return save_audio(clip)
    with patch("app.QFileDialog.getSaveFileName", side_effect=AssertionError("Unexpected export dialog")), \
            patch("app.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
            patch("app.save_audio", side_effect=delayed_save):
        QTest.mouseClick(window.export_all_button, Qt.MouseButton.LeftButton)
        wait(started.is_set)
        open_editor(target)
        assert window.modified
        release.set()
        wait(lambda: not window.exporting)
    assert window.modified and window.clip.source == target.resolve()
    assert window.settings.value("export_folder") == str(export_folder)
    assert target.read_bytes() and hashlib.sha256(target.read_bytes()).hexdigest() == hashes[target]
    np.testing.assert_array_equal(load_audio(source).samples, saving_clip.samples)
    open_editor(source)
    assert not window.modified and "alterado" not in window.name_label.text()
    action(window.undo_button)
    assert window.modified
    action(window.redo_button)
    assert not window.modified

    # With the editor closed, Ctrl+A retains the file browser's normal behavior.
    window.close_editor()
    window.files.setFocus()
    QTest.keyClick(window.files, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    assert len(window.files.selectedItems()) == window.files.topLevelItemCount()
    assert not errors
    report = {"passed": True, "checks": ["selection-only gain", "updated playback preview", "reverse time with stereo preserved", "fade edges and duration", "undo and redo buttons", "temporary audio clipboard", "waveform clicks and handles do not seek", "separate playback bar click drag and keyboard", "full-document seek independent of waveform zoom", "Play label and aligned trash undo redo icons", "playback bar cursor paste", "stereo 48kHz to mono 44.1kHz paste", "existing destination samples preserved", "Ctrl+V and Ctrl+Z", "new edits clear redo", "per-file edit and history retention", "edited FLAC export", "switch files during worker", "failed edit rollback", "remove selection joins remaining frames", "remove undo and redo", "empty document undo and paste", "playback controls in own file row", "no bottom player or count area", "inline transport survives list refresh and editor collapse", "original hashes unchanged", "desktop and compact screenshots"]}
    report["checks"].extend(["Ctrl+A selects audio without selecting files", "text field Ctrl+A unchanged", "Play pause resume and natural end", "visual waveform playhead", "cancel save keeps source", "failed save keeps edits and source", "save overwrites current file without export dialog", "save ignores export folder", "save while switching files", "saved undo redo state", "closed editor Ctrl+A selects files"])
    (directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
finally:
    window.close()
