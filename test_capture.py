import time
import json
import mss
import numpy as np
import cv2
import pytesseract
import os
import sys
from tracker import ExpTracker
from PyQt6.QtWidgets import QApplication
from overlay import Overlay


# --- TESSERACT PATH SETUP (same logic you used before) ---
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)

tesseract_path = os.path.join(base_path, "Tesseract-OCR", "tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = tesseract_path


# --- LOAD REGION ---
with open("config.json") as f:
    region_data = json.load(f)

capture_region = {
    "left": region_data["x"],
    "top": region_data["y"],
    "width": region_data["width"],
    "height": region_data["height"]
}


def extract_exp(image):
    img = np.array(image)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.convertScaleAbs(gray, alpha=1.8, beta=0)


    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)


    config = "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789,"
    text = pytesseract.image_to_string(thresh, config=config)

    cleaned = text.strip().replace(",", "")
    digits = ''.join(filter(str.isdigit, cleaned))

    return int(digits) if digits else None


if __name__ == "__main__":
    app = QApplication(sys.argv)

    overlay = Overlay()
    overlay.show()

    print("Overlay running...")

    tracker = ExpTracker()

    with mss.mss() as sct:
        while True:
            screenshot = sct.grab(capture_region)

            exp_value = extract_exp(screenshot)

            if exp_value is not None:

                # 🔒 Ignore bad OCR reads that go backwards
                if tracker.history and exp_value < tracker.history[-1][1]:
                    continue

                tracker.add(exp_value)

                gained_10 = tracker.exp_last_10_min()
                per_hour = tracker.exp_per_hour_estimate()
                session_total = tracker.session_total()

                overlay.update_stats(exp_value, gained_10, per_hour, session_total)

            app.processEvents()
            time.sleep(3)