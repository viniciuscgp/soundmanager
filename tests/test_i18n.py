from pathlib import Path
import gc
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from i18n import Localizer, Message, normalize_language


class Label:
    def setText(self, value):
        self.value = value


class LocalizationTests(unittest.TestCase):
    def test_supported_language_and_invalid_preference_fallback(self):
        self.assertEqual(normalize_language("en_US"), "en")
        for language in (None, "fr", "pt-BR", "pt_BR"):
            self.assertEqual(normalize_language(language), "pt_BR")

    def test_nested_translation_preserves_filename_arguments(self):
        locale = Localizer("en")
        self.assertEqual(locale.text("Biblioteca: {0}", "Biblioteca"), "Library: Biblioteca")
        self.assertEqual(locale.text("{0}{1}", "Nome", Message(" · alterado")), "Nome · modified")
        self.assertEqual(locale.text("Trecho: {0:.4f} s", .125), "Selection: 0.1250 s")
        self.assertEqual(locale.text("{0}: concluído.", Message("Colar trecho")), "Paste audio: completed.")

    def test_binding_replaces_old_state_and_can_switch_both_directions(self):
        locale, label = Localizer(), Label()
        locale.bind(label, "setText", "Cópia: vazia")
        locale.bind(label, "setText", "Cópia: {0:.4f} s", .5)
        locale.set_language("en")
        self.assertEqual(label.value, "Clipboard: 0.5000 s")
        locale.set_language("pt_BR")
        self.assertEqual(label.value, "Cópia: 0.5000 s")
        self.assertEqual(len(locale._bindings), 1)

    def test_removed_widgets_are_not_retained(self):
        locale, label = Localizer(), Label()
        locale.bind(label, "setText", "Salvar áudio")
        del label
        gc.collect()
        locale.set_language("en")
        self.assertEqual(len(locale._bindings), 0)

    def test_engine_errors_keep_external_diagnostic_and_filename(self):
        locale = Localizer("en")
        self.assertEqual(locale.error("Não é um arquivo de áudio: Nome"), "Not an audio file: Nome")
        self.assertEqual(locale.error("Não foi possível converter o áudio. codec XYZ"), "Could not convert the audio. codec XYZ")
        self.assertEqual(locale.error("Este arquivo não contém amostras de áudio."), "This file contains no audio samples.")


if __name__ == "__main__":
    unittest.main()
