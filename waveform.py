"""Selection-only waveform and a separate playback position bar."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from audio_engine import AudioClip
from i18n import Localizer


def time_label(seconds: float) -> str:
    minutes, rest = divmod(max(0, seconds), 60)
    return f"{int(minutes):02d}:{rest:06.3f}"


class Waveform(QWidget):
    selectionChanged = Signal(float, float)
    viewChanged = Signal(float, float)

    def __init__(self, parent=None, localizer=None):
        super().__init__(parent)
        self.i18n = localizer or Localizer()
        self.setMinimumHeight(150)
        self.setMouseTracking(True)
        self.clip = None
        self.envelope = np.empty((0, 2), dtype=np.float32)
        self.selection = (0.0, 0.0)
        self.view_start = 0.0
        self.view_length = 0.0
        self.cursor = 0.0
        self.anchor = None
        self.drag_mode = ""
        self.i18n.bind(self, "setToolTip", "Arraste para selecionar um trecho ou ajustar as alças. Use a roda para ampliar. A linha amarela indica a reprodução; use a barra abaixo para mudar a posição.")

    def set_clip(self, clip: AudioClip):
        self.clip = clip
        if not len(clip.samples):
            self.envelope = np.empty((0, 2), dtype=np.float32)
            self.selection = (0.0, 0.0)
            self.view_start = self.view_length = self.cursor = 0.0
            self.viewChanged.emit(0, 0)
            self.update()
            return
        # Keep extrema across channels so out-of-phase stereo remains visible.
        block = max(1, int(np.ceil(len(clip.samples) / 24000)))
        chunks = int(np.ceil(len(clip.samples) / block))
        padding = chunks * block - len(clip.samples)
        samples = np.pad(clip.samples, ((0, padding), (0, 0))) if padding else clip.samples
        blocks = samples.reshape(chunks, block, clip.channels)
        self.envelope = np.column_stack((blocks.min(axis=(1, 2)), blocks.max(axis=(1, 2))))
        self.selection = (0.0, clip.duration)
        self.view_start, self.view_length, self.cursor = 0.0, clip.duration, 0.0
        self.viewChanged.emit(self.view_start, self.view_length)
        self.update()

    def plot_rect(self):
        return QRectF(18, 36, max(1, self.width() - 36), max(1, self.height() - 68))

    def x_at(self, seconds):
        rect = self.plot_rect()
        return rect.left() + (seconds - self.view_start) / max(self.view_length, 1e-9) * rect.width()

    def time_at(self, x):
        rect = self.plot_rect()
        fraction = min(1.0, max(0.0, (x - rect.left()) / rect.width()))
        return min(self.clip.duration, self.view_start + fraction * self.view_length) if self.clip else 0

    def set_selection(self, start, end):
        self.selection = (start, end)
        self.update()

    def set_cursor(self, seconds):
        self.cursor = seconds
        self.update()

    def zoom(self, factor, center=None):
        if not self.clip or not len(self.clip.samples):
            return
        center = (self.view_start + self.view_length / 2) if center is None else center
        length = min(self.clip.duration, max(min(.02, self.clip.duration), self.view_length / factor))
        relative = (center - self.view_start) / self.view_length
        self.view_start = min(max(0, center - relative * length), self.clip.duration - length)
        self.view_length = length
        self.viewChanged.emit(self.view_start, self.view_length)
        self.update()

    def show_all(self):
        if self.clip:
            self.view_start, self.view_length = 0.0, self.clip.duration
            self.viewChanged.emit(self.view_start, self.view_length)
            self.update()

    def scroll_to(self, fraction):
        if self.clip:
            self.view_start = fraction * max(0, self.clip.duration - self.view_length)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111822"))
        rect = self.plot_rect()
        if not self.clip or not len(self.clip.samples):
            painter.setPen(QColor("#92a1b5"))
            message = "Áudio vazio\n\nUse Desfazer para recuperar ou Colar no cursor para inserir um trecho." if self.clip is not None else "Seu próximo som começa aqui\n\nAbra um arquivo ou toque em ▶ na biblioteca."
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.i18n.text(message))
            return
        center_y = rect.center().y()
        painter.setPen(QPen(QColor("#273343"), 1))
        for part in range(6):
            x = rect.left() + part / 5 * rect.width()
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            painter.setPen(QColor("#92a1b5"))
            text_x = min(x - 10, self.width() - 80)
            painter.drawText(QRectF(max(12, text_x), self.height() - 25, 85, 20), time_label(self.view_start + part / 5 * self.view_length))
            painter.setPen(QPen(QColor("#273343"), 1))
        for ratio in (.25, .5, .75):
            y = rect.top() + ratio * rect.height()
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        painter.save()
        painter.setClipRect(rect)
        sx, ex = (self.x_at(t) for t in self.selection)
        painter.fillRect(QRectF(sx, rect.top(), ex - sx, rect.height()), QColor(89, 211, 185, 28))
        count = len(self.envelope)
        painter.setPen(QPen(QColor("#62d6bf"), 1))
        for pixel in range(int(rect.width())):
            start = self.view_start + pixel / rect.width() * self.view_length
            end = self.view_start + (pixel + 1) / rect.width() * self.view_length
            left = min(count - 1, int(start / self.clip.duration * count))
            right = min(count, max(left + 1, int(end / self.clip.duration * count) + 1))
            lo, hi = self.envelope[left:right, 0].min(), self.envelope[left:right, 1].max()
            scale = rect.height() * .44
            painter.drawLine(QPointF(rect.left() + pixel, center_y - hi * scale), QPointF(rect.left() + pixel, center_y - lo * scale))
        painter.restore()
        # Visual-only playhead: mouse handling below still targets selection edges only.
        x = self.x_at(self.cursor)
        if rect.left() <= x <= rect.right():
            painter.setPen(QPen(QColor("#ffce77"), 2))
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#ffce77"))
            painter.drawPolygon(QPolygonF([QPointF(x - 5, rect.top() + 1),
                                           QPointF(x + 5, rect.top() + 1),
                                           QPointF(x, rect.top() + 8)]))
        painter.setPen(QPen(QColor("#62d6bf"), 2))
        for x in (sx, ex):
            if rect.left() <= x <= rect.right():
                painter.drawLine(QPointF(x, rect.top() - 6), QPointF(x, rect.bottom() + 4))
                painter.setBrush(QColor("#62d6bf"))
                painter.drawRoundedRect(QRectF(x - 4, rect.top() - 8, 8, 16), 2, 2)
        painter.setPen(QColor("#aab8ca"))
        painter.drawText(QRectF(18, 8, self.width() - 36, 22), self.i18n.text("FORMA DE ONDA    ·    {0} canal(is)    ·    arraste para selecionar", self.clip.channels))

    def mousePressEvent(self, event):
        if not self.clip or event.button() != Qt.MouseButton.LeftButton:
            return
        self.anchor = event.position().x()
        start, end = self.selection
        if abs(self.anchor - self.x_at(start)) < 9:
            self.drag_mode = "start"
        elif abs(self.anchor - self.x_at(end)) < 9:
            self.drag_mode = "end"
        else:
            self.drag_mode = "new"

    def mouseMoveEvent(self, event):
        if not self.clip:
            return
        x = event.position().x()
        if self.anchor is None:
            near = any(abs(x - self.x_at(t)) < 9 for t in self.selection)
            self.setCursor(Qt.CursorShape.SizeHorCursor if near else Qt.CursorShape.CrossCursor)
            return
        value = self.time_at(x)
        start, end = self.selection
        minimum = 1 / self.clip.sample_rate
        if self.drag_mode == "start":
            start = min(value, end - minimum)
        elif self.drag_mode == "end":
            end = max(value, start + minimum)
        elif abs(x - self.anchor) >= 3:
            start, end = sorted((self.time_at(self.anchor), value))
        else:
            return
        if end - start >= minimum:
            self.set_selection(start, end)
            self.selectionChanged.emit(start, end)

    def mouseReleaseEvent(self, event):
        if self.anchor is not None:
            self.anchor = None
            self.drag_mode = ""

    def wheelEvent(self, event):
        if self.clip:
            self.zoom(1.4 if event.angleDelta().y() > 0 else 1 / 1.4, self.time_at(event.position().x()))
            event.accept()


class PlaybackBar(QWidget):
    """Independent, full-document seek track; dragging never changes the selection."""
    seekRequested = Signal(float)

    def __init__(self, parent=None, localizer=None):
        super().__init__(parent)
        self.i18n = localizer or Localizer()
        self.duration = self.cursor = 0.0
        self.dragging = False
        self.setFixedHeight(28)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.i18n.bind(self, "setAccessibleName", "Posição de reprodução")
        self.i18n.bind(self, "setToolTip", "Clique ou arraste para posicionar a reprodução e a colagem. Setas: mover 0,1 s; Home/End: início/fim.")

    def set_duration(self, duration):
        self.duration = max(0.0, duration)
        self.cursor = min(self.cursor, self.duration)
        self.dragging = False
        self.update()

    def set_cursor(self, seconds):
        self.cursor = min(self.duration, max(0.0, seconds))
        self.update()

    def track_rect(self):
        return QRectF(18, self.height() / 2 - 2, max(1, self.width() - 36), 4)

    def x_at(self, seconds):
        rect = self.track_rect()
        return rect.left() + min(1, max(0, seconds / max(self.duration, 1e-9))) * rect.width()

    def seek_at(self, x):
        if not self.isEnabled() or not self.duration:
            return
        rect = self.track_rect()
        seconds = min(1, max(0, (x - rect.left()) / rect.width())) * self.duration
        self.set_cursor(seconds)
        self.seekRequested.emit(seconds)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111822"))
        rect = self.track_rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#35465c"))
        painter.drawRoundedRect(rect, 2, 2)
        x = self.x_at(self.cursor)
        color = QColor("#ffce77" if self.isEnabled() else "#68788f")
        painter.setBrush(color)
        painter.drawRoundedRect(QRectF(rect.left(), rect.top(), x - rect.left(), rect.height()), 2, 2)
        painter.drawEllipse(QPointF(x, rect.center().y()), 5, 5)
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(color, 1))
            painter.drawEllipse(QPointF(x, rect.center().y()), 8, 8)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled() and self.duration:
            self.dragging = True
            self.seek_at(event.position().x())
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.seek_at(event.position().x())
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.seek_at(event.position().x())
            self.dragging = False
            event.accept()

    def keyPressEvent(self, event):
        keys = {Qt.Key.Key_Left: self.cursor - .1, Qt.Key.Key_Right: self.cursor + .1,
                Qt.Key.Key_Home: 0, Qt.Key.Key_End: self.duration}
        if self.isEnabled() and self.duration and event.key() in keys:
            self.set_cursor(keys[event.key()])
            self.seekRequested.emit(self.cursor)
            event.accept()
        else:
            super().keyPressEvent(event)
