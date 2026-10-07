"""Exercise the actual frozen app against synthetic audio in an isolated folder."""
from pathlib import Path
import json
import sys
import time
import traceback
from unittest.mock import patch

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox

from app_paths import APP_DIR, state_dir
from audio_engine import load_audio, run_ffmpeg


def run(application, directory: Path) -> int:
    from app import SoundManager
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    frozen = bool(getattr(sys, "frozen", False))
    checks, errors = [], []
    report = {"passed": False, "frozen": frozen, "checks": checks}
    window = None

    def wait(predicate, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            application.processEvents()
            if errors:
                raise AssertionError(errors)
            if predicate():
                return
            QTest.qWait(15)
        raise AssertionError("Tempo esgotado durante o diagnóstico do pacote.")

    try:
        assert (APP_DIR / "assets" / "sound-manager.ico").is_file()
        assert (APP_DIR / "assets" / "sound-manager.png").is_file()
        checks.append("packaged icons")
        ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve()
        assert ffmpeg.is_file()
        if frozen:
            assert ffmpeg.is_relative_to(APP_DIR), "FFmpeg must come from the bundle"
            assert not state_dir().is_relative_to(APP_DIR), "Settings must survive onefile extraction cleanup"
        checks.extend(["bundled FFmpeg", "persistent user settings path"])
        report.update(ffmpeg=str(ffmpeg), settings_directory=str(state_dir()))

        rate = 48000
        t = np.arange(rate * 3, dtype=np.float32) / rate
        samples = np.column_stack((.2 * np.sin(2 * np.pi * 440 * t),
                                   .3 * np.cos(2 * np.pi * 660 * t)))
        library = directory / "synthetic-library"
        library.mkdir(exist_ok=True)
        source = library / "Teste estéreo.wav"
        sf.write(str(source), samples, rate, subtype="FLOAT")
        aac = library / "Teste conversão.m4a"
        run_ffmpeg(["-y", "-i", str(source), "-c:a", "aac", str(aac)])
        assert load_audio(aac).channels == 2
        checks.append("FFmpeg conversion and AAC decode")

        settings = directory / "settings.ini"
        settings.unlink(missing_ok=True)
        window = SoundManager(settings, prompt=False)
        window.show_error = lambda title, message: errors.append((title, message))
        window.output.setMuted(True)
        window.set_base(library)
        window.show()
        window.toggle_editor(source)
        wait(lambda: window.load_token is None and window.clip is not None)
        assert window.clip.channels == 2 and not window.windowIcon().isNull()
        checks.append("window, icon and waveform load")
        window.set_selection(.25, 2.75)
        window.files.setFocus()
        QTest.keyClick(window.files, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        assert window.waveform.selection == (0, 3)
        checks.append("Ctrl+A audio selection")
        window.set_selection(.25, 2.75)
        QTest.mouseClick(window.play_selection_button, Qt.MouseButton.LeftButton)
        wait(lambda: window.player.position() > 100)
        assert window.play_selection_button.text() == "Pausa"
        QTest.mouseClick(window.play_selection_button, Qt.MouseButton.LeftButton)
        assert window.player.playbackState() == QMediaPlayer.PlaybackState.PausedState
        paused = window.player.position()
        QTest.qWait(100)
        assert window.player.position() == paused and window.play_selection_button.text() == "Play"
        QTest.mouseClick(window.play_selection_button, Qt.MouseButton.LeftButton)
        wait(lambda: window.player.position() > paused + 100)
        window.stop()
        checks.append("Qt multimedia playback, pause and resume")

        window.apply_effect("gain", -6)
        wait(lambda: window.edit_token is None)
        edited = window.clip.samples.copy()
        assert window.modified
        for suffix, name in ((".wav", "WAV"), (".flac", "FLAC"), (".ogg", "OGG"), (".mp3", "MP3")):
            destination = directory / f"export{suffix}"
            with patch("app.QFileDialog.getSaveFileName", return_value=(str(destination), name)):
                window.save_selection(whole=True)
            wait(lambda: not window.exporting)
            assert load_audio(destination).channels == 2
        checks.append("edited WAV FLAC OGG MP3 export")
        with patch("app.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
                patch("app.QFileDialog.getSaveFileName", side_effect=AssertionError("Unexpected export dialog")):
            window.save_current_audio()
        wait(lambda: not window.exporting)
        assert not window.modified
        np.testing.assert_array_equal(load_audio(source).samples, edited)
        checks.append("confirmed current document save")
        window.seek(1.2)
        window.resize(1100, 760)
        window.files.verticalScrollBar().setValue(window.files.verticalScrollBar().maximum())
        QTest.qWait(100)
        assert window.grab().save(str(directory / "window.png"))
        checks.append("rendered UI screenshot")
        window.volume.setValue(37)
        window.persist()
        window.close()
        window = SoundManager(settings, prompt=False)
        assert window.base == library and window.volume.value() == 37
        checks.append("preferences survive restart")
        report["passed"] = True
    except Exception:
        report["error"] = traceback.format_exc()
    finally:
        if window is not None:
            window.close()
        (directory / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if report["passed"] else 1
