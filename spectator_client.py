"""
FragEngine V0.16 — Unified Single-Monitor In-Game Spectator Addon
PyQt5 Native Frameless Overlay with In-Memory Core Pipeline & Global Hotkeys.
"""

import os
import sys
import time
import json
import base64
import requests
import cv2
import numpy as np

# Ensure C:\FragEngine is in sys.path
BASE_DIR = r"C:\FragEngine"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from pynput import keyboard

# In-Memory Core Engines
from parser import FeedParser
from utils.state_engine import StateEngine
from utils.scoring_engine import ScoringEngine
from utils.desktop_capture import DesktopCapturer

CONFIG_PATH = os.path.join(BASE_DIR, "config", "spectator_config.json")
SERVER_URL = "http://127.0.0.1:5000"


class InteractiveCalibrationWindow(QtWidgets.QWidget):
    """Full-screen drag overlay for selecting ROIs over game screen."""
    roi_selected = pyqtSignal(dict)

    def __init__(self, title="SELECT ROI"):
        super().__init__()
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setWindowOpacity(0.55)
        self.setStyleSheet("background-color: #000000;")
        self.setCursor(Qt.CrossCursor)
        self.showFullScreen()

        self.start_pos = None
        self.end_pos = None
        self.is_drawing = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.is_drawing = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.end_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.start_pos and self.end_pos:
            self.is_drawing = False
            x = min(self.start_pos.x(), self.end_pos.x())
            y = min(self.start_pos.y(), self.end_pos.y())
            w = abs(self.start_pos.x() - self.end_pos.x())
            h = abs(self.start_pos.y() - self.end_pos.y())

            if w > 10 and h > 10:
                roi = {"left": x, "top": y, "width": w, "height": h}
                self.roi_selected.emit(roi)
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.start_pos and self.end_pos:
            painter = QtGui.QPainter(self)
            pen = QtGui.QPen(QtGui.QColor("#ff2a2a"), 3, Qt.DashLine)
            painter.setPen(pen)
            x = min(self.start_pos.x(), self.end_pos.x())
            y = min(self.start_pos.y(), self.end_pos.y())
            w = abs(self.start_pos.x() - self.end_pos.x())
            h = abs(self.start_pos.y() - self.end_pos.y())
            painter.drawRect(x, y, w, h)


class SpectatorOverlayAddon(QtWidgets.QWidget):
    """
    Unified Single-Monitor In-Game Spectator Addon Widget.
    Runs pinned always-on-top over Scarfall (250% scale).
    """

    sig_toggle_ingest = pyqtSignal()
    sig_toggle_view = pyqtSignal()
    sig_toggle_preview = pyqtSignal()
    sig_reset_match = pyqtSignal()

    def __init__(self):
        super().__init__()

        # In-Memory Core Pipeline Initialization
        self.capturer = DesktopCapturer()
        self.parser = FeedParser(os.path.join(BASE_DIR, "icons"))
        self.state_engine = StateEngine(knock_timeout_seconds=30.0)
        
        ruleset_file = os.path.join(BASE_DIR, "config", "rulesets", "bmps.json")
        self.scoring_engine = ScoringEngine(self.state_engine, ruleset_path=ruleset_file)

        # Config & State
        self.config = self.load_config()
        self.is_ingesting = False
        self.view_mode = "MINIMAL" # "MINIMAL", "FULL", "HIDDEN"
        self.show_previews = False
        self.frames_sampled = 0
        self.last_latency_ms = 0.0

        # UI Setup
        self.init_window_properties()
        self.setup_ui()

        # Connect Signals for Thread Safety
        self.sig_toggle_ingest.connect(self.toggle_ingest)
        self.sig_toggle_view.connect(self.cycle_view_mode)
        self.sig_toggle_preview.connect(self.toggle_previews)
        self.sig_reset_match.connect(self.reset_match)

        # Ingest Timer (250ms Rate)
        self.ingest_timer = QTimer()
        self.ingest_timer.setInterval(250)
        self.ingest_timer.timeout.connect(self.process_ingest_tick)

        # Start Global Hotkey Listener Thread
        self.start_hotkey_listener()

        # Initial Roster Load
        self.load_default_roster()

    def init_window_properties(self):
        self.setWindowTitle("FragEngine Spectator Addon")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(420, 160)
        self.move(20, 40) # Top-left default

        self.old_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.globalPos() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def setup_ui(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Main Card Container
        self.card = QtWidgets.QFrame(self)
        self.card.setStyleSheet("""
            QFrame {
                background-color: rgba(13, 15, 20, 0.92);
                border: 1px solid #1a1e28;
                border-top: 3px solid #ff2a2a;
                border-radius: 6px;
            }
        """)
        self.card_layout = QtWidgets.QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(10, 8, 10, 8)
        self.card_layout.setSpacing(6)

        # Header Bar & Integrated Controls
        self.hdr = QtWidgets.QHBoxLayout()
        
        self.lbl_title = QtWidgets.QLabel("((o)) FRAGLAB // SPECTATOR ADDON", self.card)
        self.lbl_title.setStyleSheet("color: #ff2a2a; font-family: 'Consolas'; font-weight: bold; font-size: 11px;")
        self.hdr.addWidget(self.lbl_title)

        self.hdr.addStretch()

        # Control Buttons
        btn_css = """
            QPushButton {
                background-color: #1a1e28;
                color: #ffffff;
                font-family: 'Consolas';
                font-size: 10px;
                font-weight: bold;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #ff2a2a; }
        """

        self.btn_ingest = QtWidgets.QPushButton("▶ START (F10)", self.card)
        self.btn_ingest.setStyleSheet(btn_css)
        self.btn_ingest.clicked.connect(self.toggle_ingest)
        self.hdr.addWidget(self.btn_ingest)

        self.btn_view = QtWidgets.QPushButton("👁 VIEW (F9)", self.card)
        self.btn_view.setStyleSheet(btn_css)
        self.btn_view.clicked.connect(self.cycle_view_mode)
        self.hdr.addWidget(self.btn_view)

        self.btn_cal = QtWidgets.QPushButton("🎯 ROI", self.card)
        self.btn_cal.setStyleSheet(btn_css)
        self.btn_cal.clicked.connect(self.start_roi_calibration)
        self.hdr.addWidget(self.btn_cal)

        self.btn_rst = QtWidgets.QPushButton("🔄 RESET (F11)", self.card)
        self.btn_rst.setStyleSheet(btn_css)
        self.btn_rst.clicked.connect(self.reset_match)
        self.hdr.addWidget(self.btn_rst)

        self.card_layout.addLayout(self.hdr)

        # View Mode 1: Minimal Floating Bar
        self.minimal_widget = QtWidgets.QWidget(self.card)
        self.minimal_layout = QtWidgets.QHBoxLayout(self.minimal_widget)
        self.minimal_layout.setContentsMargins(4, 4, 4, 4)

        self.lbl_minimal_status = QtWidgets.QLabel("STANDBY // PRESS F10 TO INGEST", self.minimal_widget)
        self.lbl_minimal_status.setStyleSheet("color: #7a8599; font-family: 'Consolas'; font-size: 11px; font-weight: bold;")
        self.minimal_layout.addWidget(self.lbl_minimal_status)

        self.card_layout.addWidget(self.minimal_widget)

        # View Mode 2: Full 16-Team Leaderboard Matrix
        self.matrix_widget = QtWidgets.QWidget(self.card)
        self.matrix_layout = QtWidgets.QVBoxLayout(self.matrix_widget)
        self.matrix_layout.setContentsMargins(0, 0, 0, 0)
        self.matrix_layout.setSpacing(2)

        self.matrix_table = QtWidgets.QTableWidget(self.matrix_widget)
        self.matrix_table.setColumnCount(5)
        self.matrix_table.setHorizontalHeaderLabels(["#", "TEAM", "STATUS", "FIN", "PTS"])
        self.matrix_table.verticalHeader().setVisible(False)
        self.matrix_table.setShowGrid(False)
        self.matrix_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.matrix_table.setStyleSheet("""
            QTableWidget {
                background-color: #0d0f14;
                color: #ffffff;
                font-family: 'Consolas';
                font-size: 10px;
                border: none;
            }
            QHeaderView::section {
                background-color: rgba(255, 42, 42, 0.1);
                color: #ff2a2a;
                font-family: 'Consolas';
                font-weight: bold;
                font-size: 10px;
                border: none;
                padding: 4px;
            }
        """)
        self.matrix_table.setColumnWidth(0, 30)
        self.matrix_table.setColumnWidth(1, 80)
        self.matrix_table.setColumnWidth(2, 130)
        self.matrix_table.setColumnWidth(3, 40)
        self.matrix_table.setColumnWidth(4, 50)

        self.matrix_layout.addWidget(self.matrix_table)
        self.card_layout.addWidget(self.matrix_widget)
        self.matrix_widget.hide() # Hidden by default

        # View Mode 3: Live Crop Preview Drawer (F8)
        self.preview_widget = QtWidgets.QWidget(self.card)
        self.preview_layout = QtWidgets.QHBoxLayout(self.preview_widget)
        self.preview_layout.setContentsMargins(2, 2, 2, 2)

        self.lbl_preview_a = QtWidgets.QLabel("KILL FEED CROP", self.preview_widget)
        self.lbl_preview_a.setAlignment(Qt.AlignCenter)
        self.lbl_preview_a.setStyleSheet("background-color: #000; border: 1px solid #1a1e28; color: #5a6478; font-family: 'Consolas'; font-size: 9px;")
        self.lbl_preview_a.setFixedHeight(70)

        self.lbl_preview_b = QtWidgets.QLabel("ALIVE COUNTER", self.preview_widget)
        self.lbl_preview_b.setAlignment(Qt.AlignCenter)
        self.lbl_preview_b.setStyleSheet("background-color: #000; border: 1px solid #1a1e28; color: #5a6478; font-family: 'Consolas'; font-size: 9px;")
        self.lbl_preview_b.setFixedHeight(70)

        self.preview_layout.addWidget(self.lbl_preview_a)
        self.preview_layout.addWidget(self.lbl_preview_b)

        self.card_layout.addWidget(self.preview_widget)
        self.preview_widget.hide()

        # Footer Stats Label
        self.lbl_footer = QtWidgets.QLabel("Rate: 250ms (4 FPS)  |  Latency: - ms  |  Samples: 0", self.card)
        self.lbl_footer.setStyleSheet("color: #5a6478; font-family: 'Consolas'; font-size: 9px;")
        self.card_layout.addWidget(self.lbl_footer)

        self.main_layout.addWidget(self.card)

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"sampling_interval_ms": 250, "roi_kill_feed": None, "roi_alive_counter": None}

    def save_config(self):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)

    def load_default_roster(self):
        roster_payload = [
            { "tag": "PLTN",   "name": "Peloton",         "players": ["P1", "P2", "P3", "P4"] },
            { "tag": "CPTN",   "name": "Captains",        "players": ["C1", "C2", "C3", "C4"] },
            { "tag": "SC",     "name": "Shadow Clan",     "players": ["S1", "S2", "S3", "S4"] },
            { "tag": "OCN",    "name": "Ocean Esports",   "players": ["O1", "O2", "O3", "O4"] },
            { "tag": "6SENSE", "name": "Sixth Sense",     "players": ["61", "62", "63", "64"] },
            { "tag": "STAR",   "name": "Star Alliance",   "players": ["St1", "St2", "St3", "St4"] },
            { "tag": "RS",     "name": "Rising Stars",    "players": ["R1", "R2", "R3", "R4"] },
            { "tag": "XBUG",   "name": "X-Bugs",          "players": ["X1", "X2", "X3", "X4"] },
            { "tag": "KyZN",   "name": "KyZN Esports",    "players": ["EviLKiOz", "Shadow", "Viper", "Apex"] },
            { "tag": "FLCN",   "name": "Falcon Squad",    "players": ["PRADIP", "Hawk", "Falcon1", "Blaze"] },
            { "tag": "TxL",    "name": "TxL Clan",        "players": ["CLUSTER", "Striker", "Ghost", "Raven"] },
            { "tag": "Tr",     "name": "Team Tr",          "players": ["CHAMP-08", "Nitro", "Venom", "Storm"] }
        ]
        self.state_engine.load_roster(roster_payload)
        self.scoring_engine.recalculate_all()

    def start_roi_calibration(self):
        self.cal_win_feed = InteractiveCalibrationWindow("SELECT KILL FEED ROI (250% SCALE)")
        self.cal_win_feed.roi_selected.connect(self.on_kill_feed_roi_selected)

    def on_kill_feed_roi_selected(self, roi):
        self.config["roi_kill_feed"] = roi
        self.save_config()

        # Prompt for optional alive counter ROI
        reply = QtWidgets.QMessageBox.question(
            self, "Calibrate Alive Counter",
            "Kill Feed ROI saved!\nDo you also want to calibrate the Teams Alive Counter ROI?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.cal_win_alive = InteractiveCalibrationWindow("SELECT TEAMS ALIVE COUNTER ROI")
            self.cal_win_alive.roi_selected.connect(self.on_alive_roi_selected)

    def on_alive_roi_selected(self, roi):
        self.config["roi_alive_counter"] = roi
        self.save_config()
        QtWidgets.QMessageBox.information(self, "ROI Locked", "All ROIs calibrated and saved to config!")

    def toggle_ingest(self):
        if self.is_ingesting:
            self.is_ingesting = False
            self.ingest_timer.stop()
            self.btn_ingest.setText("▶ START (F10)")
            self.btn_ingest.setStyleSheet("background-color: #1a1e28; color: #ffffff;")
            self.lbl_minimal_status.setText("INGEST PAUSED")
            self.lbl_minimal_status.setStyleSheet("color: #7a8599; font-weight: bold;")
        else:
            if not self.config.get("roi_kill_feed"):
                QtWidgets.QMessageBox.warning(self, "Missing Calibration", "Please click '🎯 ROI' to calibrate the 250% kill feed region.")
                return
            self.is_ingesting = True
            self.ingest_timer.start()
            self.btn_ingest.setText("⏸ PAUSE (F10)")
            self.btn_ingest.setStyleSheet("background-color: #ff2a2a; color: #ffffff;")
            self.lbl_minimal_status.setText("INGESTING (250MS / 4 FPS)")
            self.lbl_minimal_status.setStyleSheet("color: #2ecc71; font-weight: bold;")

    def cycle_view_mode(self):
        if self.view_mode == "MINIMAL":
            self.view_mode = "FULL"
            self.minimal_widget.hide()
            self.matrix_widget.show()
            self.resize(420, 420)
        elif self.view_mode == "FULL":
            self.view_mode = "HIDDEN"
            self.hide()
        else: # "HIDDEN"
            self.view_mode = "MINIMAL"
            self.matrix_widget.hide()
            self.minimal_widget.show()
            self.resize(420, 160)
            self.show()

    def toggle_previews(self):
        self.show_previews = not self.show_previews
        if self.show_previews:
            self.preview_widget.show()
        else:
            self.preview_widget.hide()

    def reset_match(self):
        self.state_engine = StateEngine(knock_timeout_seconds=30.0)
        self.scoring_engine = ScoringEngine(self.state_engine, ruleset_path=os.path.join(BASE_DIR, "config", "rulesets", "bmps.json"))
        self.load_default_roster()
        self.frames_sampled = 0
        self.update_leaderboard_display()
        self.lbl_minimal_status.setText("MATCH RESET // ENGINE READY")

    def process_ingest_tick(self):
        if not self.is_ingesting or not self.config.get("roi_kill_feed"):
            return

        t0 = time.perf_counter()
        img_crop = self.capturer.capture_roi(self.config["roi_kill_feed"])
        if img_crop is None:
            return

        self.frames_sampled += 1

        # Direct 1x Raw OCR (No upscaling needed at 250% scale)
        res = self.parser.process_frame(img_crop)

        if res and res.get("status") in ["logged", "duplicate", "recognized"]:
            # Process StateEngine in-memory
            action_state = "FINISH"
            if res.get("i2") == "KNOCK":
                action_state = "KNOCK"
            elif res.get("i1") in ["ZONE", "FALL", "DROWN"]:
                action_state = f"{res.get('i1')}_FINISH"

            try:
                self.state_engine.process_event({
                    "layout": res.get("layout"),
                    "t1": res.get("t1"),
                    "t2": res.get("t2"),
                    "action": action_state,
                    "timestamp": time.time()
                })
            except Exception as e:
                pass

            if res.get("status") == "logged":
                self.lbl_minimal_status.setText(f"EVENT: {res.get('t1')} -> {res.get('t2')}")
                self.lbl_minimal_status.setStyleSheet("color: #ff2a2a; font-weight: bold;")

        # Render Crop Previews if drawer open
        if self.show_previews and img_crop is not None:
            self.render_cv_to_qlabel(self.lbl_preview_a, img_crop)

            if self.config.get("roi_alive_counter"):
                img_alive = self.capturer.capture_roi(self.config["roi_alive_counter"])
                if img_alive is not None:
                    self.render_cv_to_qlabel(self.lbl_preview_b, img_alive)

        self.last_latency_ms = (time.perf_counter() - t0) * 1000
        self.lbl_footer.setText(f"Rate: 250ms (4 FPS)  |  Latency: {self.last_latency_ms:.1f}ms  |  Samples: {self.frames_sampled}")
        self.update_leaderboard_display()

        # Asynchronously sync to local Flask server for OBS Browser Sources
        self.sync_local_flask_server()

    def render_cv_to_qlabel(self, label, cv_img):
        try:
            h, w = cv_img.shape[:2]
            rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            qimg = QtGui.QImage(rgb.data, w, h, w * 3, QtGui.QImage.Format_RGB888)
            pix = QtGui.QPixmap.fromImage(qimg).scaled(label.width(), label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pix)
        except Exception:
            pass

    def update_leaderboard_display(self):
        leaderboard = self.scoring_engine.get_leaderboard()
        self.matrix_table.setRowCount(len(leaderboard))

        for row, item in enumerate(leaderboard):
            rank_item = QtWidgets.QTableWidgetItem(f"#{item['current_rank']:02d}")
            rank_item.setTextAlignment(Qt.AlignCenter)
            if item['current_rank'] == 1:
                rank_item.setForeground(QtGui.QColor("#ffffff"))

            tag_item = QtWidgets.QTableWidgetItem(item["team_tag"])

            bars = ""
            for p in item["player_states"]:
                if p == "ALIVE": bars += "🟩"
                elif p == "KNOCKED": bars += "🟥"
                else: bars += "⬜"
            status_item = QtWidgets.QTableWidgetItem(bars)
            status_item.setTextAlignment(Qt.AlignCenter)

            fin_item = QtWidgets.QTableWidgetItem(str(item["finishes"]))
            fin_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            pts_item = QtWidgets.QTableWidgetItem(str(int(item["total_points"])))
            pts_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            pts_item.setForeground(QtGui.QColor("#ff2a2a"))

            self.matrix_table.setItem(row, 0, rank_item)
            self.matrix_table.setItem(row, 1, tag_item)
            self.matrix_table.setItem(row, 2, status_item)
            self.matrix_table.setItem(row, 3, fin_item)
            self.matrix_table.setItem(row, 4, pts_item)

    def sync_local_flask_server(self):
        try:
            requests.post(f"{SERVER_URL}/api/roster", json={"teams": list(self.state_engine.roster.values())}, timeout=0.1)
        except Exception:
            pass

    def start_hotkey_listener(self):
        def on_press(key):
            try:
                if key == keyboard.Key.f8:
                    self.sig_toggle_preview.emit()
                elif key == keyboard.Key.f9:
                    self.sig_toggle_view.emit()
                elif key == keyboard.Key.f10:
                    self.sig_toggle_ingest.emit()
                elif key == keyboard.Key.f11:
                    self.sig_reset_match.emit()
            except Exception:
                pass

        self.hotkey_thread = threading.Thread(target=lambda: keyboard.Listener(on_press=on_press).run(), daemon=True)
        self.hotkey_thread.start()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    addon = SpectatorOverlayAddon()
    addon.show()
    sys.exit(app.exec_())
