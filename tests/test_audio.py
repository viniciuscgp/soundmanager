from pathlib import Path
import hashlib
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import soundfile as sf

from audio_engine import AudioClip, load_audio, export_audio, save_audio, write_preview, run_ffmpeg


class AudioTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="sound-manager-test-")
        self.root = Path(self.directory.name)
        self.rate = 48000
        time = np.arange(self.rate, dtype=np.float32) / self.rate
        # Opposite phase makes it possible to detect accidental mono downmixes.
        mono = .5 * np.sin(2 * np.pi * 440 * time)
        self.samples = np.column_stack((mono, -mono)).astype(np.float32)
        self.source = self.root / "som com espaços.wav"
        sf.write(str(self.source), self.samples, self.rate, subtype="FLOAT")
        self.clip = load_audio(self.source)
        self.source_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def tearDown(self):
        self.assertEqual(self.source_hash, hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.directory.cleanup()

    def test_cut_preserves_samples_rate_channels_and_independence(self):
        excerpt = self.clip.cut(.125, .375)
        np.testing.assert_array_equal(excerpt.samples, self.samples[6000:18000])
        self.assertEqual((excerpt.sample_rate, excerpt.channels, excerpt.duration), (48000, 2, .25))
        excerpt.samples[0] = 0
        np.testing.assert_array_equal(self.clip.samples, self.samples)

    def test_invalid_selection_is_rejected(self):
        for start, end in [(0, 0), (.5, .25), (-1, .5), (0, 2), (float("nan"), 1), (0, float("inf")), (0, .000001)]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                self.clip.cut(start, end)

    def test_wave_and_flac_round_trip_are_sample_accurate(self):
        cut = self.clip.cut(.1, .4)
        for extension in ("wav", "flac"):
            with self.subTest(format=extension):
                exported = export_audio(cut, self.root / f"export.{extension}")
                reopened = load_audio(exported)
                self.assertEqual(reopened.samples.shape, cut.samples.shape)
                self.assertEqual(reopened.sample_rate, self.rate)
                np.testing.assert_allclose(reopened.samples, cut.samples, atol=2e-7)

    def test_ogg_and_mp3_export_reopen_with_channels_and_duration(self):
        cut = self.clip.cut(.1, .8)
        for extension in ("ogg", "mp3"):
            with self.subTest(format=extension):
                exported = export_audio(cut, self.root / f"export.{extension}")
                reopened = load_audio(exported)
                self.assertEqual(reopened.channels, 2)
                self.assertAlmostEqual(reopened.duration, cut.duration, delta=.06)
                self.assertGreater(np.max(np.abs(reopened.samples)), .1)

    def test_source_and_hard_link_cannot_be_overwritten(self):
        cut = self.clip.cut(.1, .3)
        with self.assertRaisesRegex(ValueError, "original"):
            export_audio(cut, self.source)
        linked = self.root / "hardlink.wav"
        linked.hardlink_to(self.source)
        with self.assertRaisesRegex(ValueError, "original"):
            export_audio(cut, linked)

    def test_existing_destination_is_replaced_and_no_temporary_remains(self):
        target = self.root / "destino.wav"
        target.write_bytes(b"old")
        export_audio(self.clip.cut(.2, .4), target)
        self.assertAlmostEqual(sf.info(str(target)).duration, .2)
        self.assertFalse(list(self.root.glob(".sound-manager-*")))

    def test_failed_export_is_atomic(self):
        from unittest.mock import patch
        target = self.root / "destino.wav"
        target.write_bytes(b"keep")
        with patch("audio_engine.sf.write", side_effect=RuntimeError("simulated disk error")):
            with self.assertRaises(RuntimeError):
                export_audio(self.clip, target)
        self.assertEqual(target.read_bytes(), b"keep")
        self.assertFalse(list(self.root.glob(".sound-manager-*")))

    def test_fallback_decodes_aac_without_touching_source(self):
        from audio_engine import run_ffmpeg
        aac = self.root / "som.m4a"
        run_ffmpeg(["-y", "-i", str(self.source), "-c:a", "aac", str(aac)])
        original = aac.read_bytes()
        decoded = load_audio(aac)
        self.assertEqual(decoded.channels, 2)
        self.assertAlmostEqual(decoded.duration, 1, delta=.05)
        self.assertEqual(original, aac.read_bytes())

    def test_corrupted_audio_reports_error(self):
        bad = self.root / "corrompido.ogg"
        bad.write_bytes(b"not audio")
        with self.assertRaises(ValueError):
            load_audio(bad)

    def test_preview_keeps_channel_count(self):
        preview = self.root / "preview.wav"
        write_preview(self.clip, preview)
        info = sf.info(str(preview))
        self.assertEqual((info.channels, info.samplerate, info.frames), (2, 48000, 48000))


class AudioSaveTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="sound-manager-save-test-")
        self.root = Path(self.directory.name)
        self.rate = 48000
        t = np.arange(self.rate, dtype=np.float32) / self.rate
        self.samples = np.column_stack((.2 * np.sin(2 * np.pi * 440 * t),
                                        .3 * np.cos(2 * np.pi * 660 * t)))
        self.source = self.root / "original.wav"
        sf.write(str(self.source), self.samples, self.rate, subtype="FLOAT")

    def tearDown(self):
        self.directory.cleanup()

    def test_save_replaces_source_with_entire_edited_document_and_preserves_encoding(self):
        clip = load_audio(self.source)
        clip.samples = clip.samples[:24000] * .5
        self.assertEqual(save_audio(clip), self.source)
        reopened = load_audio(self.source)
        np.testing.assert_array_equal(reopened.samples, clip.samples)
        self.assertEqual((reopened.sample_rate, reopened.channels), (48000, 2))
        self.assertEqual(sf.info(str(self.source)).subtype, "FLOAT")
        self.assertFalse(list(self.root.glob(".sound-manager-*")))

    def test_failed_save_keeps_source_intact(self):
        from unittest.mock import patch
        original = self.source.read_bytes()
        with patch("audio_engine.sf.write", side_effect=RuntimeError("disk error")):
            with self.assertRaises(RuntimeError):
                save_audio(load_audio(self.source))
        self.assertEqual(self.source.read_bytes(), original)
        self.assertFalse(list(self.root.glob(".sound-manager-*")))

    def test_copied_selection_and_empty_document_cannot_replace_source(self):
        clip = load_audio(self.source)
        original = self.source.read_bytes()
        with self.assertRaises(ValueError):
            save_audio(clip.cut(.1, .3))
        clip.samples = clip.samples[:0]
        with self.assertRaises(ValueError):
            save_audio(clip)
        self.assertEqual(self.source.read_bytes(), original)

    def test_save_keeps_each_supported_source_extension(self):
        formats = {".ogg": ["-c:a", "libvorbis"], ".mp3": ["-c:a", "libmp3lame"],
                   ".m4a": ["-c:a", "aac"], ".aac": ["-c:a", "aac"],
                   ".opus": ["-c:a", "libopus"], ".wma": ["-c:a", "wmav2"],
                   ".flac": ["-c:a", "flac"], ".aif": ["-c:a", "pcm_s16be"],
                   ".aiff": ["-c:a", "pcm_s16be"]}
        for suffix, codec in formats.items():
            with self.subTest(suffix=suffix):
                source = self.root / f"source{suffix}"
                run_ffmpeg(["-y", "-i", str(self.source), *codec, str(source)])
                clip = load_audio(source)
                clip.samples = clip.samples[:24000] * .5
                self.assertEqual(save_audio(clip), source)
                reopened = load_audio(source)
                self.assertEqual(reopened.channels, 2)
                self.assertAlmostEqual(reopened.duration, .5, delta=.1)
                self.assertGreater(np.max(np.abs(reopened.samples)), .04)
        self.assertFalse(list(self.root.glob(".sound-manager-*")))


if __name__ == "__main__":
    unittest.main()
