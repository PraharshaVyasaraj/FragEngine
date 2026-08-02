/**
 * FragEngine V0.16.1 — In-Page Draggable Cyber-Red HUD Overlay Injector
 * Injects translucent, draggable Esparda Elites live telemetry HUD over video player pages.
 */

(function () {
  if (document.getElementById("fragengine-inpage-overlay")) {
    return; // Already injected
  }

  const SERVER_URL = "http://127.0.0.1:5000";

  // Create Overlay Widget Container
  const overlayContainer = document.createElement("div");
  overlayContainer.id = "fragengine-inpage-overlay";
  overlayContainer.style.position = "fixed";
  overlayContainer.style.top = "60px";
  overlayContainer.style.right = "20px";
  overlayContainer.style.width = "340px";
  overlayContainer.style.zIndex = "2147483647"; // Always-On-Top in DOM
  overlayContainer.style.backgroundColor = "rgba(12, 13, 16, 0.88)";
  overlayContainer.style.border = "1px solid #1a1e28";
  overlayContainer.style.borderTop = "3px solid #ff2a2a";
  overlayContainer.style.borderRadius = "6px";
  overlayContainer.style.boxShadow = "0 8px 24px rgba(0, 0, 0, 0.6)";
  overlayContainer.style.fontFamily = "'Consolas', monospace";
  overlayContainer.style.color = "#ffffff";
  overlayContainer.style.backdropFilter = "blur(6px)";
  overlayContainer.style.userSelect = "none";
  overlayContainer.style.display = "block";

  // Header Bar (Draggable)
  overlayContainer.innerHTML = `
    <div id="fragengine-overlay-hdr" style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: rgba(26, 30, 40, 0.8); cursor: move; border-bottom: 1px solid #1a1e28;">
      <span style="color: #ff2a2a; font-weight: bold; font-size: 11px;">((o)) FRAGLAB // LIVE TELEMETRY</span>
      <div>
        <button id="fragengine-overlay-toggle-btn" style="background: none; border: none; color: #7a8599; font-weight: bold; cursor: pointer; font-size: 12px; margin-right: 6px;">[ _ ]</button>
        <button id="fragengine-overlay-close-btn" style="background: none; border: none; color: #ff2a2a; font-weight: bold; cursor: pointer; font-size: 12px;">✕</button>
      </div>
    </div>
    <div id="fragengine-overlay-body" style="padding: 8px;">
      <div id="fragengine-overlay-matrix" style="max-height: 320px; overflow-y: auto;">
        <div style="display: flex; justify-content: space-between; padding: 4px 6px; font-size: 9px; color: #ff2a2a; font-weight: bold; border-bottom: 1px solid rgba(255, 42, 42, 0.2);">
          <span style="width: 24px;">#</span>
          <span style="width: 70px;">TEAM</span>
          <span style="width: 100px; text-align: center;">STATUS (4-BAR)</span>
          <span style="width: 36px; text-align: right;">FIN</span>
          <span style="width: 44px; text-align: right;">PTS</span>
        </div>
        <div id="fragengine-overlay-rows" style="margin-top: 4px;">
          <div style="text-align: center; color: #5a6478; padding: 12px; font-size: 10px;">STANDBY // WAITING FOR TELEMETRY...</div>
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
    leaderboard.slice(0, 12).forEach((item) => {
      let bars = "";
      (item.player_states || []).forEach((st) => {
        if (st === "ALIVE") bars += "🟩";
        else if (st === "KNOCKED") bars += "🟥";
        else bars += "⬜";
      });

      const rColor = item.current_rank === 1 ? "#ffffff" : "#8b95a5";

      html += `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 6px; margin-bottom: 2px; background: rgba(18, 22, 32, 0.8); border-radius: 3px; font-size: 10px;">
          <span style="width: 24px; color: ${rColor}; font-weight: bold;">#${String(item.current_rank).padStart(2, "0")}</span>
          <span style="width: 70px; color: #ffffff; font-weight: bold;">${item.team_tag}</span>
          <span style="width: 100px; text-align: center; font-size: 8px;">${bars}</span>
          <span style="width: 36px; text-align: right; color: #ffffff;">${item.finishes}</span>
          <span style="width: 44px; text-align: right; color: #ff2a2a; font-weight: bold;">${item.total_points}</span>
        </div>
      `;
    });

    rowsContainer.innerHTML = html;
  }

  setInterval(updateTelemetry, 1000);
})();
