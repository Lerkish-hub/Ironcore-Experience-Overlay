import sys
import json
import os
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QPen, QColor

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)

CONFIG_PATH = os.path.join(base_path, "config.json")


class RegionSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.chosen_region = None
        self._loop = None

        self.setWindowTitle("Select EXP Region")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.showFullScreen()
        self.setWindowOpacity(0.05)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

    def mousePressEvent(self, event):
        self.start_point = event.position().toPoint()
        self.end_point = self.start_point
        self.update()

    def mouseMoveEvent(self, event):
        self.end_point = event.position().toPoint()
        self.update()

    def mouseReleaseEvent(self, event):
        self.end_point = event.position().toPoint()
        self._finalize_region()
        self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Instruction text
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(20, 40, "Drag to select EXP area | Press ESC to cancel")

        if not self.start_point.isNull() and not self.end_point.isNull():
            rect = QRect(self.start_point, self.end_point)

            # Dark translucent fill for light backgrounds
            painter.setBrush(QColor(0, 0, 0, 120))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(rect)

            # Solid white outline
            pen = QPen(QColor(255, 255, 255), 3, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.chosen_region = None
            self.close()

    def _finalize_region(self):
        x1 = min(self.start_point.x(), self.end_point.x())
        y1 = min(self.start_point.y(), self.end_point.y())
        x2 = max(self.start_point.x(), self.end_point.x())
        y2 = max(self.start_point.y(), self.end_point.y())
        w = x2 - x1
        h = y2 - y1
        if w <= 3 or h <= 3:
            self.chosen_region = None
            return
        self.chosen_region = {"x": x1, "y": y1, "width": w, "height": h}
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(self.chosen_region, f, indent=4)
        except Exception as e:
            print("Failed to save config:", e)

    def closeEvent(self, event):
        super().closeEvent(event)
        # If a local event loop was attached, quit it so select_region can return
        if getattr(self, "_loop", None) is not None:
            try:
                self._loop.quit()
            except Exception:
                pass


def select_region() -> dict | None:
    from PyQt6.QtCore import QEventLoop
    app = QApplication.instance() or QApplication(sys.argv)
    app_running = QApplication.instance() is not None

    selector = RegionSelector()
    selector.show()

    if app_running:
        # prevent QApplication from quitting when selector closes
        prev = app.quitOnLastWindowClosed()
        app.setQuitOnLastWindowClosed(False)

        loop = QEventLoop()
        selector._loop = loop
        selector.destroyed.connect(loop.quit)
        loop.exec()

        # restore previous behavior
        app.setQuitOnLastWindowClosed(prev)
    else:
        app.exec()

    return selector.chosen_region


if __name__ == "__main__":
    region = select_region()
    print("Selected:", region)
