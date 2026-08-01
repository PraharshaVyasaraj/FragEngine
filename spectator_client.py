"""
FragEngine V0.16 — Desktop Spectator Dashboard App
Standalone Tkinter/OpenCV GUI client for direct in-game custom room spectating.
"""

import os
import sys
import time
import base64
import json
import threading
import requests
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox, ttk

# Add project root to sys.path
BASE_DIR = r"C:\FragEngine"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from utils.desktop_capture import DesktopCapturer

SERVER_URL = "http://127.0.0.1:5000"

class CalibrationOverlay:
    """Full-screen transparent overlay for drag-selecting ROIs over game screen."""
    def __init__(self, parent, capturer, callback, title="SELECT KILL FEED ROI"):
        self.parent = parent
        self.capturer = capturer
        self.callback = callback
        self.title = title

        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-alpha", 0.45)
        self.top.config(cursor="crosshair", bg="#000000")

        self.canvas = tk.Canvas(self.top, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.start_x = None
        self.start_y = None
        self.rect_id = None

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        # Instructions banner
        self.lbl_instruct = tk.Label(
            self.top,
            text=f"=== {self.title} ===\nClick and drag a box over your 250% in-game scale region. Press ESC to cancel.",
            font=("Consolas", 14, "bold"),
            fg="#ff2a2a",
            bg="#0d0f14",
            padding=10
        )
        self.lbl_instruct.pack(side=tk.TOP, fill=tk.X)
        self.top.bind("<Escape>", lambda e: self.top.destroy())

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="#ff2a2a", width=3, dash=(4, 4)
        )

    def on_move_press(self, event):
        cur_x, cur_y = event.x, event.y
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x, end_y = event.x, event.y
        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        width = abs(self.start_x - end_x)
        height = abs(self.start_y - end_y)

        if width > 10 and height > 10:
            roi = {"left": left, "top": top, "width": width, "height": height}
            self.top.destroy()
            self.callback(roi)
        else:
            self.top.destroy()


class SpectatorDashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FRAGLAB // DESKTOP SPECTATOR DASHBOARD (V0.16)")
        self.root.geometry("880x680")
        self.root.configure(bg="#060709")

        self.capturer = DesktopCapturer()
        self.roi_kill_feed = None
        self.roi_alive_counter = None

        self.is_ingesting = False
        self.ingest_thread = None

        self.setup_ui()
        self.poll_server_status()

    def setup_ui(self):
        # Header Bar
        hdr_frame = tk.Frame(self.root, bg="#0d0f14", bd=1, relief=tk.SOLID)
        hdr_frame.pack(fill=tk.X, padx=14, pady=10)

        title_lbl = tk.Label(
            hdr_frame,
            text="((o)) FRAGLAB | SPECTATOR_DASHBOARD",
            font=("Consolas", 16, "bold"),
            fg="#ff2a2a",
            bg="#0d0f14"
        )
        title_lbl.pack(side=tk.LEFT, padx=12, pady=10)

        self.status_lbl = tk.Label(
            hdr_frame,
            text="● ENGINE IDLE",
            font=("Consolas", 11, "bold"),
            fg="#7a8599",
            bg="#0d0f14"
        )
        self.status_lbl.pack(side=tk.RIGHT, padx=12, pady=10)

        # Control Panel
        ctrl_frame = tk.Frame(self.root, bg="#0d0f14", bd=1, relief=tk.SOLID)
        ctrl_frame.pack(fill=tk.X, padx=14, pady=4)

        btn_style = {"font": ("Consolas", 10, "bold"), "bd": 0, "padx": 12, "pady": 6, "cursor": "hand2"}

        self.btn_cal_feed = tk.Button(
            ctrl_frame, text="🎯 1. CALIBRATE KILL FEED (250%)",
            bg="#1a1e28", fg="#ffffff", command=self.calibrate_kill_feed, **btn_style
        )
        self.btn_cal_feed.pack(side=tk.LEFT, padx=8, pady=8)

        self.btn_cal_alive = tk.Button(
            ctrl_frame, text="🎯 2. CALIBRATE ALIVE COUNTER",
            bg="#1a1e28", fg="#ffffff", command=self.calibrate_alive_counter, **btn_style
        )
        self.btn_cal_alive.pack(side=tk.LEFT, padx=8, pady=8)

        self.btn_start = tk.Button(
            ctrl_frame, text="▶️ START INGEST (250MS)",
            bg="#ff2a2a", fg="#ffffff", command=self.start_ingest, **btn_style
        )
        self.btn_start.pack(side=tk.LEFT, padx=8, pady=8)

        self.btn_stop = tk.Button(
            ctrl_frame, text="⏹️ STOP",
            bg="#333333", fg="#888888", state=tk.DISABLED, command=self.stop_ingest, **btn_style
        )
        self.btn_stop.pack(side=tk.LEFT, padx=8, pady=8)

        # Dual Canvas Previews
        preview_container = tk.Frame(self.root, bg="#060709")
        preview_container.pack(fill=tk.BOTH, expand=True, padx=14, pady=8)

        # Canvas A: Kill Feed Crop
        box_a = tk.LabelFrame(preview_container, text=" LIVE KILL FEED CROP (250% IN-GAME SCALE) ", font=("Consolas", 10, "bold"), fg="#ff2a2a", bg="#0d0f14")
        box_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        self.canvas_a = tk.Canvas(box_a, bg="#060709", highlightthickness=0)
        self.canvas_a.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Canvas B: Alive Counter Crop
        box_b = tk.LabelFrame(preview_container, text=" TEAMS ALIVE COUNTER CROP ", font=("Consolas", 10, "bold"), fg="#ff2a2a", bg="#0d0f14")
        box_b.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=4)

        self.canvas_b = tk.Canvas(box_b, bg="#060709", highlightthickness=0)
        self.canvas_b.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Stats Bar
        stats_frame = tk.Frame(self.root, bg="#0d0f14", bd=1, relief=tk.SOLID)
        stats_frame.pack(fill=tk.X, padx=14, pady=8)

        self.lbl_stats = tk.Label(
            stats_frame,
            text="FPS: 4.0 (250ms)  |  OCR Latency: - ms  |  Frames Sampled: 0  |  Server: OK",
            font=("Consolas", 10),
            fg="#5a6478",
            bg="#0d0f14"
        )
        self.lbl_stats.pack(padx=12, pady=6)

    def calibrate_kill_feed(self):
        CalibrationOverlay(self.root, self.capturer, self.on_kill_feed_calibrated, title="SELECT KILL FEED ROI (250% SCALE)")

    def on_kill_feed_calibrated(self, roi):
        self.roi_kill_feed = roi
        messagebox.showinfo("ROI Locked", f"Kill Feed ROI Locked:\nWidth: {roi['width']}px, Height: {roi['height']}px")

    def calibrate_alive_counter(self):
        CalibrationOverlay(self.root, self.capturer, self.on_alive_calibrated, title="SELECT ALIVE COUNTER ROI")

    def on_alive_calibrated(self, roi):
        self.roi_alive_counter = roi
        messagebox.showinfo("ROI Locked", f"Alive Counter ROI Locked:\nWidth: {roi['width']}px, Height: {roi['height']}px")

    def start_ingest(self):
        if not self.roi_kill_feed:
            messagebox.showwarning("Missing Calibration", "Please calibrate the Kill Feed ROI before starting ingest.")
            return

        self.is_ingesting = True
        self.btn_start.config(state=tk.DISABLED, bg="#333333")
        self.btn_stop.config(state=tk.NORMAL, bg="#ff2a2a", fg="#ffffff")
        self.status_lbl.config(text="● INGESTING (250MS FIXED RATE)", fg="#2ecc71")

        self.ingest_thread = threading.Thread(target=self.ingest_loop, daemon=True)
        self.ingest_thread.start()

    def stop_ingest(self):
        self.is_ingesting = False
        self.btn_start.config(state=tk.NORMAL, bg="#ff2a2a")
        self.btn_stop.config(state=tk.DISABLED, bg="#333333", fg="#888888")
        self.status_lbl.config(text="● INGEST PAUSED", fg="#7a8599")

    def ingest_loop(self):
        sample_count = 0
        while self.is_ingesting:
            t0 = time.perf_counter()

            # Grab Kill Feed ROI Crop
            img_crop = self.capturer.capture_roi(self.roi_kill_feed)
            if img_crop is not None:
                sample_count += 1
                # Encode base64 JPEG
                _, buffer = cv2.imencode('.jpg', img_crop, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                b64_str = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

                # Display frame on Canvas A
                self.update_canvas_image(self.canvas_a, img_crop)

                # Send frame to local server
                try:
                    res = requests.post(f"{SERVER_URL}/process", json={"image": b64_str}, timeout=0.8)
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    
                    self.root.after(0, self.update_stats, sample_count, round(elapsed_ms, 1))
                except Exception as e:
                    print(f"[Server Error] {e}")

            # Grab Alive Counter ROI Crop if calibrated
            if self.roi_alive_counter:
                img_alive = self.capturer.capture_roi(self.roi_alive_counter)
                if img_alive is not None:
                    self.update_canvas_image(self.canvas_b, img_alive)

            # Sleep to maintain fixed 250ms interval (4 FPS)
            elapsed_sec = time.perf_counter() - t0
            sleep_time = max(0.001, 0.250 - elapsed_sec)
            time.sleep(sleep_time)

    def update_canvas_image(self, canvas, cv_img):
        try:
            # Resize image to fit canvas
            cw = canvas.winfo_width()
            ch = canvas.winfo_height()
            if cw < 10 or ch < 10:
                cw, ch = 380, 240

            h, w = cv_img.shape[:2]
            scale = min(cw / w, ch / h)
            nw, nh = int(w * scale), int(h * scale)

            resized = cv2.resize(cv_img, (nw, nh), interpolation=cv2.INTER_AREA)
            rgb_img = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_img)
            tk_img = ImageTk.PhotoImage(image=pil_img)

            canvas.delete("all")
            canvas.create_image(cw // 2, ch // 2, image=tk_img, anchor=tk.CENTER)
            canvas.image = tk_img
        except Exception:
            pass

    def update_stats(self, samples, latency_ms):
        self.lbl_stats.config(
            text=f"Rate: 250ms (4.0 FPS)  |  Ingest Latency: {latency_ms}ms  |  Frames Sampled: {samples}  |  Server: 200 OK"
        )

    def poll_server_status(self):
        try:
            r = requests.get(f"{SERVER_URL}/api/telemetry_state", timeout=0.5)
            if r.status_code == 200:
                pass
        except Exception:
            self.lbl_stats.config(text="⚠️ SERVER DISCONNECTED (Start server.py on port 5000)")
        
        self.root.after(3000, self.poll_server_status)


if __name__ == "__main__":
    root = tk.Tk()
    app = SpectatorDashboardApp(root)
    root.mainloop()
