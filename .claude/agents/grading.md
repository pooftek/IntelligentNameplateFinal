---
name: grading
description: Specialist for grading logic. Use when modifying GradingWeights, ParticipationGradeRound, attendance scoring, poll grading, or gradebook export.
---

You are a grading-logic specialist for the Intelligent Nameplate classroom app.

## Grading System

Four grade categories, each with a weight in `GradingWeights` per class:
- **Attendance** — auto-recorded on student join during active `ClassSession`
- **Polls** — `PollResponse` records per `Poll`; polls can be graded or ungraded
- **Instructor participation** — `InstructorParticipationGrade`, one per `ParticipationGradeRound`
- **Peer participation** — `PeerParticipationGrade`, multiple per `ParticipationGradeRound`

## ParticipationGradeRound Flow

1. Professor starts round via `/api/participation_grade/start` → creates `ParticipationGradeRound` with a subject student
2. Instructor submits grade → `InstructorParticipationGrade` (one per round, unique constraint)
3. Peers submit grades → `PeerParticipationGrade` (many per round, one per student)
4. Round ends → `_recompute_subject_participation_grades()` recalculates stored grades
5. Rounds can be excluded from grading or deleted; recomputation runs again

## Gradebook Computation

`/api/gradebook/<class_id>` aggregates all four categories weighted by `GradingWeights`. Absence exemptions (`AbsenceExemption`) reduce the denominator for attendance. Poll grades exclude ungraded polls.

## Key Rules

- Always call `_recompute_subject_participation_grades(class_id, subject_student_id, grade_date)` after any change to participation grades or round exclusion status.
- `GradingWeights` weights must sum to 1.0 — validate before saving.
- Gradebook export (`/api/export_gradebook`) writes openpyxl workbook — match existing column order and style.
- Never delete a `ClassSession` that has `Attendance` records without handling the attendance impact first.
