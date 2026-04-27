# Coding Rules

Before coding: state assumptions, surface tradeoffs, ask if unclear. Never decide silently between interpretations.

**Min code only.** No speculative features, unrequested abstractions, or impossible-scenario handling. 200 lines when 50 works → rewrite.

**Surgical edits:** touch only what request requires. Match existing style exactly — no reformatting, no adjacent cleanup.
Mention unrelated dead code. Remove only imports/vars made unused by YOUR changes.

**NEVER** hardcode secrets — always `os.getenv()` or `app.config`.

**Multi-step tasks** → plan first: `[step] → verify: [check]`.

**Style (match existing codebase):**
- No type hints — codebase uses none, don't introduce them.
- SQLAlchemy: use legacy `.query.filter_by()` style — codebase uses this throughout, don't mix in `select()`.
- No `flask.g` for request data.
- SocketIO: always join/leave rooms explicitly.
- PEP 8 spacing, but follow file's existing patterns over strict rules.
