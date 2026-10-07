"""Consistent vector icons for the native editor toolbar."""
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

SHAPES = {
    "play": '<path d="M8 5l11 7-11 7z"/>',
    "pause": '<path d="M8 5v14M16 5v14" stroke-width="4"/>',
    "copy": '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M15 8V4H4v11h4"/>',
    "paste": '<rect x="5" y="5" width="14" height="16" rx="2"/><rect x="8" y="3" width="8" height="4" rx="1"/><path d="M9 12h6M9 16h6"/>',
    "trash": '<path d="M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7M14 10v7"/>',
    "undo": '<path d="M8 4L3 9l5 5M3 9h10a7 7 0 010 14" transform="translate(0 -2)"/>',
    "redo": '<path d="M16 4l5 5-5 5M21 9H11a7 7 0 000 14" transform="translate(0 -2)"/>',
    "reverse": '<path d="M3 7h18l-4-4M21 17H3l4 4M7 3L3 7l4 4M17 13l4 4-4 4"/>',
    "volume_down": '<path d="M11 4L6 8H3v8h3l5 4zM15 12h6"/>',
    "volume_up": '<path d="M11 4L6 8H3v8h3l5 4zM15 12h6M18 9v6"/>',
    "fade_in": '<path d="M3 4v16h18M5 17L20 5M5 5h15"/>',
    "fade_out": '<path d="M3 4v16h18M5 5l15 12M5 5h15"/>',
    "zoom_out": '<circle cx="10" cy="10" r="6"/><path d="M15 15l6 6M7 10h6"/>',
    "zoom_in": '<circle cx="10" cy="10" r="6"/><path d="M15 15l6 6M7 10h6M10 7v6"/>',
    "fit": '<path d="M3 8V3h5M16 3h5v5M21 16v5h-5M8 21H3v-5M7 12h10M7 12l3-3M7 12l3 3M17 12l-3-3M17 12l-3 3"/>',
    "select_all": '<rect x="3" y="3" width="18" height="18" rx="2" stroke-dasharray="3 3"/><path d="M7 12l3 3 7-7"/>',
    "folder": '<path d="M3 7V4h6l3 3h9v13H3zM3 10h18"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "save": '<path d="M4 3h13l3 3v15H4zM8 3v6h8V3M8 21v-8h8v8"/>',
}


def editor_icon(name: str, primary: bool = False) -> QIcon:
    icon = QIcon()
    normal_color = "#0f2627" if primary else "#ffaaa3" if name == "trash" else "#d6e1ef"
    for mode, color in ((QIcon.Mode.Normal, normal_color),
                        (QIcon.Mode.Disabled, "#68788f")):
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{SHAPES[name]}</g></svg>'
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        for scale in (1, 2):
            pixmap = QPixmap(24 * scale, 24 * scale)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            pixmap.setDevicePixelRatio(scale)
            icon.addPixmap(pixmap, mode)
    return icon
