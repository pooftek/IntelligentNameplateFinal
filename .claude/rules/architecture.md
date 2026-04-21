# Architecture

**Auth — two systems:**
Professors: Flask-Login session cookies (`/login`, `/logout`).
Students: `itsdangerous` bearer tokens (`Authorization: Bearer <token>`). No student session cookies.

**Real-time:** SocketIO rooms `class_{id}` (prof dashboard) · `enrolled_{id}` (student devices).

**Class lifecycle:** `Class.is_active` + `ClassSession`.
Start → creates session + auto-records attendance on student join.
Stop → closes session.

**Grading:** `GradingWeights` per class (attendance, polls, instructor/peer participation).
`ParticipationGradeRound` = one event: prof picks subject student → instructor grades → peers submit `PeerParticipationGrade`.

**DB relationships:**
`Class` → `Enrollment` ↔ `Student`
`ClassSession` → `Attendance`
`Poll` → `PollResponse`
`ParticipationGradeRound` → `InstructorParticipationGrade` + `PeerParticipationGrade`
`ClassSettings` / `ProfessorPreferences` / `GradingWeights` per class.

**Templates:** `classroom.html` (prof view) · `faculty_dashboard.html` (live monitor) · `student_interface.html` (nameplate) — all heavy JS.
