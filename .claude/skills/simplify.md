---
name: simplify
description: Review recently changed code for over-engineering, redundancy, and style drift. Rewrites where simpler version exists.
---

Review the changed code. Goal: minimum code that correctly solves the problem.

## Check for

**Over-engineering:**
- Abstractions introduced for a single call site — inline them
- Helper functions wrapping one line — remove the wrapper
- Conditionals that can be collapsed
- Dead branches (conditions that can never be true given the context)

**Redundancy:**
- Duplicate DB queries fetching the same object
- Re-validation of data already validated upstream
- Variables assigned once and used once — inline the value

**Style drift (must match existing `app.py` patterns):**
- No type hints introduced
- No `select()` / `session.scalars()` — use `.query.filter_by()`
- No `flask.g` for request data
- No f-string vs % formatting inconsistency — check surrounding code and match

**Token waste:**
- Comments explaining what the code obviously does — remove
- Docstrings longer than one line on internal functions — trim
- Blank lines exceeding two in a row

For each issue: show original → simplified version. Don't touch code outside the changed area.
