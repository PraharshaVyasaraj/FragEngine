"""
FragEngine V0.16 — Desktop Spectator Command Center
Full Standalone GUI Control Hub for Direct In-Game Custom Room Spectating.
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


class CommandCenterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FRAGLAB // DESKTOP COMMAND CONTROL CENTER (V0.16)")
        self.root.geometry("1180x760")
        self.root.configure(bg="#060709")

        self.capturer = DesktopCapturer()
        self.roi_kill_feed = None
        self.roi_alive_counter = None

        self.is_ingesting = False
        self.ingest_thread = None

        self.setup_ui()
        self.poll_server_state()

    def setup_ui(self):
        # Header Bar
        hdr_frame = tk.Frame(self.root, bg="#0d0f14", bd=1, relief=tk.SOLID)
        hdr_frame.pack(fill=tk.X, padx=14, pady=10)

        title_lbl = tk.Label(
            hdr_frame,
            text="((o)) FRAGLAB | COMMAND_CONTROL_CENTER",
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

        # Main Split Frame: Left Controls & Previews | Right Live Leaderboard
        main_split = tk.Frame(self.root, bg="#060709")
        main_split.pack(fill=tk.BOTH, expand=True, padx=14, pady=4)

        # Left Column: Control Panel & Dual Canvas Previews
        left_col = tk.Frame(main_split, bg="#060709", width=540)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        # Control Panel Box
        ctrl_box = tk.LabelFrame(left_col, text=" ENGINE COMMAND CONTROLS ", font=("Consolas", 10, "bold"), fg="#ff2a2a", bg="#0d0f14")
        ctrl_box.pack(fill=tk.X, pady=(0, 8))

        btn_style = {"font": ("Consolas", 9, "bold"), "bd": 0, "padx": 10, "pady": 6, "cursor": "hand2"}

        btn_row1 = tk.Frame(ctrl_box, bg="#0d0f14")
        btn_row1.pack(fill=tk.X, padx=6, pady=4)

        self.btn_cal_feed = tk.Button(
            btn_row1, text="🎯 1. CALIBRATE KILL FEED (250%)",
            bg="#1a1e28", fg="#ffffff", command=self.calibrate_kill_feed, **btn_style
        )
        self.btn_cal_feed.pack(side=tk.LEFT, padx=4)

        self.btn_cal_alive = tk.Button(
            btn_row1, text="🎯 2. CALIBRATE ALIVE COUNTER",
            bg="#1a1e28", fg="#ffffff", command=self.calibrate_alive_counter, **btn_style
        )
        self.btn_cal_alive.pack(side=tk.LEFT, padx=4)

        btn_row2 = tk.Frame(ctrl_box, bg="#0d0f14")
        btn_row2.pack(fill=tk.X, padx=6, pady=6)

        self.btn_start = tk.Button(
            btn_row2, text="▶️ START INGEST (250MS)",
            bg="#ff2a2a", fg="#ffffff", command=self.start_ingest, **btn_style
        )
        self.btn_start.pack(side=tk.LEFT, padx=4)

        self.btn_stop = tk.Button(
            btn_row2, text="⏹️ STOP",
            bg="#333333", fg="#888888", state=tk.DISABLED, command=self.stop_ingest, **btn_style
        )
        self.btn_stop.pack(side=tk.LEFT, padx=4)

        self.btn_roster = tk.Button(
            btn_row2, text="📋 LOAD SCARFALL ROSTER",
            bg="#d35400", fg="#ffffff", command=self.load_scarfall_roster, **btn_style
        )
        self.btn_roster.pack(side=tk.LEFT, padx=4)

        self.btn_overlay = tk.Button(
            btn_row2, text="📺 IN-GAME OVERLAY HUD",
            bg="#008080", fg="#ffffff", command=self.launch_in_game_overlay, **btn_style
        )
        self.btn_overlay.pack(side=tk.LEFT, padx=4)

        # Dual Canvas Previews
        preview_box = tk.LabelFrame(left_col, text=" LIVE INGEST FRAME PREVIEWS ", font=("Consolas", 10, "bold"), fg="#ff2a2a", bg="#0d0f14")
        preview_box.pack(fill=tk.BOTH, expand=True)

        canv_row = tk.Frame(preview_box, bg="#0d0f14")
        canv_row.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Canvas A
        box_a = tk.Frame(canv_row, bg="#060709")
        box_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        tk.Label(box_a, text="KILL FEED CROP (250% SCALE)", font=("Consolas", 8, "bold"), fg="#5a6478", bg="#060709").pack()
        self.canvas_a = tk.Canvas(box_a, bg="#000000", highlightthickness=0)
        self.canvas_a.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Canvas B
        box_b = tk.Frame(canv_row, bg="#060709")
        box_b.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=2)
        tk.Label(box_b, text="TEAMS ALIVE COUNTER CROP", font=("Consolas", 8, "bold"), fg="#5a6478", bg="#060709").pack()
        self.canvas_b = tk.Canvas(box_b, bg="#000000", highlightthickness=0)
        self.canvas_b.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Right Column: Live Leaderboard Telemetry Grid
        right_col = tk.LabelFrame(main_split, text=" LIVE TELEMETRY LEADERBOARD ", font=("Consolas", 10, "bold"), fg="#ff2a2a", bg="#0d0f14")
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        # Table Treeview
        tree_style = ttk.Style()
        tree_style.theme_use("clamp")
        tree_style.configure("Treeview", background="#0d0f14", foreground="#ffffff", fieldbackground="#0d0f14", rowheight=26, font=("Consolas", 9))
        tree_style.configure("Treeview.Heading", background="#1a1e28", foreground="#ff2a2a", font=("Consolas", 9, "bold"))
        tree_style.map("Treeview", background=[("selected", "#ff2a2a")])

        cols = ("#", "TEAM", "STATUS", "FIN", "PTS")
        self.tree = ttk.Treeview(right_col, columns=cols, show="headings", selectmode="none")
        
        self.tree.heading("#", text="#")
        self.tree.heading("TEAM", text="TEAM TAG")
        self.tree.heading("STATUS", text="PLAYER STATUS (4-BAR)")
        self.tree.heading("FIN", text="FIN")
        self.tree.heading("PTS", text="PTS")

        self.tree.column("#", width=32, anchor="center")
        self.tree.column("TEAM", width=90, anchor="w")
        self.tree.column("STATUS", width=140, anchor="center")
        self.tree.column("FIN", width=50, anchor="e")
        self.tree.column("PTS", width=60, anchor="e")

        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Bottom Stats Bar
        stats_frame = tk.Frame(self.root, bg="#0d0f14", bd=1, relief=tk.SOLID)
        stats_frame.pack(fill=tk.X, padx=14, pady=8)

        self.lbl_stats = tk.Label(
            stats_frame,
            text="Rate: 250ms (4.0 FPS)  |  Ingest Latency: - ms  |  Frames Sampled: 0  |  Server: 200 OK",
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

    def launch_in_game_overlay(self):
        import subprocess
        python_exe = sys.executable
        overlay_script = os.path.join(BASE_DIR, "utils", "overlay_hud.py")
        subprocess.Popen([python_exe, overlay_script])

    def ingest_loop(self):
        sample_count = 0
        while self.is_ingesting:
            t0 = time.perf_counter()

            # Grab Kill Feed ROI Crop
            img_crop = self.capturer.capture_roi(self.roi_kill_feed)
            if img_crop is not None:
                sample_count += 1
                _, buffer = cv2.imencode('.jpg', img_crop, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                b64_str = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

                self.update_canvas_image(self.canvas_a, img_crop)

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

            elapsed_sec = time.perf_counter() - t0
            sleep_time = max(0.001, 0.250 - elapsed_sec)
            time.sleep(sleep_time)

    def load_scarfall_roster(self):
        roster_payload = {
          "teams": [
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
        }
        try:
            r = requests.post(f"{SERVER_URL}/api/roster", json=roster_payload, timeout=1.0)
            if r.status_code == 200:
                messagebox.showinfo("Roster Ingested", "Loaded 12 Scarfall Baseline Teams into Engine!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect to server: {e}")

    def update_canvas_image(self, canvas, cv_img):
        try:
            cw = canvas.winfo_width()
            ch = canvas.winfo_height()
            if cw < 10 or ch < 10:
                cw, ch = 240, 160

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

    def poll_server_state(self):
        try:
            r = requests.get(f"{SERVER_URL}/api/telemetry_state", timeout=0.5)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "success":
                    self.render_leaderboard_tree(data.get("leaderboard", []))
        except Exception:
            pass
        
        self.root.after(1000, self.poll_server_state)

    def render_leaderboard_tree(self, leaderboard):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for item in leaderboard:
            rank_str = f"#{item['current_rank']}"
            tag = item["team_tag"]
            
            bars = ""
            for p in item["player_states"]:
                if p == "ALIVE": bars += "🟩"
                elif p == "KNOCKED": bars += "🟥"
                else: bars += "⬜"

            fin = item["finishes"]
            pts = item["total_points"]
            self.tree.insert("", tk.END, values=(rank_str, tag, bars, fin, pts))


if __name__ == "__main__":
    root = tk.Tk()
    app = CommandCenterApp(root)
    root.mainloop()
