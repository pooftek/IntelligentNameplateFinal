# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Edtech SaaS: in-class participation, attendance, quizzing, auto-grading.
Priorities: performance, security, clean architecture.

Stack: Flask + SQLAlchemy + Flask-SocketIO.
All backend in `app.py` (~4400 LOC, no blueprints). Students use Raspberry Pi nameplates.

**Run:** `python app.py` (port 5000).
Copy `.env.example` → `.env` and set `SECRET_KEY`.
Email optional — missing config writes reset links to `password_reset_last_link.txt`.

**YOU MUST** match existing style on every edit.
**Surgical edits only.** Touch nothing the request does not require.
Mention (don't delete) unrelated dead code.

## Auto-Memory

Save learnings here as discovered. Format: `**[topic]:** [finding]`. Update, don't duplicate.

**Test flake:** conftest `live_server` cold boot can exceed its 15s wait → every test ERRORs "Flask server did not start on port 18764"; a plain rerun passes.
**Professor auth:** email-only login + `full_name` (non-unique) since July 2026; `username` column renamed by a table-rebuild block in `migrate_database()` — runs only via `python app.py`.
**Fixed-viewport pages:** classroom/faculty_dashboard/class_data/students_list lock `body{height:100vh;height:100dvh;overflow:hidden}` + inner container; each releases to `height:auto;overflow-y:auto` under `@media (max-width:…), ((any-pointer: coarse) and (not (any-pointer: fine)))`. Tablets need the touch OR-branch — they report desktop CSS widths (landscape 1280px; desktop-site mode even in portrait) so width breakpoints never fire. Tablet discriminator MUST be `not (any-pointer: fine)`: primary-pointer/hover heuristics (`pointer: coarse`, `any-hover: none`) misfire on real Windows touchscreen laptops (July 2026 prod incident — laptops got the compact layout). A trackpad/mouse always registers `any-pointer: fine`, so laptops can never match; pure-touch tablets have no fine pointer. Release is a visual no-op when content fits.
**Footer:** base.html wraps `.comet-footer` in `{% block footer %}`; every page with its own 14px `*-branding` logo (all professor pages + account_settings/preferences + auth pages) overrides it empty — otherwise both logos show on scrollable pages.
**Landing tablet:** `@media (any-pointer: coarse) and (not (any-pointer: fine)) and (min-width:821px)` hides `.nodes`/`.meteors` (≤820px block covers phones); JS `isCoarse` (same query) makes hero start pre-assembled (constant scale → no per-frame 2.28MB nameplate.png re-raster).
**Perf debt:** base.html tooltip MutationObserver rescans whole document per mutation; faculty_dashboard rewrites `#dashboardContent` innerHTML every 2s + per socket event → continuous rescans, laggy on tablets.
**Pi dual-DSI nameplate:** two Waveshare 480x1920 panels mounted landscape (1920x480). OS spans both into ONE 3840x480 desktop; a SINGLE spanned Chromium window (not two windows) at kiosk URL `/student?display=pi`. Route (`app.py` ~4597) reads that flag → `pi_mode`; student_interface.html emits the span CSS ONLY under `{% if pi_mode %}`, so a normal `/student` response is byte-identical for laptop/phone/tablet (non-Pi devices NEVER receive the rule — this was an explicit requirement). Inside that block `@media (min-aspect-ratio:5/1)` flips `.np-root` to `flex-direction:row` + re-shows `#npFront` with `display:block !important` (beats the coarse-pointer back-only rule at ~1291, since touch panels report `pointer:coarse`); the aspect guard means it only splits when actually spanned. Rotation+placement+kiosk launch live in `kiosk/` (`start_kiosk.sh`: Wayland `wlr-randr`/X11 `xrandr`, borderless `--app` sized 3840x480 — NOT `--kiosk`, which snaps to one output; `labwc-autostart`); `setup_pi.sh` prompts to install. Single-runtime → token/front-tint logic unchanged (no cross-window sync). Tests: `tests/test_pi_kiosk_layout.py` (incl. body-diff proof CSS served only with the flag).

## Caveman Mode

ACTIVE EVERY RESPONSE. Drop articles, filler, pleasantries, hedging. Fragments OK. Technical terms exact. Code unchanged.
Off: "stop caveman" / "normal mode".

| Level | Style |
|-------|-------|
| lite | No filler, keep articles + full sentences |
| full | Drop articles, fragments OK (default) |
| ultra | Abbreviate, arrows for causality (X → Y) |

Switch: `/caveman lite|full|ultra`. Auto-clarity on security/irreversible actions. Code/commits stay normal.
