/**
 * FragEngine V0.16.1 — Smart Roundabout Orbital App Dock
 * Interactive circular orbital dock UI for live esports telemetry, controls, and analytics.
 */

(function () {
  if (document.getElementById("fragengine-roundabout-root")) {
    return; // Already injected
  }

  const SERVER_URL = "http://127.0.0.1:5000";
  let activeCardId = null;

  // Root Container
  const root = document.createElement("div");
  root.id = "fragengine-roundabout-root";

  root.innerHTML = `
    <!-- Core Hub -->
    <div id="fr-core-hub" class="fr-roundabout-core" title="Click to Expand Smart Roundabout App Dock">
      <div class="fr-roundabout-core-ring"></div>
      <div class="fr-core-icon">🔴</div>
    </div>

    <!-- Orbital Pod Ring (360-degree Radial Menu) -->
    <div id="fr-orbit-ring" class="fr-roundabout-orbit">
      
      <!-- Pod 1: Live Leaderboard HUD -->
      <div class="fr-orbital-pod" data-target="card-leaderboard" style="transform: translate(0px, -70px);">
        📊
        <div class="fr-pod-tooltip">LEADERBOARD</div>
      </div>

      <!-- Pod 2: Ingest Controls -->
      <div class="fr-orbital-pod" data-target="card-controls" style="transform: translate(70px, 0px);">
        ⚡
        <div class="fr-pod-tooltip">CONTROLS</div>
      </div>

      <!-- Pod 3: Analytics Exporter -->
      <div class="fr-orbital-pod" data-target="card-analytics" style="transform: translate(0px, 70px);">
        📥
        <div class="fr-pod-tooltip">ANALYTICS</div>
      </div>

      <!-- Pod 4: System Telemetry SLA -->
      <div class="fr-orbital-pod" data-target="card-telemetry" style="transform: translate(-70px, 0px);">
        ⏱️
        <div class="fr-pod-tooltip">TELEMETRY</div>
      </div>

    </div>

    <!-- Roundabout App Cards -->

    <!-- Card 1: Leaderboard -->
    <div id="card-leaderboard" class="fr-roundabout-card">
      <div class="fr-card-hdr">
        <span>((o)) FRAGLAB // LIVE TELEMETRY</span>
        <button class="fr-close-card" style="background:none; border:none; color:#ff2a2a; cursor:pointer; font-weight:bold;">✕</button>
      </div>
      <div style="max-height: 280px; overflow-y: auto;">
        <div style="display: flex; justify-content: space-between; padding: 4px 6px; font-size: 10px; color: #ff2a2a; font-weight: 800; border-bottom: 1px solid rgba(255,42,42,0.25); background: rgba(255,42,42,0.08);">
          <span style="width: 24px;">#</span>
          <span style="width: 80px;">TEAM</span>
          <span style="width: 90px; text-align: center;">STATUS (4-BAR)</span>
          <span style="width: 36px; text-align: right;">FIN</span>
          <span style="width: 44px; text-align: right;">PTS</span>
        </div>
        <div id="fr-rows-container" style="margin-top: 4px;">
          <div style="text-align: center; color: #7a8599; padding: 12px; font-size: 10px;">STANDBY // WAITING FOR TELEMETRY...</div>
        </div>
      </div>
    </div>

    <!-- Card 2: Controls -->
    <div id="card-controls" class="fr-roundabout-card">
      <div class="fr-card-hdr">
        <span>⚡ INGEST CONTROL POD</span>
        <button class="fr-close-card" style="background:none; border:none; color:#ff2a2a; cursor:pointer; font-weight:bold;">✕</button>
      </div>
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <div style="display: flex; gap: 6px;">
          <button id="fr-btn-calibrate" style="flex:1; background: rgba(255,42,42,0.1); color:#fff; border:1px solid rgba(255,42,42,0.3); padding:6px; border-radius:4px; font-weight:bold; cursor:pointer;">🎯 CALIBRATE ROI</button>
          <button id="fr-btn-toggle-ingest" style="flex:1; background: #ff2a2a; color:#fff; border:none; padding:6px; border-radius:4px; font-weight:bold; cursor:pointer;">START INGEST</button>
        </div>
        <div>
          <label style="font-size: 10px; color: #7a8599; font-weight: bold;">SCALE PROFILE:</label>
          <select id="fr-sel-scale" style="width: 100%; background: #0c0d10; color: #ff2a2a; border: 1px solid rgba(255,42,42,0.3); padding: 5px; font-size: 11px; font-family: monospace; border-radius: 4px; margin-top: 2px;">
            <option value="100" selected>100% Standard Stream Scale</option>
            <option value="250">250% In-Game Large Scale</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Card 3: Analytics Exporter -->
    <div id="card-analytics" class="fr-roundabout-card">
      <div class="fr-card-hdr">
        <span>📥 MATCH ANALYTICS EXPORTER</span>
        <button class="fr-close-card" style="background:none; border:none; color:#ff2a2a; cursor:pointer; font-weight:bold;">✕</button>
      </div>
      <div style="text-align: center; padding: 10px;">
        <p style="font-size: 11px; color: #7a8599; margin-bottom: 10px;">Export full session timeline, weapon stats, and team scores to JSON format.</p>
        <button id="fr-btn-download-analytics" style="background: #ff2a2a; color:#fff; border:none; padding: 8px 16px; border-radius: 4px; font-weight: bold; cursor: pointer; letter-spacing: 0.5px;">📥 DOWNLOAD MATCH JSON</button>
      </div>
    </div>

    <!-- Card 4: System Telemetry SLA -->
    <div id="card-telemetry" class="fr-roundabout-card">
      <div class="fr-card-hdr">
        <span>⏱️ HARDWARE & SLA TELEMETRY</span>
        <button class="fr-close-card" style="background:none; border:none; color:#ff2a2a; cursor:pointer; font-weight:bold;">✕</button>
      </div>
      <div style="font-size: 11px; color: #7a8599; display: flex; flex-direction: column; gap: 6px;">
        <div style="display: flex; justify-content: space-between;">
          <span>Target Engine:</span>
          <span style="color: #fff; font-weight: bold;">PaddleOCR PP-OCRv4 (iGPU)</span>
        </div>
        <div style="display: flex; justify-content: space-between;">
          <span>Pipeline Latency ($P_{50}$):</span>
          <span style="color: #39ff14; font-weight: bold;">~11.8 ms</span>
        </div>
        <div style="display: flex; justify-content: space-between;">
          <span>Active Ruleset:</span>
          <span style="color: #ff2a2a; font-weight: bold;">BMPS Matrix</span>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(root);

  // Core Hub Click Event (Expand/Collapse Radial Orbit Dock)
  const coreHub = document.getElementById("fr-core-hub");
  const orbitRing = document.getElementById("fr-orbit-ring");

  coreHub.addEventListener("click", () => {
    orbitRing.classList.toggle("expanded");
  });

  // Orbital Pod Clicks (Open corresponding app card)
  const pods = document.querySelectorAll(".fr-orbital-pod");
  pods.forEach((pod) => {
    pod.addEventListener("click", (e) => {
      e.stopPropagation();
      const targetCardId = pod.getAttribute("data-target");

      // Close open card if same clicked, else open target
      document.querySelectorAll(".fr-roundabout-card").forEach((card) => {
        if (card.id === targetCardId) {
          card.classList.toggle("active");
        } else {
          card.classList.remove("active");
        }
      });
    });
  });

  // Close Buttons inside Cards
  document.querySelectorAll(".fr-close-card").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.closest(".fr-roundabout-card").classList.remove("active");
    });
  });

  // Controls Events inside App Pod
  const btnCalibrate = document.getElementById("fr-btn-calibrate");
  if (btnCalibrate) {
    btnCalibrate.addEventListener("click", () => {
      chrome.runtime.sendMessage({ action: "start-calibration" }).catch(() => {});
    });
  }

  const btnDownloadAnalytics = document.getElementById("fr-btn-download-analytics");
  if (btnDownloadAnalytics) {
    btnDownloadAnalytics.addEventListener("click", () => {
      fetch(`${SERVER_URL}/api/analytics/export`)
        .then((res) => res.json())
        .then((data) => {
          if (data.status === "success" && data.report) {
            const blob = new Blob([JSON.stringify(data.report, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `fragengine_match_report_${Date.now()}.json`;
            a.click();
            URL.revokeObjectURL(url);
          } else {
            alert("Failed to export analytics. Ensure server is active.");
          }
        })
        .catch(() => alert("Could not connect to Flask server."));
    });
  }

  // Real-time Telemetry Polling
  function updateTelemetry() {
    fetch(`${SERVER_URL}/api/telemetry_state`)
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "success" && data.leaderboard) {
          renderLeaderboard(data.leaderboard);
        }
      })
      .catch(() => {});
  }

  function renderLeaderboard(leaderboard) {
    const rowsContainer = document.getElementById("fr-rows-container");
    if (!rowsContainer || !leaderboard.length) return;

    let html = "";
    leaderboard.slice(0, 16).forEach((item) => {
      let bars = "";
      (item.player_states || []).forEach((st) => {
        if (st === "ALIVE") bars += '<span style="width:7px; height:11px; background:#39ff14; border-radius:1px; display:inline-block; margin:0 1px; box-shadow:0 0 4px #39ff14;"></span>';
        else if (st === "KNOCKED") bars += '<span style="width:7px; height:11px; background:#ff2a2a; border-radius:1px; display:inline-block; margin:0 1px; box-shadow:0 0 6px #ff2a2a;"></span>';
        else bars += '<span style="width:7px; height:11px; background:#2a2e39; border-radius:1px; display:inline-block; margin:0 1px; opacity:0.3;"></span>';
      });

      const rankFormatted = String(item.current_rank).padStart(2, "0");
      const rColor = item.current_rank === 1 ? "#ffffff" : "#7a8599";

      html += `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 5px 6px; margin-bottom: 3px; background: rgba(22, 25, 32, 0.85); border-radius: 4px; border: 1px solid rgba(255, 42, 42, 0.1); font-size: 11px;">
          <span style="width: 24px; color: ${rColor}; font-weight: 800;">#${rankFormatted}</span>
          <span style="width: 80px; color: #ffffff; font-weight: 800;">${item.team_tag}</span>
          <span style="width: 90px; text-align: center; display: flex; justify-content: center;">${bars}</span>
          <span style="width: 36px; text-align: right; color: #ffffff;">${item.finishes}</span>
          <span style="width: 44px; text-align: right; color: #ff2a2a; font-weight: 900;">${item.total_points}</span>
        </div>
      `;
    });

    rowsContainer.innerHTML = html;
  }

  setInterval(updateTelemetry, 1000);
})();
