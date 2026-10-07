from pathlib import Path
import sys

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QPainter, QColor, QPen
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
image = QImage(256, 256, QImage.Format.Format_ARGB32)
image.fill(Qt.GlobalColor.transparent)
painter = QPainter(image)
painter.setRenderHint(QPainter.RenderHint.Antialiasing)
painter.setPen(QPen(QColor("#314454"), 5))
painter.setBrush(QColor("#152333"))
painter.drawRoundedRect(QRectF(8, 8, 240, 240), 54, 54)
painter.setPen(Qt.PenStyle.NoPen)
painter.setBrush(QColor("#62d6bf"))
for x, height in [(48, 52), (76, 98), (104, 156), (132, 112), (160, 72), (188, 38)]:
    painter.drawRoundedRect(QRectF(x, 128 - height / 2, 18, height), 9, 9)
painter.end()
root = Path(__file__).resolve().parents[1] / "assets"
root.mkdir(exist_ok=True)
assert image.save(str(root / "sound-manager.png"))
assert image.save(str(root / "sound-manager.ico"), "ICO")
print("Icon created.")
