"""
FragEngine V0.16 — In-Game Transparent Overlay HUD
Always-on-top transparent HUD overlay for single-monitor spectating.
"""

import sys
import requests
import tkinter as tk

SERVER_URL = "http://127.0.0.1:5000"

class InGameOverlayHUD:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FRAGLAB // IN-GAME OVERLAY")
        self.root.geometry("360x420+20+40") # Default top-left position
        
        # Window attributes for Always-On-Top and Click-Through transparency
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.88)
        self.root.configure(bg="#0c0d10")
        self.root.overrideredirect(True) # Remove title bar borders for native overlay feel

        self.setup_ui()
        self.make_draggable()
        self.poll_telemetry()

    def setup_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg="#1a1e28", height=28)
        hdr.pack(fill=tk.X)

        title = tk.Label(
            hdr, text="((o)) FRAGLAB // LIVE TELEMETRY",
            font=("Consolas", 9, "bold"), fg="#ff2a2a", bg="#1a1e28"
        )
        title.pack(side=tk.LEFT, padx=8, pady=4)

        btn_close = tk.Label(
            hdr, text="✖", font=("Consolas", 10, "bold"),
            fg="#8b95a5", bg="#1a1e28", cursor="hand2"
        )
        btn_close.pack(side=tk.RIGHT, padx=8)
        btn_close.bind("<Button-1>", lambda e: self.root.destroy())

        # Table Container
        self.list_frame = tk.Frame(self.root, bg="#0c0d10")
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def make_draggable(self):
        """Allows spectator to click and drag the overlay to any screen position."""
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def poll_telemetry(self):
        try:
            r = requests.get(f"{SERVER_URL}/api/telemetry_state", timeout=0.4)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "success":
                    self.render_hud(data.get("leaderboard", []))
        except Exception:
            pass

        self.root.after(1000, self.poll_telemetry)

    def render_hud(self, leaderboard):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        if not leaderboard:
            lbl = tk.Label(
                self.list_frame, text="STANDBY // NO ROSTER LOADED",
                font=("Consolas", 9, "bold"), fg="#5a6478", bg="#0c0d10"
            )
            lbl.pack(pady=20)
            return

        # Header Row
        h_row = tk.Frame(self.list_frame, bg="#0c0d10")
        h_row.pack(fill=tk.X, pady=(0, 4))
        tk.Label(h_row, text="#", font=("Consolas", 8, "bold"), fg="#ff2a2a", bg="#0c0d10", width=3, anchor="w").pack(side=tk.LEFT)
        tk.Label(h_row, text="TEAM", font=("Consolas", 8, "bold"), fg="#ff2a2a", bg="#0c0d10", width=8, anchor="w").pack(side=tk.LEFT)
        tk.Label(h_row, text="STATUS", font=("Consolas", 8, "bold"), fg="#ff2a2a", bg="#0c0d10", width=12, anchor="center").pack(side=tk.LEFT)
        tk.Label(h_row, text="FIN", font=("Consolas", 8, "bold"), fg="#ff2a2a", bg="#0c0d10", width=4, anchor="e").pack(side=tk.LEFT)
        tk.Label(h_row, text="PTS", font=("Consolas", 8, "bold"), fg="#ff2a2a", bg="#0c0d10", width=5, anchor="e").pack(side=tk.LEFT)

        # Team Rows (Up to 12 visible)
        for item in leaderboard[:12]:
            row = tk.Frame(self.list_frame, bg="#121620", bd=0)
            row.pack(fill=tk.X, pady=1)

            rank_str = f"{item['current_rank']:02d}"
            r_fg = "#ffffff" if item['current_rank'] == 1 else "#8b95a5"
            tk.Label(row, text=rank_str, font=("Consolas", 9, "bold"), fg=r_fg, bg="#121620", width=3, anchor="w").pack(side=tk.LEFT)

            tag = item["team_tag"]
            tk.Label(row, text=tag, font=("Consolas", 9, "bold"), fg="#ffffff", bg="#121620", width=8, anchor="w").pack(side=tk.LEFT)

            bars = ""
            for p in item["player_states"]:
                if p == "ALIVE": bars += "🟩"
                elif p == "KNOCKED": bars += "🟥"
                else: bars += "⬜"
            tk.Label(row, text=bars, font=("Consolas", 8), fg="#ffffff", bg="#121620", width=12, anchor="center").pack(side=tk.LEFT)

            fin = str(item["finishes"])
            tk.Label(row, text=fin, font=("Consolas", 9, "bold"), fg="#ffffff", bg="#121620", width=4, anchor="e").pack(side=tk.LEFT)

            pts = str(int(item["total_points"]))
            tk.Label(row, text=pts, font=("Consolas", 9, "bold"), fg="#ff2a2a", bg="#121620", width=5, anchor="e").pack(side=tk.LEFT)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    overlay = InGameOverlayHUD()
    overlay.run()
