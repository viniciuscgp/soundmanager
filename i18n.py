"""Per-window translations and bindings that preserve the current document."""
from __future__ import annotations

from dataclasses import dataclass
import weakref


# Portuguese is also the source language. Keep filenames and paths out of this catalog.
ENGLISH = {
    "BIBLIOTECA LOCAL DE ÁUDIO": "LOCAL AUDIO LIBRARY",
    "Ouça. Selecione. Salve.": "Listen. Select. Save.",
    "Idioma": "Language",
    "Escolha o idioma da interface. A escolha é salva automaticamente.": "Choose the interface language. Your choice is saved automatically.",
    "Escolha a pasta onde você guarda seus sons.": "Choose the folder where you keep your sounds.",
    "Escolher biblioteca…": "Choose library…",
    "Abrir arquivo…": "Open file…",
    "↑ Subir": "↑ Up",
    "Subir uma pasta (Alt+↑)": "Go up one folder (Alt+↑)",
    "Raiz": "Root",
    "PASTAS": "FOLDERS",
    "PASTAS · buscando…": "FOLDERS · searching…",
    "Filtrar pastas ou arquivos…": "Filter folders or files…",
    "Mostra pastas com o texto no nome ou em nomes de arquivos dentro delas, inclusive em subpastas.": "Find folders matching the text in their name or in filenames inside them, including subfolders.",
    "Arraste arquivos para uma pasta\naqui ou no Explorer para copiar.": "Drag files to a folder here\nor in your file manager to copy them.",
    "Biblioteca": "Library",
    "Biblioteca: {0}": "Library: {0}",
    "Filtrar arquivos pelo nome…": "Filter files by name…",
    "Mostra arquivos da pasta atual cujo nome contém o texto.": "Show files in the current folder whose names contain the text.",
    "Ouvir / editar": "Listen / edit",
    "Nome": "Name",
    "Arquivo": "File",
    "Reprodução": "Playback",
    "Arraste concluído.": "Drag completed.",
    "Arraste cancelado.": "Drag canceled.",
    "Nenhum som aberto": "No sound open",
    "Selecione um som para ouvir e recortar.": "Select a sound to listen to and trim.",
    "Mostrar o arquivo original no Explorer.": "Show the original file in your file manager.",
    "Mostrar arquivo": "Show file",
    "Fechar o editor deste som.": "Close this sound's editor.",
    "Parar este som e voltar ao início.": "Stop this sound and return to the start.",
    "Reproduzir somente a seleção.": "Play only the selection.",
    "Repetir este som ou o trecho em reprodução.": "Loop this sound or the selection being played.",
    "Volume de reprodução; não altera as amostras do som.": "Playback volume; does not change the audio samples.",
    "Copiar seleção para a área temporária. Ctrl+C": "Copy the selection to the audio clipboard. Ctrl+C",
    "Colar o trecho na posição da barra de reprodução. Ctrl+V": "Paste the copied audio at the playback bar position. Ctrl+V",
    "Remover seleção e juntar as partes restantes. Ctrl+Z desfaz": "Remove the selection and join the remaining parts. Ctrl+Z to undo",
    "Desfazer a última edição. Ctrl+Z": "Undo the last edit. Ctrl+Z",
    "Refazer a edição. Ctrl+Y ou Ctrl+Shift+Z": "Redo the edit. Ctrl+Y or Ctrl+Shift+Z",
    "Selecionar todo o áudio. Ctrl+A": "Select all audio. Ctrl+A",
    "Inverter áudio selecionado: tocar de trás para frente, mantendo os canais.": "Reverse the selected audio: play backwards while keeping the channels.",
    "Inverter áudio selecionado": "Reverse selected audio",
    "Diminuir zoom da onda.": "Zoom out on the waveform.",
    "Ampliar onda.": "Zoom in on the waveform.",
    "Ver o áudio inteiro.": "Show the entire audio.",
    "Início": "Start",
    "Fim": "End",
    "Trecho: —": "Selection: —",
    "Trecho: {0:.4f} s": "Selection: {0:.4f} s",
    "Diminuir o volume da seleção pelo valor em dB ao lado.": "Decrease the selection volume by the dB value shown.",
    "Aumentar o volume da seleção pelo valor em dB ao lado.": "Increase the selection volume by the dB value shown.",
    "Fade in: aumentar suavemente no início da seleção pela duração indicada.": "Fade in: gradually increase volume at the start of the selection for the specified duration.",
    "Fade out: diminuir suavemente no final da seleção pela duração indicada.": "Fade out: gradually decrease volume at the end of the selection for the specified duration.",
    "Cópia: vazia": "Clipboard: empty",
    "Cópia: {0:.4f} s": "Clipboard: {0:.4f} s",
    "Salvar a seleção em um novo arquivo. Ctrl+Shift+S": "Save the selection to a new file. Ctrl+Shift+S",
    "Salvar trecho…": "Save selection…",
    "Salvar todo o áudio no arquivo aberto, após confirmação. Ctrl+S": "Save all audio to the open file after confirmation. Ctrl+S",
    "Salvar áudio": "Save audio",
    "Pronto para explorar sua biblioteca.": "Ready to explore your library.",
    "Alterado · salvar": "Modified · save",
    "Escolha a pasta base da sua biblioteca de sons": "Choose the root folder for your sound library",
    "Não foi possível filtrar as pastas: {0}": "Could not filter folders: {0}",
    "Esta biblioteca não tem subpastas.": "This library has no subfolders.",
    "Buscando nas pastas e nos arquivos…": "Searching folders and files…",
    "Nenhuma pasta ou arquivo corresponde ao filtro.": "No folders or files match the filter.",
    "Não foi possível abrir a pasta": "Could not open the folder",
    "▶ ouvir / pausar   ·   Recortar abre a onda nesta linha": "▶ play / pause   ·   Trim opens the waveform in this row",
    "{0} arquivo(s) de áudio · arraste pelo nome para copiar": "{0} audio file(s) · drag the name to copy",
    "Nenhum arquivo de áudio nesta pasta.\nEscolha outra pasta à esquerda.": "No audio files in this folder.\nChoose another folder on the left.",
    "{0} resultado(s) nesta pasta": "{0} result(s) in this folder",
    "Nenhum arquivo corresponde ao filtro.": "No files match the filter.",
    "Copiando {0} arquivo(s) para {1}…": "Copying {0} file(s) to {1}…",
    "Erro ao copiar arquivos": "Error copying files",
    "Copiado(s) {0} arquivo(s) para {1}": "Copied {0} file(s) to {1}",
    "Abrir som": "Open sound",
    "Áudio ({0});;Todos os arquivos (*)": "Audio ({0});;All files (*)",
    "Abrindo…": "Opening…",
    "Carregando {0}…": "Loading {0}…",
    "Lendo o áudio e preparando a forma de onda…": "Reading audio and preparing the waveform…",
    "Abrindo {0}…": "Opening {0}…",
    "Concluindo a edição de {0}…": "Finishing the edit of {0}…",
    "Não foi possível abrir o som": "Could not open the sound",
    "Escolha outro arquivo na biblioteca.": "Choose another file in the library.",
    "Erro ao abrir": "Error opening file",
    "Erro ao abrir áudio": "Error opening audio",
    "ÁUDIO COPIADO": "COPIED AUDIO",
    "{0} canais": "{0} channels",
    "Som aberto. Use Recortar na linha para selecionar um trecho.": "Sound opened. Use Trim in the row to select a section.",
    " · alterado": " · modified",
    "Não foi possível editar o áudio": "Could not edit the audio",
    "{0}: concluído.": "{0}: completed.",
    " O pico ultrapassa o limite; diminua o volume para evitar distorção.": " The peak exceeds the limit; reduce the volume to avoid distortion.",
    "Aumentar volume": "Increase volume",
    "Diminuir volume": "Decrease volume",
    "Inverter trecho": "Reverse selection",
    "Inverter polaridade": "Invert polarity",
    "Aplicar fade in": "Apply fade in",
    "Aplicar fade out": "Apply fade out",
    "Remover seleção": "Remove selection",
    "Desfazer": "Undo",
    "Refazer": "Redo",
    "Colar trecho": "Paste audio",
    "Trecho inválido": "Invalid selection",
    "Preparando a reprodução do trecho…": "Preparing selection playback…",
    "Erro ao reproduzir trecho": "Error playing selection",
    "Reproduzindo trecho: {0:.4f} s — {1:.4f} s": "Playing selection: {0:.4f} s — {1:.4f} s",
    "Pausa": "Pause",
    "Pausar a reprodução. Espaço": "Pause playback. Space",
    "Reproduzir / retomar a seleção. Espaço": "Play / resume the selection. Space",
    "Falha na reprodução: {0}": "Playback failed: {0}",
    "Abra um som primeiro.": "Open a sound first.",
    "Colar {0:.4f} s na posição da barra de reprodução. Ctrl+V": "Paste {0:.4f} s at the playback bar position. Ctrl+V",
    "Trecho de {0:.4f} s copiado. Abra outro som, posicione a barra de reprodução e use o ícone Colar.": "Copied {0:.4f} s. Open another sound, position the playback bar and use the Paste icon.",
    "Erro ao copiar trecho": "Error copying selection",
    "Salvar áudio?": "Save audio?",
    "Deseja salvar as alterações neste arquivo?\n\n{0}\n\nO arquivo será substituído pelo áudio completo em edição.": "Save changes to this file?\n\n{0}\n\nThe file will be replaced with the entire audio being edited.",
    "Salvando {0}…": "Saving {0}…",
    "Erro ao salvar áudio": "Error saving audio",
    "Salvo: {0}": "Saved: {0}",
    "Salvar áudio como": "Save audio as",
    "Salvar trecho como": "Save selection as",
    "Substituir arquivo?": "Replace file?",
    "{0} já existe. Deseja substituir?": "{0} already exists. Replace it?",
    "Escolha uma pasta à esquerda para ver os arquivos.": "Choose a folder on the left to see its files.",
    "⌃ Fechar": "⌃ Close",
    "⌄ Recortar": "⌄ Trim",
    "Arraste para selecionar um trecho ou ajustar as alças. Use a roda para ampliar. A linha amarela indica a reprodução; use a barra abaixo para mudar a posição.": "Drag to select audio or adjust the handles. Use the wheel to zoom. The yellow line shows playback; use the bar below to change position.",
    "Áudio vazio\n\nUse Desfazer para recuperar ou Colar no cursor para inserir um trecho.": "Empty audio\n\nUse Undo to restore it or Paste at the cursor to insert audio.",
    "Seu próximo som começa aqui\n\nAbra um arquivo ou toque em ▶ na biblioteca.": "Your next sound starts here\n\nOpen a file or click ▶ in the library.",
    "FORMA DE ONDA    ·    {0} canal(is)    ·    arraste para selecionar": "WAVEFORM    ·    {0} channel(s)    ·    drag to select",
    "Posição de reprodução": "Playback position",
    "Clique ou arraste para posicionar a reprodução e a colagem. Setas: mover 0,1 s; Home/End: início/fim.": "Click or drag to position playback and pasting. Arrows: move 0.1 s; Home/End: start/end.",
    "Trecho copiado": "Copied audio",
    "{0} — trecho": "{0} — selection",
    "Selecione um trecho válido: o fim deve ser maior que o início.": "Select a valid section: the end must be after the start.",
    "O trecho precisa conter pelo menos uma amostra de áudio.": "The selection must contain at least one audio sample.",
    "O ajuste de volume precisa estar entre -60 e +24 dB.": "The volume adjustment must be between -60 and +24 dB.",
    "A duração do fade precisa ser maior que zero.": "The fade duration must be greater than zero.",
    "Efeito de áudio desconhecido.": "Unknown audio effect.",
    "Escolha uma posição dentro do áudio para colar.": "Choose a position within the audio to paste.",
    "A área temporária não contém áudio.": "The audio clipboard is empty.",
    "Formato não suportado. Abra um arquivo WAV, OGG, MP3, FLAC, AIFF, M4A, AAC, OPUS ou WMA.": "Unsupported format. Open a WAV, OGG, MP3, FLAC, AIFF, M4A, AAC, OPUS or WMA file.",
    "Este arquivo não contém amostras de áudio.": "This file contains no audio samples.",
    "Escolha outro nome: o arquivo original não pode ser sobrescrito.": "Choose another name: the original file cannot be overwritten.",
    "Salve com a extensão .wav, .ogg, .flac ou .mp3.": "Save with the .wav, .ogg, .flac or .mp3 extension.",
    "Este áudio não tem um arquivo original para salvar.": "This audio has no original file to save.",
    "Formato do arquivo original não suportado.": "Unsupported original file format.",
    "O áudio está vazio. Desfaça a remoção ou cole um trecho antes de salvar.": "The audio is empty. Undo the removal or paste audio before saving.",
    "O destino precisa ser uma pasta.": "The destination must be a folder.",
    "Não é um arquivo de áudio: {0}": "Not an audio file: {0}",
    "Não foi possível converter o áudio. {0}": "Could not convert the audio. {0}",
}


def normalize_language(value):
    return "en" if str(value).lower() in {"en", "en-us", "en_us"} else "pt_BR"


@dataclass(frozen=True)
class Message:
    """A nested translated value; ordinary format arguments remain untouched."""
    source: str
    values: tuple = ()


class Localizer:
    def __init__(self, language="pt_BR"):
        self.language = normalize_language(language)
        self._bindings = {}

    def text(self, source, *values):
        if isinstance(source, Message):
            return self.text(source.source, *source.values)
        if isinstance(source, (list, tuple)):
            return [self.text(item) for item in source]
        translated = ENGLISH.get(source, source) if self.language == "en" else source
        if not values:
            return translated
        return translated.format(*(self.text(value) if isinstance(value, Message) else value for value in values))

    def error_message(self, message):
        # Engine errors remain language-independent internally; translate at the UI boundary.
        for prefix in ("Não é um arquivo de áudio: ", "Não foi possível converter o áudio. "):
            if message.startswith(prefix):
                return Message(prefix + "{0}", (message[len(prefix):],))
        return Message(message)

    def error(self, message):
        return self.text(self.error_message(message))

    def bind(self, target, method, source, *values, prefix=()):
        key = (id(target), method, prefix)
        self._bindings[key] = (weakref.ref(target, lambda _: self._bindings.pop(key, None)), method, source, values, prefix)
        self._apply(self._bindings[key])

    def _apply(self, binding):
        reference, method, source, values, prefix = binding
        target = reference()
        if target is None:
            return
        translated = self.text(source, *values)
        if method == "empty_message":
            target.empty_message = translated
            target.viewport().update()
        else:
            getattr(target, method)(*prefix, translated)

    def set_language(self, language):
        self.language = normalize_language(language)
        for key, binding in list(self._bindings.items()):
            try:
                self._apply(binding)
            except RuntimeError:  # A row may have been removed by a folder refresh.
                self._bindings.pop(key, None)
