# Security

Edtech app — student data is sensitive. Security is non-negotiable.

**NEVER:**
- Hardcode secrets, tokens, or passwords anywhere in code.
- Trust client-supplied IDs without verifying ownership (confirm `class_id` belongs to `current_user` before any mutation).
- Expose stack traces or internal errors in API responses.
- Skip `@login_required` on professor routes or bearer token validation on student routes.

**YOU MUST:**
- Validate all user input at API boundaries — reject unexpected types/shapes early.
- Use `werkzeug.security` for password hashing — never roll your own.
- Treat student tokens as sensitive — call `verify_student_token()` before any student API action.
- Scope all DB queries to the authenticated user's data — no cross-professor data leaks.

**Auth boundaries:**
Professor actions → `@login_required` + ownership check on `class_id`.
Student actions → `_authenticated_student_id()` + enrollment check before interaction.
