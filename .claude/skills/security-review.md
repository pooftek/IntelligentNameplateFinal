---
name: security-review
description: Run a security review on changed code. Checks auth boundaries, input validation, data scoping, and secrets handling for this Flask edtech app.
---

Review all changed code against these security requirements for this edtech app. Student data is sensitive — treat it as such.

## Checklist

**Auth:**
- [ ] Every professor route has `@login_required`
- [ ] Every student API calls `_authenticated_student_id()` and validates result is not None
- [ ] `class_id` in professor routes verified to belong to `current_user` before any read or mutation
- [ ] Enrollment checked before any student-class interaction

**Input validation:**
- [ ] All `request.json` / `request.form` values validated for type and shape at boundary
- [ ] No raw user strings passed to DB queries without parameterization (SQLAlchemy handles this, but verify)
- [ ] File uploads (if any) use `secure_filename` and validate extension

**Secrets:**
- [ ] No hardcoded secrets, tokens, or passwords — all via `os.getenv()` or `app.config`
- [ ] No secrets in error messages or API responses

**Data leaks:**
- [ ] All DB queries scoped to authenticated user's classes/students — no cross-professor data possible
- [ ] API responses don't expose internal fields (password hashes, tokens, etc.)
- [ ] Error handlers return generic messages, not stack traces

**Tokens:**
- [ ] Student tokens validated via `verify_student_token()` — not trusted raw
- [ ] Password reset tokens validated via `verify_professor_password_reset_token()` with expiry

Report each issue as: `[SEVERITY] location — problem — fix`.
Severity: CRITICAL / HIGH / MEDIUM / LOW.
