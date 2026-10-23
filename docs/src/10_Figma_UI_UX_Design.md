---
date: October 2026
title: EarthScape – Figma UI/UX Design Specification
---

# 1. Design Goals

Calm, trustworthy and data-dense; alerts must stand out instantly; usable by non-technical stakeholders; responsive from 1366 px laptops to large control-room screens.

# 2. Design System

| Token           | Value                                                               |
|-----------------|---------------------------------------------------------------------|
| Primary         | \#138A72 (teal green)                                               |
| Primary dark    | \#0B4F4A                                                            |
| Background      | \#F3F7F5                                                            |
| Critical        | \#B42318 · High \#E8590C · Medium \#F2B134 · Low \#ADB5BD           |
| Event colours   | heatwave \#E8590C · flood \#1C7ED6 · storm \#7048E8 · smog \#868E96 |
| Font            | Inter / system-ui; H3 24 px bold, body 14 px, labels 12 px          |
| Radius / shadow | 10 px cards, shadow 0 1 4 rgba(0,0,0,.06)                           |
| Grid            | 12 columns, 24 px gutters, 24 px page padding                       |

Components: navbar with model-version badge and LIVE badge, KPI card (4 px left accent), chart card, data table (small), level badge, toast alert, form controls, map marker (colour scale + red ring for alerts).

# 3. Frames to Create in Figma

| \#  | Frame (1440×1024)                | Key elements                                                                                                   |
|-----|----------------------------------|----------------------------------------------------------------------------------------------------------------|
| 1   | Login                            | Centred card, logo 🌍, username, password, role note                                                           |
| 2   | Dashboard                        | 8 KPI cards, 4 charts in 2×2 grid, latest readings table, models card, toast stack bottom-right, stream button |
| 3   | Map                              | Metric selector, full-width Leaflet map, labelled station circles, popup                                       |
| 4   | Explore                          | Filter bar, wide time-series chart, correlation heat-map, trend bar chart                                      |
| 5   | Predict                          | Two columns: input form (12 fields) / result tiles + explanation table with bars                               |
| 6   | Ingestion                        | Upload card, real-time sources card, jobs table                                                                |
| 7   | Alerts                           | Level filter, table with badges and Ack buttons, notification log                                              |
| 8   | Alert Rules                      | Rules table with inline threshold edit, add-rule form                                                          |
| 9   | Models                           | Runtime card, active model card, 3 charts, version table                                                       |
| 10  | Monitor                          | 8 system tiles, latency chart, drift chart + table, jobs                                                       |
| 11  | Backups / Users / Support / Help | Forms + tables, FAQ accordion                                                                                  |

# 4. User Flows (prototype links)

1.  Login → Dashboard → toast → Alerts → Ack.
2.  Dashboard → Map → station popup → Explore (station preselected).
3.  Analyst: Ingestion → upload → success message → Models (new version) → Monitor (drift).
4.  Analyst: Predict → result → Alert Rules (adjust threshold).

# 5. Accessibility

Contrast ≥ 4.5:1, colour never the only signal (icons ⚠ and text labels), keyboard focus states, 44 px touch targets, units on every value.

# 6. Building it in Figma (step by step)

1.  Create file “EarthScape UI”, add a page “Design system”, define colour and text styles from §2.
2.  Build components (Button, KPI card, Chart card, Badge, Table row, Toast, Navbar) with variants.
3.  Create the 11 frames using a 12-column layout grid; use screenshots of the running app as reference.
4.  Add prototype connections for the flows in §4 (On click → Navigate to, Smart animate).
5.  Share → “Anyone with the link can view” and paste the link in the submission.
