"""Tests for quiz aggregates in GET /api/class_metrics/<class_id>."""
import json
import os
import sys

import pytest
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash


@pytest.fixture(scope="module")
def app_module(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("metrics") / "class_metrics_quiz.db"
    os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    os.environ["SECRET_KEY"] = "test-secret-class-metrics-quiz"
    os.environ["TESTING"] = "1"
    for name in list(sys.modules.keys()):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    import app as app_mod

    with app_mod.app.app_context():
        app_mod.db.create_all()
        app_mod.migrate_database()
    return app_mod


def test_class_metrics_quiz_results_per_student(app_module):
    """Session includes quiz_results with per-student correct/total and null when not submitted."""
    m = app_module
    with m.app.app_context():
        prof = m.Professor(
            username="metprof_quiz",
            email="metquiz@test.local",
            password_hash=generate_password_hash("secret12"),
        )
        m.db.session.add(prof)
        m.db.session.commit()
        c = m.Class(professor_id=prof.id, name="Metrics Quiz Class", class_code="MQZ001")
        m.db.session.add(c)
        m.db.session.commit()

        st1 = m.Student(
            first_name="Ann",
            last_name="One",
            student_number="111",
            email="ann@test.local",
        )
        st2 = m.Student(
            first_name="Bob",
            last_name="Two",
            student_number="222",
            email="bob@test.local",
        )
        m.db.session.add_all([st1, st2])
        m.db.session.commit()
        m.db.session.add(m.Enrollment(class_id=c.id, student_id=st1.id, is_active=True))
        m.db.session.add(m.Enrollment(class_id=c.id, student_id=st2.id, is_active=True))

        t0 = datetime.utcnow() - timedelta(days=1)
        sess = m.ClassSession(
            class_id=c.id,
            start_time=t0,
            end_time=t0 + timedelta(hours=1),
            exclude_from_grading=False,
        )
        m.db.session.add(sess)
        m.db.session.commit()

        qz = m.Quiz(
            class_id=c.id,
            title="Week 1 check-in",
            time_limit_seconds=300,
            quiz_index=1,
        )
        m.db.session.add(qz)
        m.db.session.flush()
        q1 = m.QuizQuestion(
            quiz_id=qz.id,
            order=1,
            prompt="A?",
            options=json.dumps(["x", "y"]),
            correct_index=0,
        )
        q2 = m.QuizQuestion(
            quiz_id=qz.id,
            order=2,
            prompt="B?",
            options=json.dumps(["p", "q"]),
            correct_index=1,
        )
        m.db.session.add_all([q1, q2])
        m.db.session.flush()

        run = m.QuizRun(
            quiz_id=qz.id,
            class_id=c.id,
            started_at=t0 + timedelta(minutes=10),
            deadline_at=t0 + timedelta(minutes=40),
            ended_at=t0 + timedelta(minutes=35),
            is_active=False,
        )
        m.db.session.add(run)
        m.db.session.flush()

        m.db.session.add(
            m.QuizAnswer(
                quiz_run_id=run.id,
                student_id=st1.id,
                question_id=q1.id,
                selected_index=0,
                is_correct=True,
            )
        )
        m.db.session.add(
            m.QuizAnswer(
                quiz_run_id=run.id,
                student_id=st1.id,
                question_id=q2.id,
                selected_index=0,
                is_correct=False,
            )
        )
        m.db.session.commit()
        class_id = c.id
        session_id = sess.id
        st1_id = st1.id
        st2_id = st2.id
        run_id = run.id

    with m.app.test_client() as client:
        client.post(
            "/login",
            data={
                "username": "metprof_quiz",
                "password": "secret12",
                "user_type": "professor",
            },
        )
        rv = client.get(f"/api/class_metrics/{class_id}")

    assert rv.status_code == 200
    payload = rv.get_json()
    assert isinstance(payload, list)
    assert len(payload) >= 1
    session_row = next((s for s in payload if s.get("session_id") == session_id), None)
    assert session_row is not None
    qr = session_row.get("quiz_results") or []
    assert len(qr) == 1
    block = qr[0]
    assert block["quiz_run_id"] == run_id
    assert block["quiz_title"] == "Week 1 check-in"
    assert block["question_count"] == 2
    scores = {row["student_id"]: row for row in block["student_scores"]}
    assert scores[st1_id]["correct_count"] == 1
    assert scores[st1_id]["total_questions"] == 2
    assert scores[st1_id]["percent"] == 50.0
    bd = scores[st1_id]["question_breakdown"]
    assert bd is not None and len(bd) == 2
    assert bd[0]["prompt"] == "A?"
    assert bd[0]["is_correct"] is True
    assert bd[0]["selected_text"] == "x"
    assert bd[0]["correct_text"] == "x"
    assert bd[1]["prompt"] == "B?"
    assert bd[1]["is_correct"] is False
    assert bd[1]["selected_text"] == "p"
    assert bd[1]["correct_text"] == "q"
    assert scores[st2_id]["correct_count"] is None
    assert scores[st2_id]["percent"] is None
    assert scores[st2_id]["question_breakdown"] is None
