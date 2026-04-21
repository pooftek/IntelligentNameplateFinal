---
name: review
description: Code review focused on correctness, logic bugs, and codebase-specific gotchas before committing.
---

Review changed code for correctness. Focus on bugs, not style.

## Logic checks

**Grading logic (if touched):**
- `_recompute_subject_participation_grades()` called after any participation grade change
- `GradingWeights` weights validated to sum to 1.0
- Absence exemptions accounted for in attendance denominator
- Ungraded polls excluded from poll grade computation

**Auth logic (if touched):**
- Professor route: `class_id` ownership verified against `current_user.id`
- Student route: `_authenticated_student_id()` result checked for None before use
- Token expiry respected — no `max_age` bypass

**SocketIO (if touched):**
- Correct rooms targeted — `class_{id}` vs `enrolled_{id}` vs both
- No blocking operations in event handlers
- Room join/leave balanced — no phantom listeners

**DB (if touched):**
- No N+1 query patterns in loops over students/sessions
- `ClassSession` active-session invariant maintained (`Class.is_active` consistent with open session)
- New nullable=False columns have defaults

**General:**
- All branches of conditionals handled — no silent fall-through
- Error responses return JSON (this is an API), not HTML
- No unhandled exceptions that would expose stack traces

Report format: `[file:line] problem — suggested fix`. Flag blocking bugs separately from warnings.
