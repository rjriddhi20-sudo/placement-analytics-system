# Placement Analytics (Personal Version)

A small, clean web app that tracks **my own** placement readiness: skills, assessments, projects and placement
records, with rule-based recommendations and an optional Gemini AI layer.

This is a single-student MVP on purpose. The database layer (`src/db.py`) is separate from the pages, so
multi-student support can be added later (see *Future scalability*).

## Objective

Help one student see where they stand for campus placements, what to practise next, and which roles to target.

## Features

| Page | What it does |
|---|---|
| **Dashboard** | Overall Skill Score, Placement Readiness, Projects, Highest Package; one skill chart; "Focus Next" (3 weakest skills with practical actions) |
| **Skills** | Add, edit, change score and remove skills (0-100). Levels: below 60 High Priority, 60-74 Needs Improvement, 75-84 Good, 85+ Excellent |
| **Assessments** | Table (Assessment, Category, Score %, Date, Notes), add/delete, and **Recommendations on the same page**, weakest skill first |
| **Projects** | Add/delete projects: name, description, tech stack, status, GitHub URL, date |
| **Placements** | Company, Role, Package (LPA), Date; Average/Highest Package and Companies; **Roles to Target** |
| **Settings** | Personal profile (name, email, phone, college, degree, year, graduation year, location, goal); shows only whether Gemini is configured |

## Architecture

```
app.py              pages + navigation (Streamlit)
src/ui.py           CSS, cards, badges, progress bars, the skill chart (Plotly)
src/recommendations.py   scores, rule-based engine, optional Gemini call
src/db.py           all SQLite code (sqlite3) - no SQL anywhere else
data/               SQLite file is created here automatically
```

## Database design (SQLite)

| Table | Columns |
|---|---|
| profile | id (always 1), full_name, email, phone, college, degree, current_year, graduation_year, location, goal |
| skills | id, name (unique), score (0-100) |
| assessments | id, name, category, score (0-100), taken_on, notes |
| projects | id, name, description, tech_stack, status, github_url, started_on |
| placements | id, company, role, package (LPA), placed_on |

There is **no students table**. The database and starter data are created automatically on first run; starter data
is inserted only once (it is tracked with SQLite's `user_version`), so deleted rows never come back.
The starter rows are samples - edit or delete them freely.

## Scores and recommendations

- **Overall Skill Score** = simple average of all skills.
- **Placement Readiness** = weighted average: DSA 20%, Core CS 20%, Development 20%, Aptitude 15%,
  Communication 15%, AI/ML 10%. Skills you add yourself get a 10% weight. Weights are re-balanced to the skills you have.
- **Roles to Target** uses the readiness score: 80+ Software Engineer / SDE / Developer; 70-79 Graduate Engineer
  Trainee / Junior Developer; below 70 Internship / Trainee / Junior roles while strengthening fundamentals.
  This is a preparation suggestion, not a hiring guarantee.

## AI functionality

1. **Local engine (always on):** if/else rules turn each skill score into a level and a practical action, weakest first.
2. **Gemini (optional):** if `GEMINI_API_KEY` is set, a button on the Assessments page sends your skill scores and
   recent assessments to the Gemini API and shows a short action plan. If the key is missing or the call fails,
   the app keeps using the local engine. The key is read from `.env`, sent in a request header, and never shown or stored.

   Note: the Gemini call was tested with a mocked network response, not a live key. If your key rejects the default
   model name, set `GEMINI_MODEL` in `.env` to a model available to you.

## Installation (VS Code, Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

(or double-click `run_app.bat`). On macOS/Linux use `source .venv/bin/activate`.

## Gemini configuration (optional)

1. Create a key in Google AI Studio.
2. Copy `.env.example` to `.env` and set `GEMINI_API_KEY=your_key`.
3. Restart the app. Settings will show "Gemini configured".

## GitHub

```powershell
git init
git add .
git commit -m "Placement Analytics personal version"
git branch -M main
git remote add origin https://github.com/<your-username>/placement-analytics.git
git push -u origin main
```
`.env` and the database file are in `.gitignore`, so your key and personal data are not uploaded.

## Future scalability

Because all SQL is in `src/db.py`, the app can grow into a multi-student system by adding a `users`/`students`
table and a `user_id` column to the other tables, then adding login. The pages would not need to change much.

## Agile Kanban Workflow

This project follows an Agile Kanban methodology.

### Workflow

Todo → In Progress → Done

### WIP Limit

A maximum of 3 tasks are kept in the In Progress column at one time.

Tasks are moved from Todo to In Progress when development begins and moved to Done after completion and testing.

### Agile Practices Used

- User Stories
- GitHub Issues
- Priority levels
- Labels
- Milestones
- Kanban board
- WIP limit
- Incremental development
- Testing before completion
