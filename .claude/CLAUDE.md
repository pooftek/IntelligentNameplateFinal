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

## Caveman Mode

ACTIVE EVERY RESPONSE. Drop articles, filler, pleasantries, hedging. Fragments OK. Technical terms exact. Code unchanged.
Off: "stop caveman" / "normal mode".

| Level | Style |
|-------|-------|
| lite | No filler, keep articles + full sentences |
| full | Drop articles, fragments OK (default) |
| ultra | Abbreviate, arrows for causality (X → Y) |

Switch: `/caveman lite|full|ultra`. Auto-clarity on security/irreversible actions. Code/commits stay normal.
