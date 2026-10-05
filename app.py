"""Placement Analytics (personal version).  Run with:  python -m streamlit run app.py"""
from datetime import date

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

st.set_page_config(page_title="Placement Analytics", page_icon="🎓", layout="wide")
load_dotenv()  # reads GEMINI_API_KEY from .env (optional)

from src import db, recommendations as rec, ui  # noqa: E402


@st.cache_resource
def setup_database() -> None:
    db.init_db()  # creates data/, the SQLite file and tables; seeds starter data only once


setup_database()
ui.inject_css()


# ------------------------------------------------------------------ helpers used by several pages
def flash(message: str, kind: str = "success") -> None:
    """Keep a message across the rerun that happens after saving."""
    st.session_state["flash"] = (kind, message)


def show_flash() -> None:
    if "flash" in st.session_state:
        kind, message = st.session_state.pop("flash")
        getattr(st, kind)(message)


def fkey(form: str, field: str) -> str:
    """Widget key that changes after a successful save, which gives a fresh empty form."""
    return f"{form}_{field}_{st.session_state.get(form + '_v', 0)}"


def clear_form(form: str) -> None:
    st.session_state[form + "_v"] = st.session_state.get(form + "_v", 0) + 1


def attempt(action, success_message: str, form: str | None = None) -> None:
    """Run a database action. Show the validation error, or flash success and refresh the page."""
    try:
        action()
    except ValueError as error:
        st.error(str(error))
    except Exception:
        st.error("Something went wrong while saving. Nothing was changed.")
    else:
        flash(success_message)
        if form:
            clear_form(form)
        st.rerun()


def delete_picker(label: str, df: pd.DataFrame, describe, on_delete, noun: str) -> None:
    """Select a row by description and delete it (the tables themselves never show IDs)."""
    if df.empty:
        return
    options = dict(zip(df["id"].astype(int), [describe(row) for row in df.itertuples()]))
    chosen = st.selectbox(label, list(options), format_func=lambda i: options[i], key=f"pick_{noun}")
    if st.button(f"Delete {noun}", key=f"del_{noun}"):
        attempt(lambda: on_delete(int(chosen)), f"{noun.capitalize()} deleted.")


def date_column() -> st.column_config.DateColumn:
    return st.column_config.DateColumn(format="DD MMM YYYY")


# ------------------------------------------------------------------ pages
def dashboard_page() -> None:
    skills, projects, placements = db.list_skills(), db.list_projects(), db.list_placements()
    name = db.get_profile().get("full_name", "").strip()
    ui.page_header("Dashboard", f"Welcome back, {name}" if name else "Your placement preparation at a glance")
    show_flash()

    overall, readiness = rec.overall_score(skills), rec.readiness_score(skills)
    highest = f"{placements['package'].max():g} LPA" if len(placements) else "—"
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        ui.kpi_card("📊", "Overall Skill Score", f"{overall}%", f"Average of {len(skills)} skills", ui.COLORS["blue"])
    with k2:
        ui.kpi_card("🎯", "Placement Readiness", f"{readiness}%", rec.readiness_label(readiness), ui.COLORS["green"])
    with k3:
        done = int((projects["status"] == "Completed").sum())
        ui.kpi_card("💻", "Projects", len(projects), f"{done} completed", ui.COLORS["purple"])
    with k4:
        ui.kpi_card("💰", "Highest Package", highest, f"{len(placements)} record(s)", ui.COLORS["orange"])
    st.write("")

    left, right = st.columns([1.5, 1])
    with left:
        with ui.card("snapshot"):
            ui.card_title("Skill Snapshot", "Weakest skills first")
            if skills.empty:
                ui.empty_note("No skills yet. Add them on the Skills page.")
            else:
                st.plotly_chart(ui.skill_chart(skills), width="stretch", config={"displaylogo": False, "displayModeBar": False})
    with right:
        with ui.card("focus"):
            ui.card_title("Focus Next", "Your three weakest skills")
            weakest = rec.build_recommendations(skills)[:3]
            if not weakest:
                ui.empty_note("Add skills to get recommendations.")
            ui.render_html("".join(
                f'<div class="focus-item"><div class="focus-head"><b>{ui.esc(r["name"])} — {r["score"]}%</b>{ui.badge(r["level"], r["color"])}</div>'
                f'<div class="focus-text">{ui.esc(r["text"])}</div></div>' for r in weakest))


def skills_page() -> None:
    ui.page_header("Skills", "Track your skill scores (0-100). Recommendations update automatically.")
    show_flash()
    skills = db.list_skills()

    if skills.empty:
        ui.empty_note("No skills yet. Add your first skill below.")
    columns = st.columns(3)
    for index, row in enumerate(skills.itertuples()):
        level = rec.skill_level(row.score)
        color = ui.level_color(row.score)
        with columns[index % 3]:
            ui.render_html(f'<div class="skill-card"><div style="display:flex;justify-content:space-between;align-items:center;">'
                           f'<div class="skill-name">{ui.esc(row.name)}</div>{ui.badge(level, color)}</div>'
                           f'<div class="skill-score">{row.score}%</div>{ui.bar_only(row.score, color)}</div>')

    add_col, edit_col = st.columns(2)
    with add_col:
        st.markdown("##### Add skill")
        with st.form("add_skill_form"):
            name = st.text_input("Skill name *", placeholder="e.g. SQL", key=fkey("add_skill", "name"))
            score = st.number_input("Score (0-100) *", 0, 100, 50, key=fkey("add_skill", "score"))
            if st.form_submit_button("Add skill", type="primary"):
                attempt(lambda: db.add_skill(name, score), f"Skill '{name.strip()}' added.", "add_skill")
    with edit_col:
        st.markdown("##### Edit or remove skill")
        if skills.empty:
            ui.empty_note("Nothing to edit yet.")
        else:
            names = dict(zip(skills["id"].astype(int), skills["name"]))
            skill_id = int(st.selectbox("Skill", list(names), format_func=lambda i: names[i]))
            current = skills[skills["id"] == skill_id].iloc[0]
            with st.form("edit_skill_form"):
                new_name = st.text_input("Skill name *", current["name"], key=f"edit_skill_name_{skill_id}")
                new_score = st.number_input("Score (0-100) *", 0, 100, int(current["score"]), key=f"edit_skill_score_{skill_id}")
                if st.form_submit_button("Save changes", type="primary"):
                    attempt(lambda: db.update_skill(skill_id, new_name, new_score), f"Skill '{new_name.strip()}' updated.")
            confirm = st.checkbox(f"Yes, remove {current['name']}", key=f"confirm_remove_skill_{skill_id}")
            if st.button("Remove skill", disabled=not confirm):
                attempt(lambda: db.delete_skill(skill_id), f"Skill '{current['name']}' removed.")


def assessments_page() -> None:
    ui.page_header("Assessments", "Your test results, with recommendations based on your current skills")
    show_flash()
    skills, assessments = db.list_skills(), db.list_assessments()

    with ui.card("assessment_table"):
        ui.card_title("Assessments")
        if assessments.empty:
            ui.empty_note("No assessments yet. Add one below.")
        else:
            table = assessments[["name", "category", "score", "taken_on", "notes"]].copy()
            table["taken_on"] = pd.to_datetime(table["taken_on"])
            table.columns = ["Assessment", "Category", "Score %", "Date", "Notes"]
            st.dataframe(table, hide_index=True, width="stretch",
                         column_config={"Score %": st.column_config.NumberColumn(format="%.0f%%"), "Date": date_column()})

    add_col, del_col = st.columns([2, 1])
    with add_col:
        st.markdown("##### Add assessment")
        categories = list(skills["name"]) + ["Other"]
        with st.form("add_assessment_form"):
            a1, a2 = st.columns(2)
            name = a1.text_input("Assessment *", key=fkey("add_assess", "name"))
            category = a2.selectbox("Category *", categories, key=fkey("add_assess", "cat"))
            a3, a4 = st.columns(2)
            score = a3.number_input("Score % *", 0.0, 100.0, 70.0, 1.0, key=fkey("add_assess", "score"))
            when = a4.date_input("Date *", date.today(), key=fkey("add_assess", "date"))
            notes = st.text_input("Notes", key=fkey("add_assess", "notes"))
            if st.form_submit_button("Add assessment", type="primary"):
                attempt(lambda: db.add_assessment(name, category, score, when, notes), f"Assessment '{name.strip()}' added.", "add_assess")
    with del_col:
        st.markdown("##### Delete assessment")
        delete_picker("Select assessment", assessments, lambda r: f"{r.name} · {r.taken_on}", db.delete_assessment, "assessment")

    # ---- recommendations (same page, directly below) ----
    st.markdown("---")
    st.markdown("## Recommendations")
    recommendations = rec.build_recommendations(skills)
    if not recommendations:
        ui.empty_note("Add skills to see recommendations.")
    for item in recommendations:
        ui.render_html(f'<div class="rec-card" style="border-left-color:{item["color"]};"><div style="display:flex;justify-content:space-between;align-items:center;">'
                       f'<b>{ui.esc(item["name"])} — {item["score"]}%</b>{ui.badge(item["level"], item["color"])}</div>'
                       f'<div class="focus-text">{ui.esc(item["text"])}</div></div>')

    if rec.gemini_configured():
        if st.button("✨ Get AI-assisted suggestions (Gemini)"):
            with st.spinner("Asking Gemini..."):
                try:
                    st.session_state["ai_text"] = rec.gemini_recommendations(skills, assessments)
                except rec.GeminiError as error:
                    st.session_state.pop("ai_text", None)
                    st.warning(f"{error} Showing the built-in recommendations instead.")
        if st.session_state.get("ai_text"):
            with ui.card("ai_box"):
                ui.card_title("AI-assisted suggestions (Gemini)", "Generated from your current skills and recent assessments")
                st.markdown(st.session_state["ai_text"])
    else:
        st.caption("Built-in recommendation engine is active. Add GEMINI_API_KEY to your .env file to enable optional AI-assisted suggestions.")


def projects_page() -> None:
    ui.page_header("Projects", "Your personal project tracker")
    show_flash()
    projects = db.list_projects()

    with ui.card("project_table"):
        ui.card_title("Projects")
        if projects.empty:
            ui.empty_note("No projects yet. Add one below.")
        else:
            table = projects[["name", "description", "tech_stack", "status", "github_url", "started_on"]].copy()
            table["github_url"] = table["github_url"].replace("", None)
            table["started_on"] = pd.to_datetime(table["started_on"])
            table.columns = ["Project", "Description", "Tech Stack", "Status", "GitHub", "Date"]
            st.dataframe(table, hide_index=True, width="stretch",
                         column_config={"GitHub": st.column_config.LinkColumn(display_text="Open"), "Date": date_column()})

    add_col, del_col = st.columns([2, 1])
    with add_col:
        st.markdown("##### Add project")
        with st.form("add_project_form"):
            p1, p2 = st.columns(2)
            name = p1.text_input("Project name *", key=fkey("add_proj", "name"))
            status = p2.selectbox("Status *", db.PROJECT_STATUSES, key=fkey("add_proj", "status"))
            tech = st.text_input("Tech stack * (comma separated)", placeholder="Python, Flask, SQLite", key=fkey("add_proj", "tech"))
            description = st.text_area("Description", key=fkey("add_proj", "desc"))
            p3, p4 = st.columns(2)
            github = p3.text_input("GitHub URL", placeholder="https://github.com/you/project", key=fkey("add_proj", "gh"))
            when = p4.date_input("Date *", date.today(), key=fkey("add_proj", "date"))
            if st.form_submit_button("Add project", type="primary"):
                attempt(lambda: db.add_project(name, description, tech, status, github, when), f"Project '{name.strip()}' added.", "add_proj")
    with del_col:
        st.markdown("##### Delete project")
        delete_picker("Select project", projects, lambda r: r.name, db.delete_project, "project")


def placements_page() -> None:
    ui.page_header("Placements", "Offers and applications, plus roles to target")
    show_flash()
    placements = db.list_placements()

    average = f"{placements['package'].mean():.2f} LPA" if len(placements) else "—"
    highest = f"{placements['package'].max():g} LPA" if len(placements) else "—"
    k1, k2, k3 = st.columns(3)
    with k1:
        ui.kpi_card("💰", "Average Package", average, "Across all records", ui.COLORS["purple"])
    with k2:
        ui.kpi_card("🏆", "Highest Package", highest, "Best offer so far", ui.COLORS["orange"])
    with k3:
        ui.kpi_card("🏢", "Companies", placements["company"].nunique(), "Different companies", ui.COLORS["blue"])
    st.write("")

    with ui.card("placement_table"):
        ui.card_title("Placement records")
        if placements.empty:
            ui.empty_note("No records yet. Add one below.")
        else:
            table = placements[["company", "role", "package", "placed_on"]].copy()
            table["placed_on"] = pd.to_datetime(table["placed_on"])
            table.columns = ["Company", "Role", "Package (LPA)", "Date"]
            st.dataframe(table, hide_index=True, width="stretch",
                         column_config={"Package (LPA)": st.column_config.NumberColumn(format="%.2f"), "Date": date_column()})

    add_col, del_col = st.columns([2, 1])
    with add_col:
        st.markdown("##### Add placement record")
        with st.form("add_placement_form"):
            l1, l2 = st.columns(2)
            company = l1.text_input("Company *", key=fkey("add_place", "company"))
            role = l2.text_input("Role *", key=fkey("add_place", "role"))
            l3, l4 = st.columns(2)
            package = l3.text_input("Package (LPA) *", placeholder="6.5", key=fkey("add_place", "package"))
            when = l4.date_input("Date *", date.today(), key=fkey("add_place", "date"))
            if st.form_submit_button("Add record", type="primary"):
                attempt(lambda: db.add_placement(company, role, package, when), f"Record for '{company.strip()}' added.", "add_place")
    with del_col:
        st.markdown("##### Delete record")
        delete_picker("Select record", placements, lambda r: f"{r.company} · {r.role}", db.delete_placement, "record")

    # ---- roles to target ----
    readiness = rec.readiness_score(db.list_skills())
    level, roles = rec.roles_to_target(readiness)
    with ui.card("roles"):
        ui.card_title("Roles to Target", f"Based on your placement readiness of {readiness}% ({level})")
        ui.render_html(f'<div class="role-box">{ui.esc(roles)}</div>')
        st.caption("This is a preparation suggestion based on your current skill scores, not a hiring guarantee.")


def settings_page() -> None:
    ui.page_header("Settings", "Your personal profile")
    show_flash()
    profile = db.get_profile()
    with st.form("profile_form"):
        s1, s2 = st.columns(2)
        full_name = s1.text_input("Full Name", profile["full_name"] or "")
        email = s2.text_input("Email", profile["email"] or "")
        s3, s4 = st.columns(2)
        phone = s3.text_input("Phone", profile["phone"] or "")
        college = s4.text_input("College", profile["college"] or "")
        s5, s6, s7 = st.columns(3)
        degree = s5.text_input("Degree", profile["degree"] or "")
        current_year = s6.selectbox("Current Year", [1, 2, 3, 4], index=[1, 2, 3, 4].index(profile["current_year"] or 3))
        graduation_year = s7.number_input("Graduation Year", 2000, 2100, int(profile["graduation_year"] or date.today().year + 1))
        location = st.text_input("Location", profile["location"] or "")
        goal = st.text_area("Short Profile / Goal", profile["goal"] or "")
        if st.form_submit_button("Update Profile", type="primary"):
            attempt(lambda: db.save_profile(full_name=full_name.strip(), email=email.strip(), phone=phone.strip(), college=college.strip(),
                                            degree=degree.strip(), current_year=current_year, graduation_year=int(graduation_year),
                                            location=location.strip(), goal=goal.strip()), "Profile updated.")

    with ui.card("gemini_status"):
        ui.card_title("AI recommendations (optional)")
        if rec.gemini_configured():
            ui.render_html(ui.badge("Gemini configured", ui.COLORS["green"]))
        else:
            ui.render_html(ui.badge("Gemini not configured", ui.COLORS["grey"]))
            st.caption("The app works fully without it. To enable AI-assisted suggestions, set GEMINI_API_KEY in your .env file.")


# ------------------------------------------------------------------ navigation
PAGES = [
    st.Page(dashboard_page, title="Dashboard", icon=":material/dashboard:", url_path="dashboard", default=True),
    st.Page(skills_page, title="Skills", icon=":material/psychology:", url_path="skills"),
    st.Page(assessments_page, title="Assessments", icon=":material/quiz:", url_path="assessments"),
    st.Page(projects_page, title="Projects", icon=":material/code_blocks:", url_path="projects"),
    st.Page(placements_page, title="Placements", icon=":material/work:", url_path="placements"),
    st.Page(settings_page, title="Settings", icon=":material/settings:", url_path="settings"),
]
navigation = st.navigation(PAGES, position="hidden")  # our own dark sidebar replaces the default menu
with st.sidebar:
    ui.render_html('<div class="brand"><div class="brand-logo">🎓</div><div><div class="brand-title">Placement Analytics</div>'
                   '<div class="brand-sub">Personal readiness tracker</div></div></div>')
    for page in PAGES:
        st.page_link(page)
navigation.run()
