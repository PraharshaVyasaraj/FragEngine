"""
FragEngine V0.17 — Interactive Match Replay Package Builder
Generates self-contained HTML/JS replay packages with interactive timelines and video scrubbing.
"""

import os
import json
import datetime
from typing import Dict, List

BASE_DIR = r"C:\FragEngine"
REPORTS_DIR = os.path.join(BASE_DIR, "reports")


class ReplayBuilder:
    def __init__(self, session_id: str = "SESSION_0001"):
        self.session_id = session_id
        self.output_dir = os.path.join(REPORTS_DIR, session_id)
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_replay_html(self, events_timeline: List[dict], leaderboard: List[dict], ruleset_name: str) -> str:
        """Generates self-contained HTML replay document."""
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.output_dir, f"match_replay_{timestamp_str}.html")

        events_json = json.dumps(events_timeline, indent=2)
        leaderboard_json = json.dumps(leaderboard, indent=2)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>FRAGENGINE V0.17 // INTERACTIVE MATCH REPLAY — {self.session_id}</title>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=Outfit:wght@600;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --red-primary: #ff2a2a;
      --bg-dark: #07080a;
      --card-bg: rgba(15, 18, 24, 0.9);
      --card-border: rgba(255, 42, 42, 0.2);
      --text-white: #ffffff;
      --text-dim: #64748b;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg-dark);
      color: var(--text-white);
      font-family: 'JetBrains Mono', monospace;
      padding: 24px;
      min-height: 100vh;
    }}
    .replay-container {{ max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }}
    header {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-top: 3px solid var(--red-primary);
      border-radius: 8px;
      padding: 16px 20px;
      display: flex; justify-content: space-between; align-items: center;
    }}
    .h-title {{ font-family: 'Outfit', sans-serif; font-size: 20px; font-weight: 800; letter-spacing: 1px; }}
    .h-title span {{ color: var(--red-primary); }}
    
    /* Interactive Timeline Bar */
    .timeline-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
    }}
    .timeline-hdr {{ font-size: 12px; font-weight: 800; color: var(--red-primary); margin-bottom: 12px; }}
    .timeline-track {{
      position: relative;
      height: 24px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 12px;
      border: 1px solid var(--card-border);
      overflow: hidden;
      cursor: pointer;
    }}
    .event-marker {{
      position: absolute;
      top: 3px;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: var(--red-primary);
      box-shadow: 0 0 8px var(--red-primary);
      cursor: pointer;
      transform: translateX(-50%);
      transition: transform 0.2s ease;
    }}
    .event-marker:hover {{ transform: translateX(-50%) scale(1.4); }}
    
    /* Event Feed List */
    .events-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
    .box {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 8px; padding: 16px; max-height: 400px; overflow-y: auto; }}
    .event-row {{ padding: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.04); font-size: 11px; display: flex; justify-content: space-between; }}
    .event-row:hover {{ background: rgba(255, 42, 42, 0.08); }}
  </style>
</head>
<body>

  <div class="replay-container">
    <header>
      <div class="h-title">FRAGENGINE <span>//</span> MATCH REPLAY PACKAGE</div>
      <div style="font-size: 11px; color: var(--text-dim);">SESSION: {self.session_id} | RULESET: {ruleset_name.upper()}</div>
    </header>

    <!-- Interactive Match Timeline Scrub Bar -->
    <div class="timeline-card">
      <div class="timeline-hdr">⏱️ INTERACTIVE MATCH TIMELINE SCRUBBER (CLICK EVENT MARKERS TO JUMP)</div>
      <div id="timelineTrack" class="timeline-track"></div>
    </div>

    <!-- Data Split View -->
    <div class="events-grid">
      <div class="box">
        <div style="font-size: 12px; font-weight: 800; color: var(--red-primary); margin-bottom: 10px;">📜 MATCH EVENTS TIMELINE</div>
        <div id="eventsContainer"></div>
      </div>
      <div class="box">
        <div style="font-size: 12px; font-weight: 800; color: var(--red-primary); margin-bottom: 10px;">🏆 FINAL MATCH LEADERBOARD</div>
        <div id="leaderboardContainer"></div>
      </div>
    </div>
  </div>

  <script>
    const eventsData = {events_json};
    const leaderboardData = {leaderboard_json};

    document.addEventListener("DOMContentLoaded", () => {{
      renderTimeline();
      renderEvents();
      renderLeaderboard();
    }});

    function renderTimeline() {{
      const track = document.getElementById("timelineTrack");
      if (!eventsData.length) return;

      const maxTime = Math.max(...eventsData.map(e => e.match_time_sec || 1));
      eventsData.forEach(evt => {{
        const posPct = ((evt.match_time_sec || 0) / maxTime) * 100;
        const marker = document.createElement("div");
        marker.className = "event-marker";
        marker.style.left = posPct + "%";
        marker.title = `${{evt.type || 'EVENT'}}: ${{evt.killer || 'T1'}} -> ${{evt.victim || 'T2'}}`;
        marker.onclick = () => alert(`Event at ${{evt.match_time_sec}}s: ${{evt.killer || 'T1'}} killed ${{evt.victim || 'T2'}} with ${{evt.weapon || 'GUN'}}`);
        track.appendChild(marker);
      }});
    }}

    function renderEvents() {{
      const container = document.getElementById("eventsContainer");
      if (!eventsData.length) {{
        container.innerHTML = '<div style="color:var(--text-dim);">No logged events in this session.</div>';
        return;
      }}
      let html = "";
      eventsData.forEach(evt => {{
        html += `
          <div class="event-row">
            <span style="color:var(--red-primary); font-weight:bold;">${{evt.match_time_sec || 0}}s</span>
            <span>${{evt.type || 'EVENT'}}</span>
            <span>${{evt.killer || 'T1'}} -> ${{evt.victim || 'T2'}}</span>
            <span style="color:var(--text-dim);">${{evt.weapon || ''}}</span>
          </div>
        `;
      }});
      container.innerHTML = html;
    }}

    function renderLeaderboard() {{
      const container = document.getElementById("leaderboardContainer");
      if (!leaderboardData.length) {{
        container.innerHTML = '<div style="color:var(--text-dim);">No leaderboard data.</div>';
        return;
      }}
      let html = "";
      leaderboardData.forEach(item => {{
        html += `
          <div class="event-row">
            <span style="font-weight:bold;">#${{String(item.current_rank).padStart(2,'0')}}</span>
            <span style="font-weight:bold; color:#fff;">${{item.team_tag}}</span>
            <span>${{item.finishes}} Finishes</span>
            <span style="color:var(--red-primary); font-weight:bold;">${{item.total_points}} PTS</span>
          </div>
        `;
      }});
      container.innerHTML = html;
    }}
  </script>
</body>
</html>
"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"[REPLAY BUILDER] Exported standalone match replay package to {output_file}")
        return output_file
