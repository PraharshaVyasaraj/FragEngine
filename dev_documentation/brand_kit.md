# FragEngine // Esparda Elites — Official Brand Kit & Art Direction

This document defines the official visual design system, cyber-red color palette, distressed typography specs, and tactical HUD motifs for **FragEngine / Esparda Elites Broadcast Intelligence**.

---

## 🔴 1. Core Color Palette Tokens

| Token Name | Hex Code | Visual Style | Application |
|---|---|---|---|
| `--color-primary-red` | `#ff2a2a` | Vivid Cyber Red | Primary brand accents, frame motifs, stroke outlines |
| `--color-crimson-flame` | `#d30000` | Crimson Flame Gradient | Corner swirls, active status highlights |
| `--color-dark-obsidian` | `#0c0d10` | Matte Obsidian Black | Main HUD background panel |
| `--color-panel-charcoal` | `#161920` | Charcoal Slate | Secondary table container fills |
| `--color-text-white` | `#ffffff` | Distressed Pure White | Primary headlines, rank numbers, totals |
| `--color-text-dim` | `#7a8599` | Muted Gunmetal | Technical grid labels & secondary telemetry |

---

## 🔤 2. Typography & Texture Specs

### Fonts
1. **Title & Headline Font**: `Bebas Neue` / `Teko` (Weight: 800/900)
   * *Style*: Heavy condensed, uppercase, 3-degree italic slant.
   * *Texture Effect*: Subtle grunge/ink-spray distress overlay inside text fills.
2. **Text Outline Effect**: Hollow red stroke offset (`-webkit-text-stroke: 1.5px #ff2a2a`) layered behind white solid text for depth.
3. **Tactical Telemetry Font**: `JetBrains Mono` (Weight: 700)
   * *Style*: High-tech HUD numbers, crosshairs, grid coordinate labels.

---

## 📐 3. Tactical Graphic Motifs & Grid Overlay

* **Tech Grid Pattern**: 20px semi-transparent grid lines (`rgba(255, 42, 42, 0.08)`).
* **Corner Brackets**: 45-degree chamfered HUD corners with dashed hash marks (`///`).
* **Flame Flourish**: Dynamic organic crimson flame curves sweeping across the outer border edges.

---

## 📊 4. Telemetry Component Colors

* **`ALIVE` Status Bar**: Lime Green `#39ff14` (or Cyber Red `#ff2a2a` in red-themed mode)
* **`KNOCKED` Status Bar**: Flashing Neon Crimson `#ff0033` (`0.8s pulse`)
* **`ELIMINATED` Status Bar**: Dark Charcoal Slate `#2a2e39` (`opacity: 0.3`)
