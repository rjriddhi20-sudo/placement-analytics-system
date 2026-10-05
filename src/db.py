"""SQLite data layer. All SQL lives in this file, so the UI never touches the database directly.

Keeping it separate means the storage can later be swapped for a multi-user database
(for example by adding a user_id column) without rewriting the pages.
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("PLACEMENT_DB_PATH", BASE_DIR / "data" / "placement_analytics.db"))

PROJECT_STATUSES = ["Planned", "In Progress", "Completed"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),          -- exactly one row: this is a personal app
    full_name TEXT, email TEXT, phone TEXT, college TEXT, degree TEXT,
    current_year INTEGER, graduation_year INTEGER, location TEXT, goal TEXT
);
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100)
);
CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, category TEXT NOT NULL,
    score REAL NOT NULL CHECK (score BETWEEN 0 AND 100),
    taken_on TEXT NOT NULL, notes TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, description TEXT DEFAULT '', tech_stack TEXT DEFAULT '',
    status TEXT NOT NULL, github_url TEXT DEFAULT '', started_on TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS placements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL, role TEXT NOT NULL,
    package REAL NOT NULL CHECK (package > 0),      -- LPA (lakhs per annum)
    placed_on TEXT NOT NULL
);
"""

# Starter data (all of it can be edited or deleted from the app)
SEED_SKILLS = [("DSA", 64), ("Aptitude", 81), ("Core CS", 68), ("Development", 84), ("AI/ML", 76), ("Communication", 88)]
SEED_ASSESSMENTS = [
    ("DSA Test 1", "DSA", 72, "2026-10-04", "Graphs weak"),
    ("Aptitude Test", "Aptitude", 84, "2026-10-02", "Good"),
    ("Core CS Quiz", "Core CS", 66, "2026-09-25", "Revise OS scheduling"),
]
SEED_PROJECTS = [
    ("Placement Analytics", "Personal placement readiness tracker.", "Python, Streamlit, SQLite, Plotly",
     "In Progress", "", "2026-09-15"),
    ("Expense Tracker", "Tracks daily expenses with monthly summaries.", "Flask, SQLite", "Completed", "", "2026-06-10"),
]
SEED_PLACEMENTS = [
    ("Zensar Technologies", "Graduate Engineer Trainee", 4.5, "2026-09-21"),
    ("Persistent Systems", "Software Engineer", 7.5, "2026-09-01"),
    ("Cognizant", "Programmer Analyst", 4.0, "2026-08-12"),
]


@contextmanager
def connect():
    """Open a connection; commit on success, roll back on error, always close."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    """Create the data folder, database and tables; insert starter data only once."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript(SCHEMA)
        db.execute("INSERT OR IGNORE INTO profile (id, full_name) VALUES (1, '')")
        if db.execute("PRAGMA user_version").fetchone()[0] == 0:  # 0 = never seeded
            db.executemany("INSERT INTO skills (name, score) VALUES (?, ?)", SEED_SKILLS)
            db.executemany("INSERT INTO assessments (name, category, score, taken_on, notes) VALUES (?,?,?,?,?)", SEED_ASSESSMENTS)
            db.executemany("INSERT INTO projects (name, description, tech_stack, status, github_url, started_on) VALUES (?,?,?,?,?,?)", SEED_PROJECTS)
            db.executemany("INSERT INTO placements (company, role, package, placed_on) VALUES (?,?,?,?)", SEED_PLACEMENTS)
            db.execute("PRAGMA user_version = 1")  # remember that seeding is done (even if rows are deleted later)


# ------------------------------------------------------------------ validation helpers
def _text(value, label: str, required: bool = True) -> str:
    value = (value or "").strip()
    if required and not value:
        raise ValueError(f"{label} is required.")
    return value


def _score(value, label: str = "Score") -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number.") from None
    if not 0 <= number <= 100:
        raise ValueError(f"{label} must be between 0 and 100.")
    return number


def _iso(value) -> str:
    return value.isoformat() if isinstance(value, date) else str(value)


def _read(query: str, columns: list[str]) -> pd.DataFrame:
    with connect() as db:
        rows = db.execute(query).fetchall()
    return pd.DataFrame([tuple(r) for r in rows], columns=columns)


# ------------------------------------------------------------------ profile
PROFILE_FIELDS = ["full_name", "email", "phone", "college", "degree", "current_year", "graduation_year", "location", "goal"]


def get_profile() -> dict:
    with connect() as db:
        return dict(db.execute("SELECT * FROM profile WHERE id = 1").fetchone())


def save_profile(**fields) -> None:
    email = (fields.get("email") or "").strip()
    if email and not ("@" in email and "." in email.split("@")[-1] and " " not in email):
        raise ValueError("Please enter a valid email address.")
    values = [fields.get(name) for name in PROFILE_FIELDS]
    with connect() as db:
        db.execute(f"UPDATE profile SET {', '.join(f'{n} = ?' for n in PROFILE_FIELDS)} WHERE id = 1", values)


# ------------------------------------------------------------------ skills
def list_skills() -> pd.DataFrame:
    return _read("SELECT id, name, score FROM skills ORDER BY id", ["id", "name", "score"])


def add_skill(name: str, score) -> None:
    name, score = _text(name, "Skill name"), _score(score)
    try:
        with connect() as db:
            db.execute("INSERT INTO skills (name, score) VALUES (?, ?)", (name, int(score)))
    except sqlite3.IntegrityError:
        raise ValueError(f"A skill named '{name}' already exists.") from None


def update_skill(skill_id: int, name: str, score) -> None:
    name, score = _text(name, "Skill name"), _score(score)
    try:
        with connect() as db:
            db.execute("UPDATE skills SET name = ?, score = ? WHERE id = ?", (name, int(score), skill_id))
    except sqlite3.IntegrityError:
        raise ValueError(f"A skill named '{name}' already exists.") from None


def delete_skill(skill_id: int) -> None:
    with connect() as db:
        db.execute("DELETE FROM skills WHERE id = ?", (skill_id,))


# ------------------------------------------------------------------ assessments
def list_assessments() -> pd.DataFrame:
    return _read("SELECT id, name, category, score, taken_on, notes FROM assessments ORDER BY taken_on DESC, id DESC",
                 ["id", "name", "category", "score", "taken_on", "notes"])


def add_assessment(name: str, category: str, score, taken_on, notes: str = "") -> None:
    name, category = _text(name, "Assessment name"), _text(category, "Category")
    score = _score(score, "Score %")
    with connect() as db:
        db.execute("INSERT INTO assessments (name, category, score, taken_on, notes) VALUES (?,?,?,?,?)",
                   (name, category, score, _iso(taken_on), (notes or "").strip()))


def delete_assessment(assessment_id: int) -> None:
    with connect() as db:
        db.execute("DELETE FROM assessments WHERE id = ?", (assessment_id,))


# ------------------------------------------------------------------ projects
def list_projects() -> pd.DataFrame:
    return _read("SELECT id, name, description, tech_stack, status, github_url, started_on FROM projects ORDER BY started_on DESC, id DESC",
                 ["id", "name", "description", "tech_stack", "status", "github_url", "started_on"])


def add_project(name: str, description: str, tech_stack: str, status: str, github_url: str, started_on) -> None:
    name, tech_stack = _text(name, "Project name"), _text(tech_stack, "Tech stack")
    github_url = (github_url or "").strip()
    if status not in PROJECT_STATUSES:
        raise ValueError("Please choose a valid status.")
    if github_url and not github_url.lower().startswith(("http://", "https://")):
        raise ValueError("GitHub URL must start with http:// or https://")
    with connect() as db:
        db.execute("INSERT INTO projects (name, description, tech_stack, status, github_url, started_on) VALUES (?,?,?,?,?,?)",
                   (name, (description or "").strip(), tech_stack, status, github_url, _iso(started_on)))


def delete_project(project_id: int) -> None:
    with connect() as db:
        db.execute("DELETE FROM projects WHERE id = ?", (project_id,))


# ------------------------------------------------------------------ placements
def list_placements() -> pd.DataFrame:
    return _read("SELECT id, company, role, package, placed_on FROM placements ORDER BY placed_on DESC, id DESC",
                 ["id", "company", "role", "package", "placed_on"])


def add_placement(company: str, role: str, package, placed_on) -> None:
    company, role = _text(company, "Company"), _text(role, "Role")
    try:
        package = float(str(package).strip())
    except ValueError:
        raise ValueError("Package must be a number (for example 6.5).") from None
    if package <= 0:
        raise ValueError("Package must be greater than 0.")
    with connect() as db:
        db.execute("INSERT INTO placements (company, role, package, placed_on) VALUES (?,?,?,?)",
                   (company, role, package, _iso(placed_on)))


def delete_placement(placement_id: int) -> None:
    with connect() as db:
        db.execute("DELETE FROM placements WHERE id = ?", (placement_id,))
