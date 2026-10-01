"""Show the real GUI with original synthetic pixels, without USB/device content."""
import argparse
from pathlib import Path
import sys

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QFont
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exword_capture.app import Window

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--language", choices=("ja", "en", "zh_CN", "zh_TW"), default="ja")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
app = QApplication([])
window = Window()
window.set_language(args.language)
image = QImage(528, 320, QImage.Format.Format_RGB888)
image.fill(QColor("#16202c"))
painter = QPainter(image)
painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
painter.setPen(QColor("#293b4d"))
for x in range(0, 528, 16):
    painter.drawLine(x, 0, x, 319)
for y in range(0, 320, 16):
    painter.drawLine(0, y, 527, y)
painter.setPen(QColor("#7dcfff"))
painter.setFont(QFont("Sans", 16))
painter.drawText(24, 50, "EX-word Screen Capture")
painter.setPen(QColor("white"))
painter.setFont(QFont("Sans", 12))
painter.drawText(24, 86, "UI確認用テスト画像")
painter.drawText(24, 114, "実機の画面・辞書コンテンツではありません")
painter.drawText(24, 150, "528 × 320 px / 整数倍・最大10倍")
for i, color in enumerate(("#ff5f56", "#ffbd2e", "#27c93f", "#4ba3ff", "#bd83ff")):
    painter.fillRect(24 + i * 96, 190, 80, 64, QColor(color))
painter.setPen(QColor("#9fb5c8"))
painter.drawText(24, 292, "ORIGINAL TEST PATTERN / NO DEVICE CONTENT")
painter.end()
window.full_image = image
window.refresh_view()
window.statusBar().showMessage(window.text("preview"))
window.show()


def save():
    window.grab().save(str(args.output / "capture-ui-window.png"))
    window.close()
    app.quit()


QTimer.singleShot(500, save)
app.exec()
