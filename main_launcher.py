import sys
import os
import json
import time
import threading
import queue

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction, QIcon

# GUI / app modules
from region_selector import select_region
from overlay import Overlay
from tracker import ExpTracker

# OCR libs
import pytesseract
from PIL import Image, ImageOps
import mss

# Base path resolution (works when frozen)
if getattr(sys, "frozen", False):
    BASE_PATH = sys._MEIPASS
else:
    BASE_PATH = os.path.dirname(__file__)

TESSERACT_EXE = os.path.join(BASE_PATH, "Tesseract-OCR", "tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE

# Locations
CONFIG_PATH = os.path.join(BASE_PATH, "config.json")
OVERLAY_POS_PATH = os.path.join(BASE_PATH, "overlay_position.json")

# OCR worker settings
POLL_INTERVAL = 0.9  # seconds between captures
OCR_PSM_CONFIG = r'--psm 7 -c tessedit_char_whitelist=0123456789,.'


def load_region():
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
            return cfg
    except Exception:
        return None


def preprocess_image(img: Image.Image) -> Image.Image:
    img = ImageOps.grayscale(img)
    img = img.point(lambda p: 0 if p < 150 else 255)
    return img


def ocr_worker(stop_event: threading.Event, out_queue: "queue.Queue[int]"):
    with mss.mss() as sct:
        while not stop_event.is_set():
            region = load_region()
            if not region:
                time.sleep(1.0)
                continue

            try:
                bbox = {
                    "left": int(region["x"]),
                    "top": int(region["y"]),
                    "width": int(region["width"]),
                    "height": int(region["height"]),
                }
            except Exception:
                time.sleep(1.0)
                continue

            try:
                sct_img = sct.grab(bbox)
                img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
                img = preprocess_image(img)
                raw = pytesseract.image_to_string(img, config=OCR_PSM_CONFIG)
                filtered = "".join(ch for ch in raw if ch.isdigit())
                if filtered:
                    exp_val = int(filtered)
                    out_queue.put(exp_val)
            except Exception:
                pass

            for _ in range(int(POLL_INTERVAL / 0.1)):
                if stop_event.is_set():
                    break
                time.sleep(0.1)


def main():
    q = queue.Queue()
    stop_event = threading.Event()
    worker = threading.Thread(target=ocr_worker, args=(stop_event, q), daemon=True)
    worker.start()

    app = QApplication.instance() or QApplication(sys.argv)

    # Always ask user to select region on startup (overwrites existing config)
    selected = select_region()
    if not selected:
        print("No region selected; exiting.")
        stop_event.set()
        worker.join(timeout=1.0)
        return

    tracker = ExpTracker()
    overlay = Overlay()
    overlay.reset_session_callback = tracker.reset_session
    overlay.show()

    def poll_queue_and_update():
        while not q.empty():
            try:
                val = q.get_nowait()
            except queue.Empty:
                break
            tracker.add(val)

        overlay.update_stats(
            exp=tracker.session_current or 0,
            gained_10=tracker.exp_last_10_min(),
            per_hour=tracker.exp_per_hour_estimate(),
            session_total=tracker.session_total(),
        )
        overlay.update()

    timer = QTimer()
    timer.timeout.connect(poll_queue_and_update)
    timer.start(800)

    def on_exit():
        stop_event.set()
        worker.join(timeout=2.0)

    app.aboutToQuit.connect(on_exit)

    exit_code = app.exec()
    on_exit()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
