"""
Set every professor and student password to the literal string: password

Usage (from project root):
  PowerShell:  $env:RESET_ALL_PASSWORDS='1'; python reset_all_passwords.py
  bash:        RESET_ALL_PASSWORDS=1 python reset_all_passwords.py

Requires the same .env / database as app.py (SQLALCHEMY_DATABASE_URI).
"""
import os
import sys

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)
os.chdir(_APP_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_APP_DIR, '.env'))
except ImportError:
    pass

from werkzeug.security import generate_password_hash

from app import app, db, Professor, Student

DEFAULT_PASSWORD = 'password'


def main():
    if os.environ.get('RESET_ALL_PASSWORDS', '').strip() != '1':
        print(
            'Refusing to run: set environment variable RESET_ALL_PASSWORDS=1 to confirm '
            '(this overwrites every professor and student password).',
            file=sys.stderr,
        )
        sys.exit(1)

    with app.app_context():
        h = generate_password_hash(DEFAULT_PASSWORD)
        profs = Professor.query.all()
        studs = Student.query.all()
        for p in profs:
            p.password_hash = h
        for s in studs:
            s.password_hash = h
        db.session.commit()
        print(f'OK: {len(profs)} professor(s) and {len(studs)} student(s) now use password {DEFAULT_PASSWORD!r}.')


if __name__ == '__main__':
    main()
