from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from file_browser import copy_files


class FileCopyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="sound-manager-copy-")
        self.root = Path(self.directory.name)
        self.source = self.root / "Som com espaços.wav"
        self.source.write_bytes(b"unchanged source audio")
        self.destination = self.root / "Destino"
        self.destination.mkdir()

    def tearDown(self):
        self.assertEqual(self.source.read_bytes(), b"unchanged source audio")
        self.directory.cleanup()

    def test_copy_preserves_original_and_exact_bytes(self):
        result = copy_files([self.source], self.destination)
        self.assertEqual(result, [self.destination / self.source.name])
        self.assertEqual(result[0].read_bytes(), self.source.read_bytes())

    def test_duplicate_names_and_same_folder_get_unique_copies(self):
        existing = self.destination / self.source.name
        existing.write_bytes(b"keep existing")
        first = copy_files([self.source], self.destination)[0]
        second = copy_files([self.source], self.destination)[0]
        self.assertNotEqual(first, second)
        self.assertEqual(existing.read_bytes(), b"keep existing")
        self.assertEqual(first.read_bytes(), self.source.read_bytes())
        self.assertEqual(second.read_bytes(), self.source.read_bytes())
        same_folder_copy = copy_files([self.source], self.root)[0]
        self.assertNotEqual(same_folder_copy, self.source)
        self.assertEqual(same_folder_copy.read_bytes(), self.source.read_bytes())

    def test_failed_copy_removes_its_partial_file(self):
        with patch("file_browser.shutil.copyfileobj", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                copy_files([self.source], self.destination)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_non_audio_and_directory_sources_are_rejected(self):
        unrelated = self.root / "notes.txt"
        unrelated.write_text("keep")
        for source in (unrelated, self.destination):
            with self.assertRaises(ValueError):
                copy_files([source], self.destination)
        self.assertEqual(list(self.destination.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
