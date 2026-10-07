from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from audio_engine import AudioClip, edit_selection, insert_clip, remove_selection


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.samples = np.arange(40, dtype=np.float32).reshape(20, 2) / 100
        self.clip = AudioClip(self.samples.copy(), 20, Path("original.wav"), "original.wav")

    def assert_unchanged_outside(self, edited):
        np.testing.assert_array_equal(edited.samples[:4], self.samples[:4])
        np.testing.assert_array_equal(edited.samples[14:], self.samples[14:])
        np.testing.assert_array_equal(self.clip.samples, self.samples)
        self.assertEqual((edited.sample_rate, edited.source, edited.name), (20, self.clip.source, self.clip.name))

    def test_gain_applies_only_to_selected_frames_without_clipping(self):
        for gain in (-6, 6, 24):
            with self.subTest(gain=gain):
                result = edit_selection(self.clip, .2, .7, "gain", gain)
                self.assert_unchanged_outside(result)
                np.testing.assert_allclose(result.samples[4:14], self.samples[4:14] * 10 ** (gain / 20), rtol=1e-6)

    def test_reverse_keeps_channels_and_reverses_only_time(self):
        result = edit_selection(self.clip, .2, .7, "reverse")
        self.assert_unchanged_outside(result)
        np.testing.assert_array_equal(result.samples[4:14], self.samples[4:14][::-1])
        restored = edit_selection(result, .2, .7, "reverse")
        np.testing.assert_array_equal(restored.samples, self.samples)

    def test_fades_start_and_end_at_selection_edges(self):
        fade_in = edit_selection(self.clip, .2, .7, "fade_in", .2)
        fade_out = edit_selection(self.clip, .2, .7, "fade_out", .2)
        for result in (fade_in, fade_out):
            self.assert_unchanged_outside(result)
        np.testing.assert_allclose(fade_in.samples[4:8], self.samples[4:8] * np.linspace(0, 1, 4)[:, None], atol=1e-7)
        np.testing.assert_array_equal(fade_in.samples[8:14], self.samples[8:14])
        np.testing.assert_array_equal(fade_out.samples[4:10], self.samples[4:10])
        np.testing.assert_allclose(fade_out.samples[10:14], self.samples[10:14] * np.linspace(1, 0, 4)[:, None], atol=1e-7)

    def test_long_fade_clamps_to_selection_and_one_sample_fades_to_zero(self):
        for effect in ("fade_in", "fade_out"):
            result = edit_selection(self.clip, .2, .7, effect, 50)
            self.assert_unchanged_outside(result)
            endpoint = 4 if effect == "fade_in" else 13
            np.testing.assert_array_equal(result.samples[endpoint], [0, 0])
            one = edit_selection(self.clip, .2, .25, effect, .001)
            np.testing.assert_array_equal(one.samples[4], [0, 0])

    def test_invalid_effect_parameters_are_rejected(self):
        for effect, value in (("gain", float("nan")), ("gain", 25), ("fade_in", 0), ("fade_out", -1), ("unknown", 0)):
            with self.subTest(effect=effect, value=value), self.assertRaises(ValueError):
                edit_selection(self.clip, .2, .7, effect, value)

    def test_paste_at_start_middle_and_end_preserves_all_existing_audio(self):
        copied = self.clip.cut(.2, .4)
        for position in (0, .5, 1):
            with self.subTest(position=position):
                result, selection = insert_clip(self.clip, copied, position)
                frame = round(position * 20)
                np.testing.assert_array_equal(result.samples, np.concatenate((self.samples[:frame], copied.samples, self.samples[frame:])))
                self.assertEqual(selection, (position, position + .2))
                self.assertEqual(result.duration, 1.2)
                np.testing.assert_array_equal(self.clip.samples, self.samples)
                np.testing.assert_array_equal(copied.samples, self.samples[4:8])

    def test_paste_adapts_sample_rate_and_channel_count(self):
        mono = AudioClip(np.full((2400, 1), .25, dtype=np.float32), 24000)
        destination = AudioClip(np.zeros((4800, 2), dtype=np.float32), 48000)
        result, selection = insert_clip(destination, mono, .05)
        self.assertEqual(result.samples.shape, (9600, 2))
        self.assertEqual(selection, (.05, .15))
        np.testing.assert_allclose(result.samples[2400:7200], .25, atol=1e-4)
        stereo = AudioClip(np.tile([.1, .3], (4800, 1)).astype(np.float32), 48000)
        result, _ = insert_clip(mono, stereo, 0)
        self.assertEqual(result.samples.shape, (4800, 1))
        np.testing.assert_allclose(result.samples[:2400], .2, atol=1e-4)

    def test_single_sample_paste_survives_resampling(self):
        copied = AudioClip(np.array([[.5]], dtype=np.float32), 24000)
        destination = AudioClip(np.zeros((10, 2), dtype=np.float32), 48000)
        result, _ = insert_clip(destination, copied, 0)
        self.assertEqual(result.samples.shape, (12, 2))
        np.testing.assert_allclose(result.samples[:2], .5, atol=1e-4)

    def test_invalid_paste_position_and_empty_clip_are_rejected(self):
        for position in (-.1, 2, float("nan")):
            with self.subTest(position=position), self.assertRaises(ValueError):
                insert_clip(self.clip, self.clip, position)
        with self.assertRaises(ValueError):
            insert_clip(self.clip, AudioClip(np.empty((0, 2)), 20), 0)

    def test_remove_joins_remaining_samples_exactly_without_silence(self):
        for start, end in ((0, .2), (.2, .7), (.7, 1)):
            with self.subTest(start=start, end=end):
                edited, join = remove_selection(self.clip, start, end)
                first, last = round(start * 20), round(end * 20)
                np.testing.assert_array_equal(edited.samples, np.concatenate((self.samples[:first], self.samples[last:])))
                self.assertEqual(join, min(start, edited.duration))
                self.assertEqual((edited.sample_rate, edited.channels, edited.source, edited.name), (20, 2, self.clip.source, self.clip.name))
                np.testing.assert_array_equal(self.clip.samples, self.samples)
                edited.samples[:] = 0
                np.testing.assert_array_equal(self.clip.samples, self.samples)

    def test_remove_entire_audio_can_be_followed_by_paste(self):
        empty, join = remove_selection(self.clip, 0, 1)
        self.assertEqual(empty.samples.shape, (0, 2))
        self.assertEqual((empty.duration, join), (0, 0))
        restored, selection = insert_clip(empty, self.clip, 0)
        np.testing.assert_array_equal(restored.samples, self.samples)
        self.assertEqual(selection, (0, 1))

    def test_remove_rejects_empty_or_invalid_selection(self):
        for start, end in ((0, 0), (.7, .2), (-1, .5), (0, 2), (0, float("nan"))):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                remove_selection(self.clip, start, end)


if __name__ == "__main__":
    unittest.main()
