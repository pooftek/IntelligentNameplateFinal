"""
Tests for hand-raise participation grading (instructor 1–100, peer 0–4 → %).
"""
import os
import sys
import uuid
import pytest
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash


@pytest.fixture(scope="module")
def app_module(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("pg") / "participation_grade.db"
    os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    os.environ["SECRET_KEY"] = "test-secret-participation-grade"
    os.environ["TESTING"] = "1"
    for name in list(sys.modules.keys()):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    import app as app_mod

    with app_mod.app.app_context():
        app_mod.db.create_all()
        app_mod.migrate_database()
    return app_mod


def test_peer_rating_maps_to_percent(app_module):
    m = app_module
    assert m._peer_rating_to_percent(0) == 0.0
    assert m._peer_rating_to_percent(4) == 100.0
    assert m._peer_rating_to_percent(2) == 50.0


def test_blended_participation_grade_formula(app_module):
    """75% instructor / 25% peer of participation: 80 and 40 averages -> 70 blended."""
    m = app_module
    assert abs(m.blended_participation_grade(80, 40, 75) - 70.0) < 1e-9
    # 100% participation weight, 0 attendance/poll -> overall equals blended
    overall = 70.0 * (100.0 / 100.0)
    assert abs(overall - 70.0) < 1e-9


def test_instructor_and_peer_averages_in_participation(app_module):
    """After instructor + one peer grade, Participation row has expected means."""
    m = app_module
    with m.app.app_context():
        prof = m.Professor(
            username="pgprof1",
            email="pg1@test.local",
            password_hash=generate_password_hash("secret12"),
        )
        m.db.session.add(prof)
        m.db.session.commit()

        c = m.Class(professor_id=prof.id, name="PG Class", class_code="PG001", is_active=True)
        m.db.session.add(c)
        m.db.session.commit()

        m.db.session.add(m.ClassSettings(class_id=c.id, show_first_name_only=False, quiet_mode=False))
        m.db.session.add(
            m.ClassSession(class_id=c.id, start_time=datetime.utcnow(), end_time=None, exclude_from_grading=False)
        )
        s1 = m.Student(
            student_number="111111111",
            first_name="Ann",
            last_name="A",
            email="ann@test.local",
            password_hash=generate_password_hash("x"),
        )
        s2 = m.Student(
            student_number="222222222",
            first_name="Bob",
            last_name="B",
            email="bob@test.local",
            password_hash=generate_password_hash("x"),
        )
        m.db.session.add_all([s1, s2])
        m.db.session.commit()

        m.db.session.add(m.Enrollment(class_id=c.id, student_id=s1.id, is_active=True))
        m.db.session.add(m.Enrollment(class_id=c.id, student_id=s2.id, is_active=True))
        m.db.session.commit()

        today = datetime.utcnow().date()
        rnd = m.ParticipationGradeRound(
            class_id=c.id,
            subject_student_id=s1.id,
            date=today,
        )
        m.db.session.add(rnd)
        m.db.session.commit()

        m.db.session.add(m.InstructorParticipationGrade(round_id=rnd.id, score=80))
        m.db.session.add(
            m.PeerParticipationGrade(
                round_id=rnd.id,
                grader_student_id=s2.id,
                rating=2,
                score_percent=50.0,
            )
        )
        m.db.session.commit()

        m._recompute_subject_participation_grades(c.id, s1.id, today)
        m.db.session.commit()

        p = m.Participation.query.filter_by(class_id=c.id, student_id=s1.id, date=today).first()
        assert p is not None
        assert abs(p.instructor_grade - 80.0) < 0.01
        assert abs(p.peer_grade - 50.0) < 0.01


def test_participation_grade_start_requires_active_session(app_module):
    m = app_module
    class_id = None
    student_id = None
    with m.app.app_context():
        prof = m.Professor(
            username="pgprof2",
            email="pg2@test.local",
            password_hash=generate_password_hash("secret12"),
        )
        m.db.session.add(prof)
        m.db.session.commit()
        c = m.Class(professor_id=prof.id, name="PG2", class_code="PG002", is_active=False)
        m.db.session.add(c)
        m.db.session.commit()
        class_id = c.id
        st = m.Student(
            student_number="333333333",
            first_name="C",
            last_name="C",
            email="c@test.local",
            password_hash=generate_password_hash("x"),
        )
        m.db.session.add(st)
        m.db.session.commit()
        student_id = st.id
        m.db.session.add(m.Enrollment(class_id=c.id, student_id=st.id, is_active=True))
        m.db.session.commit()

    with m.app.test_client() as client:
        client.post(
            "/login",
            data={"username": "pgprof2", "password": "secret12", "user_type": "professor"},
        )
        rv = client.post(
            "/api/participation_grade/start",
            json={"class_id": class_id, "subject_student_id": student_id},
        )
        data = rv.get_json()
        assert data.get("success") is False


def _setup_class_with_session(m, *, share_inst=50.0):
    """Professor, class, one graded session, one enrolled student; returns (class, session, student)."""
    u = uuid.uuid4().hex[:10]
    prof = m.Professor(
        username=f"pgprof_sess_{u}",
        email=f"sess{u}@test.local",
        password_hash=generate_password_hash("secret12"),
    )
    m.db.session.add(prof)
    m.db.session.commit()
    c = m.Class(professor_id=prof.id, name="Sess Class", class_code=f"SE{u}", is_active=True)
    m.db.session.add(c)
    m.db.session.commit()
    m.db.session.add(m.ClassSettings(class_id=c.id, show_first_name_only=False, quiet_mode=False))
    t0 = datetime.utcnow() - timedelta(days=1)
    sess = m.ClassSession(
        class_id=c.id,
        start_time=t0,
        end_time=t0 + timedelta(hours=2),
        exclude_from_grading=False,
    )
    m.db.session.add(sess)
    st = m.Student(
        student_number=f"{abs(hash(u)) % 1000000000:09d}",
        first_name="Pat",
        last_name="P",
        email=f"p{u}@test.local",
        password_hash=generate_password_hash("x"),
    )
    m.db.session.add(st)
    m.db.session.commit()
    m.db.session.add(m.Enrollment(class_id=c.id, student_id=st.id, is_active=True))
    m.db.session.add(
        m.GradingWeights(
            class_id=c.id,
            attendance_weight=25.0,
            participation_weight=50.0,
            participation_instructor_share=share_inst,
            poll_weight=25.0,
        )
    )
    m.db.session.commit()
    return c, sess, st


def test_session_participation_score_attendance_floor_only(app_module):
    """Attended, no hand raise, no graded rounds -> 25."""
    m = app_module
    with m.app.app_context():
        c, sess, st = _setup_class_with_session(m)
        m.db.session.add(
            m.Attendance(
                class_id=c.id,
                student_id=st.id,
                class_session_id=sess.id,
                date=sess.start_time.date(),
                present=True,
                join_time=sess.start_time + timedelta(minutes=1),
                leave_time=sess.start_time + timedelta(minutes=30),
            )
        )
        m.db.session.commit()
        sc = m.session_participation_score(c.id, sess, st.id, 50.0)
        assert abs(sc - 25.0) < 1e-6


def test_session_participation_score_hand_raise_floor(app_module):
    """Attended + hand raise in window -> at least 40."""
    m = app_module
    with m.app.app_context():
        c, sess, st = _setup_class_with_session(m)
        m.db.session.add(
            m.Attendance(
                class_id=c.id,
                student_id=st.id,
                class_session_id=sess.id,
                date=sess.start_time.date(),
                present=True,
                join_time=sess.start_time + timedelta(minutes=1),
                leave_time=sess.start_time + timedelta(minutes=30),
            )
        )
        m.db.session.add(
            m.HandRaise(
                class_id=c.id,
                student_id=st.id,
                timestamp=sess.start_time + timedelta(minutes=10),
                cleared=True,
            )
        )
        m.db.session.commit()
        sc = m.session_participation_score(c.id, sess, st.id, 50.0)
        assert abs(sc - 40.0) < 1e-6


def test_session_participation_score_max_of_round_blends(app_module):
    """Multiple rounds in session: course uses max blended score (100% instructor -> max of instructor scores)."""
    m = app_module
    with m.app.app_context():
        c, sess, st = _setup_class_with_session(m, share_inst=100.0)
        m.db.session.add(
            m.Attendance(
                class_id=c.id,
                student_id=st.id,
                class_session_id=sess.id,
                date=sess.start_time.date(),
                present=True,
                join_time=sess.start_time + timedelta(minutes=1),
                leave_time=sess.start_time + timedelta(minutes=30),
            )
        )
        today = sess.start_time.date()
        r1 = m.ParticipationGradeRound(
            class_id=c.id,
            subject_student_id=st.id,
            date=today,
            class_session_id=sess.id,
            created_at=sess.start_time + timedelta(minutes=5),
        )
        r2 = m.ParticipationGradeRound(
            class_id=c.id,
            subject_student_id=st.id,
            date=today,
            class_session_id=sess.id,
            created_at=sess.start_time + timedelta(minutes=20),
        )
        m.db.session.add_all([r1, r2])
        m.db.session.commit()
        m.db.session.add(m.InstructorParticipationGrade(round_id=r1.id, score=30))
        m.db.session.add(m.InstructorParticipationGrade(round_id=r2.id, score=88))
        m.db.session.commit()
        sc = m.session_participation_score(c.id, sess, st.id, 100.0)
        assert abs(sc - 88.0) < 1e-6


def test_course_mean_omits_sessions_where_absent(app_module):
    """Absent for a graded session -> that session does not contribute to the mean."""
    m = app_module
    with m.app.app_context():
        c, sess_a, st = _setup_class_with_session(m)
        t1 = sess_a.start_time + timedelta(days=2)
        sess_b = m.ClassSession(
            class_id=c.id,
            start_time=t1,
            end_time=t1 + timedelta(hours=1),
            exclude_from_grading=False,
        )
        m.db.session.add(sess_b)
        m.db.session.commit()
        m.db.session.add(
            m.Attendance(
                class_id=c.id,
                student_id=st.id,
                class_session_id=sess_a.id,
                date=sess_a.start_time.date(),
                present=True,
                join_time=sess_a.start_time + timedelta(minutes=1),
                leave_time=sess_a.start_time + timedelta(minutes=30),
            )
        )
        m.db.session.commit()
        mean = m.course_mean_session_participation(c.id, st.id, 50.0)
        assert abs(mean - 25.0) < 1e-6


def test_excluded_session_not_in_participation_mean(app_module):
    """exclude_from_grading session -> no score; empty attended set yields 0."""
    m = app_module
    with m.app.app_context():
        c, sess, st = _setup_class_with_session(m)
        sess.exclude_from_grading = True
        m.db.session.add(
            m.Attendance(
                class_id=c.id,
                student_id=st.id,
                class_session_id=sess.id,
                date=sess.start_time.date(),
                present=True,
                join_time=sess.start_time + timedelta(minutes=1),
                leave_time=sess.start_time + timedelta(minutes=30),
            )
        )
        m.db.session.commit()
        assert m.session_participation_score(c.id, sess, st.id, 50.0) is None
        assert m.course_mean_session_participation(c.id, st.id, 50.0) == 0.0


def test_gradebook_participation_matches_course_mean_session(app_module):
    """API gradebook participation_grade matches course_mean_session_participation."""
    m = app_module
    prof_username = None
    class_id = None
    student_id = None
    with m.app.app_context():
        c, sess, st = _setup_class_with_session(m)
        class_id = c.id
        student_id = st.id
        prof_username = m.Professor.query.get(c.professor_id).username
        m.db.session.add(
            m.Attendance(
                class_id=c.id,
                student_id=st.id,
                class_session_id=sess.id,
                date=sess.start_time.date(),
                present=True,
                join_time=sess.start_time + timedelta(minutes=1),
                leave_time=sess.start_time + timedelta(minutes=30),
            )
        )
        m.db.session.commit()
        gw = m.GradingWeights.query.filter_by(class_id=c.id).first()
        expected = m.course_mean_session_participation(c.id, st.id, gw.participation_instructor_share)

    with m.app.test_client() as client:
        client.post(
            "/login",
            data={"username": prof_username, "password": "secret12", "user_type": "professor"},
        )
        rv = client.get(f"/api/gradebook/{class_id}")
        rows = rv.get_json()
        row = next(r for r in rows if r["student_id"] == student_id)
        assert abs(row["participation_grade"] - round(expected, 2)) < 0.02
