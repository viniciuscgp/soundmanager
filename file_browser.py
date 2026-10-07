"""Copy-only native file drags, folder drops and compact per-file actions."""
from pathlib import Path
import os
import shutil
import struct

from PySide6.QtCore import Qt, Signal, QMimeData, QUrl, QRectF, QTimer
from PySide6.QtGui import QDrag, QColor, QPainter
from PySide6.QtWidgets import QTreeWidget, QTreeView, QAbstractItemView, QStyledItemDelegate, QStyle

from audio_engine import EXTENSIONS


def index_library(base: Path, cancelled) -> dict[Path, list[str]]:
    """Index folder and file names without reading file contents or following directory links."""
    folders, pending = {base: []}, [base]
    while pending and not cancelled.is_set():
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if cancelled.is_set():
                        return {}
                    if entry.name.startswith((".", "__")):
                        continue
                    path = Path(entry.path)
                    if entry.is_dir(follow_symlinks=False):
                        if getattr(os.path, "isjunction", lambda _: False)(path):
                            continue
                        folders[path] = []
                        pending.append(path)
                    elif entry.is_file():
                        folders[directory].append(entry.name.casefold())
        except OSError:
            continue
    return folders


def copy_files(sources: list[Path], directory: Path) -> list[Path]:
    directory = directory.resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("O destino precisa ser uma pasta.")
    copied = []
    for source in sources:
        source = source.resolve(strict=True)
        if not source.is_file() or source.suffix.lower() not in EXTENSIONS:
            raise ValueError(f"Não é um arquivo de áudio: {source.name}")
        number = 0
        while True:
            name = source.name if number == 0 else f"{source.stem} (cópia{'' if number == 1 else ' ' + str(number)}){source.suffix}"
            destination = directory / name
            try:
                output = destination.open("xb")
                break
            except FileExistsError:
                number += 1
        try:
            with output, source.open("rb") as original:
                shutil.copyfileobj(original, output, length=1024 * 1024)
            shutil.copystat(source, destination)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        copied.append(destination)
    return copied


class FileList(QTreeWidget):
    dragFinished = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.setExpandsOnDoubleClick(False)
        self.drag_from_name = False
        self.empty_message = "Escolha uma pasta à esquerda para ver os arquivos."

    def mousePressEvent(self, event):
        index = self.indexAt(event.position().toPoint())
        self.drag_from_name = index.isValid() and index.column() == 1
        super().mousePressEvent(event)

    def file_mime_data(self):
        mime = QMimeData()
        urls = [QUrl.fromLocalFile(item.data(1, Qt.ItemDataRole.UserRole))
                for item in self.selectedItems() if item.data(1, Qt.ItemDataRole.UserRole)]
        mime.setUrls(urls)
        # Windows Explorer receives an explicit copy preference, even on the same drive.
        mime.setData('application/x-qt-windows-mime;value="Preferred DropEffect"', struct.pack("<I", 1))
        return mime

    def startDrag(self, supported_actions):
        if not self.drag_from_name:
            return
        mime = self.file_mime_data()
        if not mime.urls():
            return
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon).pixmap(32, 32))
        self.dragFinished.emit(drag.exec(Qt.DropAction.CopyAction, Qt.DropAction.CopyAction))

    def paintEvent(self, event):
        super().paintEvent(event)
        if not any(not self.topLevelItem(row).isHidden() for row in range(self.topLevelItemCount())):
            painter = QPainter(self.viewport())
            painter.setPen(QColor("#92a1b5"))
            painter.drawText(self.viewport().rect().adjusted(25, 25, -25, -25),
                             Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.empty_message)


class FolderTree(QTreeView):
    copyRequested = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.setDropIndicatorShown(False)
        self.setAutoExpandDelay(600)
        self.hover_index = None
        self.empty_message = "Esta biblioteca não tem subpastas."
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.setInterval(600)
        self.hover_timer.timeout.connect(self.expand_hovered)

    def expand_hovered(self):
        if self.hover_index is not None and self.hover_index.isValid():
            self.expand(self.hover_index)

    @staticmethod
    def audio_paths(mime):
        if not mime.hasUrls():
            return []
        paths = [Path(url.toLocalFile()) for url in mime.urls() if url.isLocalFile()]
        return paths if paths and all(path.is_file() and path.suffix.lower() in EXTENSIONS for path in paths) else []

    def dragEnterEvent(self, event):
        if self.audio_paths(event.mimeData()) and event.possibleActions() & Qt.DropAction.CopyAction:
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if not self.audio_paths(event.mimeData()) or not event.possibleActions() & Qt.DropAction.CopyAction:
            event.ignore()
            return
        index = self.indexAt(event.position().toPoint())
        hover = index if index.isValid() else self.rootIndex()
        if hover != self.hover_index:
            self.hover_index = hover
            self.hover_timer.start()
        self.viewport().update()
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()

    def dragLeaveEvent(self, event):
        self.hover_timer.stop()
        self.hover_index = None
        self.viewport().update()
        event.accept()

    def dropEvent(self, event):
        self.hover_timer.stop()
        paths = self.audio_paths(event.mimeData())
        index = self.indexAt(event.position().toPoint())
        if not index.isValid():
            index = self.rootIndex()
        directory = Path(self.model().filePath(index))
        self.hover_index = None
        self.viewport().update()
        if paths and directory.is_dir() and event.possibleActions() & Qt.DropAction.CopyAction:
            self.copyRequested.emit(paths, directory)
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def paintEvent(self, event):
        super().paintEvent(event)
        root = self.rootIndex()
        if not any(not self.isRowHidden(row, root) for row in range(self.model().rowCount(root))):
            painter = QPainter(self.viewport())
            painter.setPen(QColor("#92a1b5"))
            painter.drawText(self.viewport().rect().adjusted(15, 15, -15, -15),
                             Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.empty_message)
            painter.end()
        if self.hover_index is not None and self.hover_index.isValid():
            painter = QPainter(self.viewport())
            rect = self.visualRect(self.hover_index)
            if rect.isValid():
                painter.fillRect(rect, QColor(98, 214, 191, 55))
                painter.setPen(QColor("#62d6bf"))
                painter.drawRect(rect.adjusted(1, 1, -1, -1))


class FileActions(QStyledItemDelegate):
    playRequested = Signal(object)
    editorRequested = Signal(object)

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if not index.data(Qt.ItemDataRole.UserRole):
            return
        playing = index.data(Qt.ItemDataRole.UserRole + 1) == "playing"
        unavailable = bool(index.data(Qt.ItemDataRole.UserRole + 3))
        expanded = bool(index.data(Qt.ItemDataRole.UserRole + 2))
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        rect = QRectF(option.rect)
        painter.setBrush(QColor("#202b3b" if unavailable else "#294d47"))
        painter.drawRoundedRect(QRectF(rect.left() + 6, rect.top() + 5, 32, rect.height() - 10), 5, 5)
        painter.setBrush(QColor("#304159" if expanded else "#253246"))
        editor_rect = QRectF(rect.left() + 44, rect.top() + 5, rect.width() - 50, rect.height() - 10)
        painter.drawRoundedRect(editor_rect, 5, 5)
        painter.setPen(QColor("#68788f" if unavailable else "#86e9d1"))
        painter.drawText(QRectF(rect.left() + 6, rect.top(), 32, rect.height()), Qt.AlignmentFlag.AlignCenter, "Ⅱ" if playing else "▶")
        painter.setPen(QColor("#d6e1ef"))
        painter.drawText(editor_rect, Qt.AlignmentFlag.AlignCenter, "⌃ Fechar" if expanded else "⌄ Recortar")
        painter.restore()

    def editorEvent(self, event, model, option, index):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            path = index.data(Qt.ItemDataRole.UserRole)
            if path:
                if event.position().x() - option.rect.left() < 41:
                    if not index.data(Qt.ItemDataRole.UserRole + 3):
                        self.playRequested.emit(Path(path))
                else:
                    self.editorRequested.emit(Path(path))
                return True
        return False
