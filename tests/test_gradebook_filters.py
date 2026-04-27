"""
Unit tests for gradebook poll filtering and attendance counting (session-scoped).
Uses a fresh SQLite DB and reloads app so the module is not tied to the dev database.
"""
import os
import sys
import pytest
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash


@pytest.fixture(scope="module")
def app_module(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("gb") / "filter_test.db"
    os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    os.environ["SECRET_KEY"] = "test-secret-gradebook-filters"
    os.environ["TESTING"] = "1"
    for name in list(sys.modules.keys()):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    import app as app_mod

    with app_mod.app.app_context():
        app_mod.db.create_all()
        app_mod.migrate_database()
    return app_mod


def test_gradebook_poll_excludes_exclude_from_grading_session(app_module):
    """Polls created during an exclude_from_grading session do not count toward poll grade."""
    m = app_module
    with m.app.app_context():
        prof = m.Professor(
            username="gbprof1",
            email="gb1@test.local",
            password_hash=generate_password_hash("x"),
        )
        m.db.session.add(prof)
        m.db.session.commit()

        c = m.Class(professor_id=prof.id, name="GB Class", class_code="GBX001")
        m.db.session.add(c)
        m.db.session.commit()

        st = m.Student(
            first_name="S",
            last_name="T",
            student_number="111222333",
            email="st@test.local",
        )
        m.db.session.add(st)
        m.db.session.commit()

        m.db.session.add(m.Enrollment(class_id=c.id, student_id=st.id, is_active=True))
        m.db.session.add(
            m.GradingWeights(
                class_id=c.id,
                attendance_weight=25.0,
                participation_weight=50.0,
                participation_instructor_share=50.0,
                poll_weight=25.0,
            )
        )
        m.db.session.commit()

        t0 = datetime.utcnow() - timedelta(hours=2)
        sess_ex = m.ClassSession(
            class_id=c.id,
            start_time=t0,
            end_time=t0 + timedelta(hours=1),
            exclude_from_grading=True,
        )
        m.db.session.add(sess_ex)
        m.db.session.commit()

        poll = m.Poll(
            class_id=c.id,
            question="Q",
            options='["a","b"]',
            correct_answer=0,
            is_graded=True,
            is_active=False,
            created_at=t0 + timedelta(minutes=10),
        )
        m.db.session.add(poll)
        m.db.session.commit()

        m.db.session.add(
            m.PollResponse(
                poll_id=poll.id,
                student_id=st.id,
                answer=0,
                is_correct=True,
            )
        )
        m.db.session.commit()

        prs = m.gradebook_poll_responses_by_student(c.id)
        assert prs.get(st.id, []) == []


def test_count_graded_attendance_session_scoped(app_module):
    """Attendance counts one graded session when student has a session-scoped row with join_time."""
    m = app_module
    with m.app.app_context():
        prof = m.Professor(
            username="gbprof2",
            email="gb2@test.local",
            password_hash=generate_password_hash("x"),
        )
        m.db.session.add(prof)
        m.db.session.commit()

        c = m.Class(professor_id=prof.id, name="GB Class 2", class_code="GBX002")
        m.db.session.add(c)
        m.db.session.commit()

        st = m.Student(
            first_name="A",
            last_name="B",
            student_number="444555666",
            email="ab@test.local",
        )
        m.db.session.add(st)
        m.db.session.commit()

        m.db.session.add(m.Enrollment(class_id=c.id, student_id=st.id, is_active=True))
        t0 = datetime.utcnow() - timedelta(days=1)
        sess = m.ClassSession(
            class_id=c.id,
            start_time=t0,
            end_time=t0 + timedelta(hours=1),
            exclude_from_grading=False,
        )
        m.db.session.add(sess)
        m.db.session.commit()

        m.db.session.add(
            m.Attendance(
                class_id=c.id,
                student_id=st.id,
                class_session_id=sess.id,
                date=t0.date(),
                present=True,
                join_time=t0,
                leave_time=t0 + timedelta(minutes=30),
            )
        )
        m.db.session.commit()

        cnt, total = m.count_graded_attendance_for_student(c.id, st.id)
        assert total == 1
        assert cnt == 1


def test_clear_poll_responses_returns_poll_id_in_socket_payload(app_module):
    """clear_poll_responses commits and documents poll_id for client handlers."""
    m = app_module
    with m.app.app_context():
        from unittest.mock import patch

        prof = m.Professor(
            username="gbprof3",
            email="gb3@test.local",
            password_hash=generate_password_hash("x"),
        )
        m.db.session.add(prof)
        m.db.session.commit()
        c = m.Class(professor_id=prof.id, name="GB Class 3", class_code="GBX003")
        m.db.session.add(c)
        m.db.session.commit()
        poll = m.Poll(
            class_id=c.id,
            question="Q",
            options='["a"]',
            correct_answer=0,
            is_graded=True,
            is_active=True,
        )
        m.db.session.add(poll)
        m.db.session.commit()

        emitted = {}

        def capture_emit(event, payload, **kwargs):
            emitted["event"] = event
            emitted["payload"] = payload

        with patch.object(m.socketio, "emit", side_effect=capture_emit):
            with m.app.test_request_context():
                from flask_login import login_user

                login_user(prof)
                m.clear_poll_responses(poll.id)

        assert emitted.get("event") == "poll_responses_cleared"
        assert emitted.get("payload", {}).get("poll_id") == poll.id


def test_effective_weights_all_graded_sessions_without_polls(app_module):
    """When every graded session has no poll, poll_weight is added to attendance_weight."""
    m = app_module
    with m.app.app_context():
        prof = m.Professor(
            username="gbprof_eff1",
            email="eff1@test.local",
            password_hash=generate_password_hash("x"),
        )
        m.db.session.add(prof)
        m.db.session.commit()
        c = m.Class(professor_id=prof.id, name="Eff Class", class_code="EFF001")
        m.db.session.add(c)
        m.db.session.commit()
        gw = m.GradingWeights(
            class_id=c.id,
            attendance_weight=50.0,
            participation_weight=0.0,
            participation_instructor_share=50.0,
            poll_weight=50.0,
        )
        m.db.session.add(gw)
        t0 = datetime.utcnow() - timedelta(days=2)
        sess = m.ClassSession(
            class_id=c.id,
            start_time=t0,
            end_time=t0 + timedelta(hours=1),
            exclude_from_grading=False,
        )
        m.db.session.add(sess)
        m.db.session.commit()

        eff_a, eff_p = m.effective_attendance_and_poll_weights(c.id, gw)
        assert eff_a == 100.0
        assert eff_p == 0.0


def test_effective_weights_split_when_some_sessions_have_polls(app_module):
    """Poll weight is split: voided share moves to attendance proportionally."""
    m = app_module
    with m.app.app_context():
        prof = m.Professor(
            username="gbprof_eff2",
            email="eff2@test.local",
            password_hash=generate_password_hash("x"),
        )
        m.db.session.add(prof)
        m.db.session.commit()
        c = m.Class(professor_id=prof.id, name="Eff Class 2", class_code="EFF002")
        m.db.session.add(c)
        m.db.session.commit()
        gw = m.GradingWeights(
            class_id=c.id,
            attendance_weight=50.0,
            participation_weight=0.0,
            participation_instructor_share=50.0,
            poll_weight=50.0,
        )
        m.db.session.add(gw)
        t_a = datetime.utcnow() - timedelta(days=5)
        t_b = datetime.utcnow() - timedelta(days=3)
        sess_a = m.ClassSession(
            class_id=c.id,
            start_time=t_a,
            end_time=t_a + timedelta(hours=1),
            exclude_from_grading=False,
        )
        sess_b = m.ClassSession(
            class_id=c.id,
            start_time=t_b,
            end_time=t_b + timedelta(hours=1),
            exclude_from_grading=False,
        )
        m.db.session.add_all([sess_a, sess_b])
        m.db.session.commit()

        poll = m.Poll(
            class_id=c.id,
            question="Q",
            options='["a","b"]',
            correct_answer=0,
            is_graded=True,
            is_active=False,
            created_at=t_b + timedelta(minutes=5),
        )
        m.db.session.add(poll)
        m.db.session.commit()

        eff_a, eff_p = m.effective_attendance_and_poll_weights(c.id, gw)
        assert abs(eff_a - 75.0) < 1e-6
        assert abs(eff_p - 25.0) < 1e-6


def test_absence_exemption_skips_session_in_attendance_count(app_module):
    """Excused session is omitted from denominator; other graded sessions still count."""
    m = app_module
    with m.app.app_context():
        prof = m.Professor(
            username="gbprof_ex1",
            email="ex1@test.local",
            password_hash=generate_password_hash("x"),
        )
        m.db.session.add(prof)
        m.db.session.commit()
        c = m.Class(professor_id=prof.id, name="Ex Class", class_code="EX001")
        m.db.session.add(c)
        m.db.session.commit()
        st = m.Student(
            first_name="E",
            last_name="X",
            student_number="777888999",
            email="exst@test.local",
        )
        m.db.session.add(st)
        m.db.session.commit()
        m.db.session.add(m.Enrollment(class_id=c.id, student_id=st.id, is_active=True))
        t_a = datetime.utcnow() - timedelta(days=10)
        t_b = datetime.utcnow() - timedelta(days=8)
        sess_a = m.ClassSession(
            class_id=c.id,
            start_time=t_a,
            end_time=t_a + timedelta(hours=1),
            exclude_from_grading=False,
        )
        sess_b = m.ClassSession(
            class_id=c.id,
            start_time=t_b,
            end_time=t_b + timedelta(hours=1),
            exclude_from_grading=False,
        )
        m.db.session.add_all([sess_a, sess_b])
        m.db.session.commit()
        m.db.session.add(
            m.AbsenceExemption(
                class_id=c.id,
                class_session_id=sess_a.id,
                student_id=st.id,
            )
        )
        m.db.session.commit()

        cnt, total = m.count_graded_attendance_for_student(c.id, st.id)
        assert total == 1
        assert cnt == 0


def test_absence_exemption_all_countable_sessions_exempt(app_module):
    """When every graded session is excused for the student, denominator is zero."""
    m = app_module
    with m.app.app_context():
        prof = m.Professor(
            username="gbprof_ex2",
            email="ex2@test.local",
            password_hash=generate_password_hash("x"),
        )
        m.db.session.add(prof)
        m.db.session.commit()
        c = m.Class(professor_id=prof.id, name="Ex Class 2", class_code="EX002")
        m.db.session.add(c)
        m.db.session.commit()
        st = m.Student(
            first_name="Y",
            last_name="Z",
            student_number="666777888",
            email="yz@test.local",
        )
        m.db.session.add(st)
        m.db.session.commit()
        m.db.session.add(m.Enrollment(class_id=c.id, student_id=st.id, is_active=True))
        t0 = datetime.utcnow() - timedelta(days=4)
        sess = m.ClassSession(
            class_id=c.id,
            start_time=t0,
            end_time=t0 + timedelta(hours=1),
            exclude_from_grading=False,
        )
        m.db.session.add(sess)
        m.db.session.commit()
        m.db.session.add(
            m.AbsenceExemption(
                class_id=c.id,
                class_session_id=sess.id,
                student_id=st.id,
            )
        )
        m.db.session.commit()

        cnt, total = m.count_graded_attendance_for_student(c.id, st.id)
        assert total == 0
        assert cnt == 0


def test_absence_exemption_api_sets_and_clears(app_module):
    m = app_module
    sess_id = None
    st_id = None
    with m.app.app_context():
        prof = m.Professor(
            username="gbprof_ex3",
            email="ex3@test.local",
            password_hash=generate_password_hash("secret12"),
        )
        m.db.session.add(prof)
        m.db.session.commit()
        c = m.Class(professor_id=prof.id, name="Ex Class 3", class_code="EX003")
        m.db.session.add(c)
        m.db.session.commit()
        st = m.Student(
            first_name="Api",
            last_name="Test",
            student_number="555444333",
            email="apiex@test.local",
        )
        m.db.session.add(st)
        m.db.session.commit()
        m.db.session.add(m.Enrollment(class_id=c.id, student_id=st.id, is_active=True))
        t0 = datetime.utcnow() - timedelta(days=5)
        sess = m.ClassSession(
            class_id=c.id,
            start_time=t0,
            end_time=t0 + timedelta(hours=1),
            exclude_from_grading=False,
        )
        m.db.session.add(sess)
        m.db.session.commit()
        sess_id = sess.id
        st_id = st.id

    with m.app.test_client() as client:
        client.post(
            "/login",
            json={"username": "gbprof_ex3", "password": "secret12", "user_type": "professor"},
        )
        rv = client.post(
            f"/api/class_session/{sess_id}/absence_exemption",
            json={"student_id": st_id, "exempt": True},
        )
        assert rv.status_code == 200
        assert rv.get_json().get("success") is True
        rv2 = client.post(
            f"/api/class_session/{sess_id}/absence_exemption",
            json={"student_id": st_id, "exempt": False},
        )
        assert rv2.status_code == 200
        assert rv2.get_json().get("absence_exempt") is False

    with m.app.app_context():
        assert (
            m.AbsenceExemption.query.filter_by(
                class_session_id=sess_id,
                student_id=st_id,
            ).first()
            is None
        )


def test_gradebook_attendance_hundred_when_no_countable_sessions(app_module):
    """If all graded sessions are exempt for a student, attendance grade is 100%."""
    m = app_module
    class_id = None
    with m.app.app_context():
        prof = m.Professor(
            username="gbprof_ex4",
            email="ex4@test.local",
            password_hash=generate_password_hash("secret12"),
        )
        m.db.session.add(prof)
        m.db.session.commit()
        c = m.Class(professor_id=prof.id, name="Ex Class 4", class_code="EX004")
        m.db.session.add(c)
        m.db.session.commit()
        class_id = c.id
        m.db.session.add(
            m.GradingWeights(
                class_id=c.id,
                attendance_weight=100.0,
                participation_weight=0.0,
                participation_instructor_share=50.0,
                poll_weight=0.0,
            )
        )
        st = m.Student(
            first_name="Zed",
            last_name="Zero",
            student_number="991112223",
            email="zedex4@test.local",
        )
        m.db.session.add(st)
        m.db.session.commit()
        m.db.session.add(m.Enrollment(class_id=c.id, student_id=st.id, is_active=True))
        t0 = datetime.utcnow() - timedelta(days=6)
        sess = m.ClassSession(
            class_id=c.id,
            start_time=t0,
            end_time=t0 + timedelta(hours=1),
            exclude_from_grading=False,
        )
        m.db.session.add(sess)
        m.db.session.commit()
        m.db.session.add(
            m.AbsenceExemption(
                class_id=c.id,
                class_session_id=sess.id,
                student_id=st.id,
            )
        )
        m.db.session.commit()
        student_id = st.id

    with m.app.test_client() as client:
        client.post(
            "/login",
            json={"username": "gbprof_ex4", "password": "secret12", "user_type": "professor"},
        )
        rv = client.get(f"/api/gradebook/{class_id}")
        rows = rv.get_json()
        row = next(r for r in rows if r["student_id"] == student_id)
        assert abs(row["attendance_grade"] - 100.0) < 0.02
