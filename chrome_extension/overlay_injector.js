/**
 * FragEngine V0.16.1 — In-Page Draggable Cyber-Red HUD Overlay Injector
 * Strictly follows the official Esparda Elites Brand Kit (dev_documentation/brand_kit.md).
 */

(function () {
  if (document.getElementById("fragengine-inpage-overlay")) {
    return; // Already injected
  }

  const SERVER_URL = "http://127.0.0.1:5000";

  // Inject CSS styles for the HUD
  const styleEl = document.createElement("style");
  styleEl.textContent = `
    #fragengine-inpage-overlay {
      position: fixed;
      top: 60px;
      right: 20px;
      width: 360px;
      z-index: 2147483647;
      background-color: rgba(12, 13, 16, 0.92);
      border: 1px solid rgba(255, 42, 42, 0.25);
      border-top: 3px solid #ff2a2a;
      border-radius: 6px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.7);
      font-family: 'JetBrains Mono', 'Consolas', monospace;
      color: #ffffff;
      backdrop-filter: blur(8px);
      user-select: none;
      display: block;
    }
    #fragengine-overlay-hdr {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      background: rgba(22, 25, 32, 0.9);
      cursor: move;
      border-bottom: 1px solid rgba(255, 42, 42, 0.2);
    }
    .hud-bar-pill {
      width: 8px;
      height: 12px;
      border-radius: 2px;
      display: inline-block;
      margin: 0 1px;
    }
    .hud-bar-alive {
      background: #39ff14;
      box-shadow: 0 0 6px rgba(57, 255, 20, 0.5);
    }
    .hud-bar-knocked {
      background: #ff2a2a;
      box-shadow: 0 0 8px #ff2a2a;
      animation: pulse-red-bar 0.8s infinite alternate;
    }
    .hud-bar-eliminated {
      background: #2a2e39;
      opacity: 0.35;
    }
    @keyframes pulse-red-bar {
      from { opacity: 0.4; } to { opacity: 1; }
    }
  `;
  document.head.appendChild(styleEl);

  // Create Overlay Widget Container
  const overlayContainer = document.createElement("div");
  overlayContainer.id = "fragengine-inpage-overlay";

  // Header Bar (Draggable)
  overlayContainer.innerHTML = `
    <div id="fragengine-overlay-hdr">
      <span style="color: #ff2a2a; font-weight: 800; font-size: 12px; letter-spacing: 1px; text-shadow: 0 0 8px rgba(255, 42, 42, 0.4);">((o)) FRAGLAB // LIVE TELEMETRY</span>
      <div>
        <button id="fragengine-overlay-toggle-btn" style="background: none; border: none; color: #7a8599; font-weight: bold; cursor: pointer; font-size: 12px; margin-right: 6px;">[ _ ]</button>
        <button id="fragengine-overlay-close-btn" style="background: none; border: none; color: #ff2a2a; font-weight: bold; cursor: pointer; font-size: 12px;">✕</button>
      </div>
    </div>
    <div id="fragengine-overlay-body" style="padding: 8px;">
      <div id="fragengine-overlay-matrix" style="max-height: 320px; overflow-y: auto;">
        <div style="display: flex; justify-content: space-between; padding: 6px 8px; font-size: 10px; color: #ff2a2a; font-weight: 800; border-bottom: 1px solid rgba(255, 42, 42, 0.25); background: rgba(255, 42, 42, 0.08); letter-spacing: 0.5px;">
          <span style="width: 24px;">#</span>
          <span style="width: 80px;">TEAM</span>
          <span style="width: 90px; text-align: center;">STATUS (4-BAR)</span>
          <span style="width: 36px; text-align: right;">FIN</span>
          <span style="width: 44px; text-align: right;">PTS</span>
        </div>
        <div id="fragengine-overlay-rows" style="margin-top: 4px;">
          <div style="text-align: center; color: #7a8599; padding: 16px; font-size: 11px; font-weight: 700;">STANDBY // WAITING FOR TELEMETRY...</div>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(overlayContainer);

  // Dragging Functionality
  const hdr = document.getElementById("fragengine-overlay-hdr");
  let isDragging = false;
  let offsetX = 0, offsetY = 0;

  hdr.addEventListener("mousedown", (e) => {
    isDragging = true;
    offsetX = e.clientX - overlayContainer.getBoundingClientRect().left;
    offsetY = e.clientY - overlayContainer.getBoundingClientRect().top;
  });

  document.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    overlayContainer.style.left = `${e.clientX - offsetX}px`;
    overlayContainer.style.top = `${e.clientY - offsetY}px`;
    overlayContainer.style.right = "auto";
  });

  document.addEventListener("mouseup", () => {
    isDragging = false;
  });

  // Buttons
  const body = document.getElementById("fragengine-overlay-body");
  const toggleBtn = document.getElementById("fragengine-overlay-toggle-btn");
  const closeBtn = document.getElementById("fragengine-overlay-close-btn");

  toggleBtn.addEventListener("click", () => {
    if (body.style.display === "none") {
      body.style.display = "block";
      toggleBtn.innerText = "[ _ ]";
    } else {
      body.style.display = "none";
      toggleBtn.innerText = "[ + ]";
    }
  });

  closeBtn.addEventListener("click", () => {
    overlayContainer.style.display = "none";
  });

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
    const rowsContainer = document.getElementById("fragengine-overlay-rows");
    if (!rowsContainer || !leaderboard.length) return;

    let html = "";
    leaderboard.slice(0, 16).forEach((item) => {
      let bars = "";
      (item.player_states || []).forEach((st) => {
        if (st === "ALIVE") bars += '<span class="hud-bar-pill hud-bar-alive"></span>';
        else if (st === "KNOCKED") bars += '<span class="hud-bar-pill hud-bar-knocked"></span>';
        else bars += '<span class="hud-bar-pill hud-bar-eliminated"></span>';
      });

      const rankFormatted = String(item.current_rank).padStart(2, "0");
      const rColor = item.current_rank === 1 ? "#ffffff" : "#7a8599";
      const rankGlow = item.current_rank === 1 ? "text-shadow: 0 0 8px rgba(255, 42, 42, 0.6);" : "";

      html += `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 5px 8px; margin-bottom: 3px; background: rgba(22, 25, 32, 0.85); border-radius: 4px; border: 1px solid rgba(255, 42, 42, 0.1); font-size: 11px;">
          <span style="width: 24px; color: ${rColor}; font-weight: 800; ${rankGlow}">#${rankFormatted}</span>
          <span style="width: 80px; color: #ffffff; font-weight: 800; letter-spacing: 0.5px;">${item.team_tag}</span>
          <span style="width: 90px; text-align: center; display: flex; justify-content: center; align-items: center;">${bars}</span>
          <span style="width: 36px; text-align: right; color: #ffffff; font-weight: 700;">${item.finishes}</span>
          <span style="width: 44px; text-align: right; color: #ff2a2a; font-weight: 900;">${item.total_points}</span>
        </div>
      `;
    });

    rowsContainer.innerHTML = html;
  }

  setInterval(updateTelemetry, 1000);
})();
