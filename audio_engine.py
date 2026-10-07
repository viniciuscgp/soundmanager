"""Audio decoding, in-memory editing, export and atomic document saving."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
import tempfile

import imageio_ffmpeg
import numpy as np
import soundfile as sf

EXTENSIONS = frozenset({".wav", ".ogg", ".mp3", ".flac", ".aif", ".aiff", ".m4a", ".aac", ".opus", ".wma"})
EXPORT_FORMATS = {".wav": ("WAV", "PCM_24"), ".flac": ("FLAC", "PCM_24"), ".ogg": ("OGG", "VORBIS")}


@dataclass
class AudioClip:
    samples: np.ndarray
    sample_rate: int
    source: Path | None = None
    name: str = "Trecho copiado"

    @property
    def duration(self) -> float:
        return len(self.samples) / self.sample_rate

    @property
    def channels(self) -> int:
        return self.samples.shape[1]

    def cut(self, start: float, end: float) -> "AudioClip":
        first, last = self.selection_frames(start, end)
        return AudioClip(self.samples[first:last].copy(), self.sample_rate, self.source, f"{Path(self.name).stem} — trecho")

    def selection_frames(self, start: float, end: float) -> tuple[int, int]:
        if not np.isfinite(start) or not np.isfinite(end) or not 0 <= start < end <= self.duration + 1e-6:
            raise ValueError("Selecione um trecho válido: o fim deve ser maior que o início.")
        first = max(0, min(len(self.samples), round(start * self.sample_rate)))
        last = max(0, min(len(self.samples), round(end * self.sample_rate)))
        if last <= first:
            raise ValueError("O trecho precisa conter pelo menos uma amostra de áudio.")
        return first, last


def edit_selection(clip: AudioClip, start: float, end: float, effect: str, value: float = 0) -> AudioClip:
    """Return a new document; keep samples outside the selection byte-identical."""
    first, last = clip.selection_frames(start, end)
    samples = clip.samples.copy()
    selected = samples[first:last]
    if effect == "gain":
        if not np.isfinite(value) or not -60 <= value <= 24:
            raise ValueError("O ajuste de volume precisa estar entre -60 e +24 dB.")
        selected *= np.float32(10 ** (value / 20))
    elif effect == "reverse":
        selected[:] = selected[::-1].copy()
    elif effect == "polarity":
        selected *= -1
    elif effect in {"fade_in", "fade_out"}:
        if not np.isfinite(value) or value <= 0:
            raise ValueError("A duração do fade precisa ser maior que zero.")
        count = min(last - first, max(1, round(value * clip.sample_rate)))
        if effect == "fade_in":
            curve = np.linspace(0, 1, count, dtype=np.float32) if count > 1 else np.zeros(1, dtype=np.float32)
            selected[:count] *= curve[:, None]
        else:
            curve = np.linspace(1, 0, count, dtype=np.float32) if count > 1 else np.zeros(1, dtype=np.float32)
            selected[-count:] *= curve[:, None]
    else:
        raise ValueError("Efeito de áudio desconhecido.")
    return AudioClip(samples, clip.sample_rate, clip.source, clip.name)


def convert_for_paste(clip: AudioClip, sample_rate: int, channels: int) -> np.ndarray:
    samples = clip.samples
    if clip.channels == 1 and channels > 1:
        samples = np.repeat(samples, channels, axis=1)
    elif channels == 1 and clip.channels > 1:
        samples = samples.mean(axis=1, keepdims=True, dtype=np.float32)
    if clip.sample_rate == sample_rate and samples.shape[1] == channels:
        return samples.copy()
    with tempfile.TemporaryDirectory(prefix="sound-manager-paste-") as directory:
        source, destination = Path(directory) / "source.wav", Path(directory) / "converted.wav"
        # The resampler needs a small input window, even for one-sample selections.
        if len(samples) < 64:
            samples = np.pad(samples, ((0, 64 - len(samples)), (0, 0)), mode="edge")
        sf.write(str(source), samples, clip.sample_rate, subtype="FLOAT")
        run_ffmpeg(["-y", "-i", str(source), "-ar", str(sample_rate), "-ac", str(channels), "-c:a", "pcm_f32le", str(destination)])
        converted, _ = sf.read(str(destination), dtype="float32", always_2d=True)
    # Keep the inserted duration independent of codec/resampler rounding and delay.
    expected = max(1, round(clip.duration * sample_rate))
    if len(converted) < expected:
        converted = np.pad(converted, ((0, expected - len(converted)), (0, 0)))
    return converted[:expected].copy()


def insert_clip(destination: AudioClip, copied: AudioClip, position: float) -> tuple[AudioClip, tuple[float, float]]:
    if not np.isfinite(position) or not 0 <= position <= destination.duration + 1e-6:
        raise ValueError("Escolha uma posição dentro do áudio para colar.")
    if not len(copied.samples):
        raise ValueError("A área temporária não contém áudio.")
    frame = min(len(destination.samples), round(position * destination.sample_rate))
    inserted = convert_for_paste(copied, destination.sample_rate, destination.channels)
    samples = np.concatenate((destination.samples[:frame], inserted, destination.samples[frame:]), axis=0)
    start, end = frame / destination.sample_rate, (frame + len(inserted)) / destination.sample_rate
    return AudioClip(samples, destination.sample_rate, destination.source, destination.name), (start, end)


def remove_selection(clip: AudioClip, start: float, end: float) -> tuple[AudioClip, float]:
    """Delete selected frames and join the two untouched parts without adding silence."""
    first, last = clip.selection_frames(start, end)
    samples = np.concatenate((clip.samples[:first], clip.samples[last:]), axis=0)
    edited = AudioClip(samples, clip.sample_rate, clip.source, clip.name)
    return edited, min(first / clip.sample_rate, edited.duration)


def run_ffmpeg(arguments: list[str]) -> None:
    executable = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run(
        [executable, "-hide_banner", "-loglevel", "error", "-nostdin", *arguments],
        capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        timeout=300,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"Não foi possível converter o áudio. {detail[-1200:]}")


def load_audio(path: Path) -> AudioClip:
    path = path.resolve(strict=True)
    if path.suffix.lower() not in EXTENSIONS:
        raise ValueError("Formato não suportado. Abra um arquivo WAV, OGG, MP3, FLAC, AIFF, M4A, AAC, OPUS ou WMA.")
    try:
        samples, rate = sf.read(str(path), dtype="float32", always_2d=True)
    except (RuntimeError, sf.LibsndfileError):
        with tempfile.TemporaryDirectory(prefix="sound-manager-decode-") as directory:
            decoded = Path(directory) / "decoded.wav"
            run_ffmpeg(["-y", "-i", str(path), "-vn", "-c:a", "pcm_f32le", str(decoded)])
            samples, rate = sf.read(str(decoded), dtype="float32", always_2d=True)
    if not len(samples):
        raise ValueError("Este arquivo não contém amostras de áudio.")
    if not np.isfinite(samples).all():
        samples = np.nan_to_num(samples)
    return AudioClip(samples, rate, path, path.name)


def write_preview(clip: AudioClip, destination: Path) -> None:
    sf.write(str(destination), clip.samples, clip.sample_rate, format="WAV", subtype="PCM_16")


def export_audio(clip: AudioClip, destination: Path) -> Path:
    """Write atomically, refusing to overwrite the opened source (including hard links)."""
    destination = destination.resolve()
    if clip.source and (destination == clip.source.resolve() or (
        destination.exists() and clip.source.exists() and os.path.samefile(destination, clip.source)
    )):
        raise ValueError("Escolha outro nome: o arquivo original não pode ser sobrescrito.")
    suffix = destination.suffix.lower()
    if suffix not in {*EXPORT_FORMATS, ".mp3"}:
        raise ValueError("Salve com a extensão .wav, .ogg, .flac ou .mp3.")
    return _write_audio(clip, destination)


def save_audio(clip: AudioClip) -> Path:
    """Replace the edited document only; callers must confirm with the user first."""
    if not clip.source or clip.name != clip.source.name:
        raise ValueError("Este áudio não tem um arquivo original para salvar.")
    destination = clip.source.resolve(strict=True)
    if destination.suffix.lower() not in EXTENSIONS:
        raise ValueError("Formato do arquivo original não suportado.")
    if not len(clip.samples):
        raise ValueError("O áudio está vazio. Desfaça a remoção ou cole um trecho antes de salvar.")
    encoding = None
    if destination.suffix.lower() in {".wav", ".flac", ".aif", ".aiff"}:
        info = sf.info(str(destination))
        encoding = (info.format, info.subtype)
    return _write_audio(clip, destination, encoding)


def _write_audio(clip: AudioClip, destination: Path, encoding=None) -> Path:
    """Encode beside the destination, replacing it only after encoding succeeds."""
    suffix = destination.suffix.lower()
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".sound-manager-", suffix=suffix, dir=destination.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        if encoding is not None:
            format_name, subtype = encoding
            sf.write(str(temporary), clip.samples, clip.sample_rate, format=format_name, subtype=subtype)
        elif suffix not in EXPORT_FORMATS:
            codecs = {".mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
                      ".m4a": ["-c:a", "aac", "-b:a", "192k"],
                      ".aac": ["-c:a", "aac", "-b:a", "192k"],
                      ".opus": ["-c:a", "libopus", "-b:a", "128k"],
                      ".wma": ["-c:a", "wmav2", "-b:a", "192k"]}
            with tempfile.TemporaryDirectory(prefix="sound-manager-export-") as directory:
                wav = Path(directory) / "selection.wav"
                sf.write(str(wav), clip.samples, clip.sample_rate, subtype="FLOAT")
                run_ffmpeg(["-y", "-i", str(wav), *codecs[suffix], str(temporary)])
        else:
            format_name, subtype = EXPORT_FORMATS[suffix]
            sf.write(str(temporary), clip.samples, clip.sample_rate, format=format_name, subtype=subtype)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
