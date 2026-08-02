/**
 * FragEngine V0.16.2 — Studio Command Center Logic
 */

const SERVER_URL = "http://127.0.0.1:5000";

document.addEventListener("DOMContentLoaded", () => {
  const btnLoadRoster = document.getElementById("btnLoadRoster");
  const btnSwitchRulesetBMPS = document.getElementById("btnSwitchRulesetBMPS");
  const btnSwitchRulesetHardcore = document.getElementById("btnSwitchRulesetHardcore");
  const btnDownloadReport = document.getElementById("btnDownloadReport");

  if (btnLoadRoster) {
    btnLoadRoster.addEventListener("click", loadScarfallRoster);
  }
  if (btnSwitchRulesetBMPS) {
    btnSwitchRulesetBMPS.addEventListener("click", () => switchRuleset("bmps"));
  }
  if (btnSwitchRulesetHardcore) {
    btnSwitchRulesetHardcore.addEventListener("click", () => switchRuleset("hardcore"));
  }
  if (btnDownloadReport) {
    btnDownloadReport.addEventListener("click", downloadReport);
  }

  // Poll live telemetry every second
  setInterval(pollTelemetry, 1000);
  pollTelemetry();
});

async function pollTelemetry() {
  try {
    const res = await fetch(`${SERVER_URL}/api/telemetry_state`);
    const data = await res.json();
    if (data.status === "success") {
      renderLeaderboard(data.leaderboard);
      const lblRuleset = document.getElementById("lblActiveRuleset");
      if (lblRuleset && data.active_ruleset) {
        lblRuleset.innerText = `RULESET: ${data.active_ruleset.toUpperCase()}`;
      }
    }
  } catch (err) {
    console.warn("Studio telemetry poll error:", err);
  }
}

function renderLeaderboard(leaderboard) {
  const tbody = document.getElementById("studioLeaderboardBody");
  if (!tbody) return;

  if (!leaderboard || leaderboard.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; padding: 24px; color: var(--fr-text-muted);">
          STANDBY // NO ROSTER LOADED. Click 'LOAD SCARFALL 12-TEAM ROSTER'.
        </td>
      </tr>`;
    return;
  }

  let html = "";
  leaderboard.forEach((item) => {
    let bars = "";
    (item.player_states || []).forEach((st) => {
      if (st === "ALIVE") bars += '<div class="pill-bar pill-alive" title="ALIVE"></div>';
      else if (st === "KNOCKED") bars += '<div class="pill-bar pill-knocked" title="KNOCKED"></div>';
      else bars += '<div class="pill-bar pill-eliminated" title="ELIMINATED"></div>';
    });

    const rankFormatted = String(item.current_rank).padStart(2, "0");
    const rankColor = item.current_rank === 1 ? "#ffffff" : "#64748b";

    html += `
      <tr>
        <td style="text-align: center; font-weight: 800; color: ${rankColor};">#${rankFormatted}</td>
        <td style="font-weight: 800; color: #ffffff;">${item.team_tag}</td>
        <td style="text-align: center;"><div class="pill-flex">${bars}</div></td>
        <td style="text-align: right; font-weight: 700; color: #ffffff;">${item.finishes}</td>
        <td style="text-align: right; color: var(--fr-text-muted);">${item.placement_points}</td>
        <td style="text-align: right; font-weight: 900; color: var(--fr-red-primary); font-size: 15px;">${item.total_points}</td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

async function loadScarfallRoster() {
  const rosterPayload = {
    teams: [
      { tag: "PLTN", name: "Peloton", players: ["P1", "P2", "P3", "P4"] },
      { tag: "CPTN", name: "Captains", players: ["C1", "C2", "C3", "C4"] },
      { tag: "SC", name: "Shadow Clan", players: ["S1", "S2", "S3", "S4"] },
      { tag: "OCN", name: "Ocean Esports", players: ["O1", "O2", "O3", "O4"] },
      { tag: "6SENSE", name: "Sixth Sense", players: ["61", "62", "63", "64"] },
      { tag: "STAR", name: "Star Alliance", players: ["St1", "St2", "St3", "St4"] },
      { tag: "RS", name: "Rising Stars", players: ["R1", "R2", "R3", "R4"] },
      { tag: "XBUG", name: "X-Bugs", players: ["X1", "X2", "X3", "X4"] },
      { tag: "KyZN", name: "KyZN Esports", players: ["EviLKiOz", "Shadow", "Viper", "Apex"] },
      { tag: "FLCN", name: "Falcon Squad", players: ["PRADIP", "Hawk", "Falcon1", "Blaze"] },
      { tag: "TxL", name: "TxL Clan", players: ["CLUSTER", "Striker", "Ghost", "Raven"] },
      { tag: "Tr", name: "Team Tr", players: ["CHAMP-08", "Nitro", "Venom", "Storm"] }
    ]
  };

  try {
    await fetch(`${SERVER_URL}/api/roster`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(rosterPayload)
    });
    pollTelemetry();
  } catch (err) {
    alert("Error loading roster: " + err);
  }
}

async function switchRuleset(rulesetName) {
  try {
    await fetch(`${SERVER_URL}/api/ruleset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ruleset: rulesetName })
    });
    pollTelemetry();
  } catch (err) {
    alert("Error updating ruleset: " + err);
  }
}

function downloadReport() {
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
        alert("Failed to export match report.");
      }
    })
    .catch(() => alert("Could not connect to server."));
}
