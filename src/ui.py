"""Look and feel: CSS, HTML building blocks (cards, badges, progress bars) and the one chart."""
import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import recommendations as rec

COLORS = {"navy": "#0B1F3A", "blue": "#2563EB", "green": "#16A34A", "red": "#DC2626",
          "orange": "#F97316", "purple": "#7C3AED", "grey": "#64748B"}

CSS = """
.stApp { background: #F4F7FB; }
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1300px; }
header[data-testid="stHeader"] { background: transparent; }
h1, h2, h3, h4 { color: #0B1F3A; letter-spacing: -0.01em; }
[data-testid="stSidebar"] { background: #0B1F3A; border-right: none; }
.brand { display: flex; align-items: center; gap: 12px; padding: 14px 8px 22px 8px; }
.brand-logo { width: 42px; height: 42px; border-radius: 12px; background: #2563EB; display: flex; align-items: center; justify-content: center; font-size: 22px; }
.brand-title { color: #FFFFFF; font-weight: 700; font-size: 15px; line-height: 1.2; }
.brand-sub { color: #94A3B8; font-size: 12px; }
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] { border-radius: 10px; padding: 0.55rem 0.8rem; margin-bottom: 2px; }
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] p, [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] span { color: #CBD5E1; font-size: 15px; }
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover { background: rgba(255,255,255,0.08); }
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"] { background: #2563EB; }
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"] p, [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"] span { color: #FFFFFF; font-weight: 600; }
.page-title { font-size: 28px; font-weight: 700; color: #0B1F3A; margin: 0; line-height: 1.2; }
.page-subtitle { color: #64748B; font-size: 14px; margin: 2px 0 16px 0; }
[class*="st-key-card_"] { background: #FFFFFF; border: 1px solid #E2E8F0 !important; border-radius: 16px; box-shadow: 0 1px 3px rgba(15,23,42,0.06); padding: 1rem 1.1rem; }
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] { height: 100%; }
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:has([class*="st-key-card_"]) { flex: 1; }
.card-title { font-weight: 650; font-size: 16px; color: #0B1F3A; margin-bottom: 2px; }
.card-note { color: #64748B; font-size: 13px; margin-bottom: 8px; }
.kpi { min-height: 100px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px; padding: 16px; box-shadow: 0 1px 3px rgba(15,23,42,0.06); display: flex; gap: 12px; align-items: center; }
.kpi > div:last-child { min-width: 0; }
.kpi-icon { width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; }
.kpi-label { color: #64748B; font-size: 12.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.kpi-value { color: #0B1F3A; font-size: 28px; font-weight: 700; line-height: 1.15; white-space: nowrap; }
.kpi-sub { font-size: 12.5px; font-weight: 500; }
.bar-row { margin-bottom: 12px; }
.bar-head { display: flex; justify-content: space-between; font-size: 13.5px; color: #334155; margin-bottom: 5px; }
.bar-track { background: #E8EEF6; border-radius: 999px; height: 9px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 999px; }
.badge { display: inline-block; padding: 3px 11px; border-radius: 999px; font-size: 12px; font-weight: 600; white-space: nowrap; }
.skill-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px; padding: 16px 18px; box-shadow: 0 1px 3px rgba(15,23,42,0.06); margin-bottom: 14px; }
.skill-name { font-weight: 650; font-size: 15.5px; color: #0B1F3A; }
.skill-score { font-size: 30px; font-weight: 700; color: #0B1F3A; margin: 4px 0 8px 0; }
.focus-item { padding: 11px 0; border-bottom: 1px solid #EEF2F7; }
.focus-item:last-child { border-bottom: none; }
.focus-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; font-size: 14.5px; color: #0B1F3A; }
.focus-text { color: #475569; font-size: 13.5px; margin-top: 4px; }
.rec-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 5px solid #2563EB; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(15,23,42,0.05); }
.empty-note { color: #64748B; font-size: 14px; padding: 18px 0; text-align: center; }
.role-box { background: #EFF6FF; border-radius: 12px; padding: 14px 16px; color: #0B1F3A; font-size: 16px; font-weight: 600; margin: 8px 0; }
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"] { border-radius: 10px; font-weight: 600; }
button[data-testid="stBaseButton-secondary"], button[data-testid="stBaseButton-secondaryFormSubmit"] { border-radius: 10px; }
[data-testid="stForm"] { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px; padding: 1.2rem; }
[data-testid="stDataFrame"] { border: 1px solid #E2E8F0; border-radius: 12px; overflow: hidden; }
"""


def inject_css() -> None:
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


# ------------------------------------------------------------------ small helpers
def esc(value) -> str:
    """Escape text before putting it inside HTML."""
    return html.escape(str(value))


def render_html(markup: str) -> None:
    """Collapse line breaks/indentation so Markdown never turns the HTML into a code block."""
    st.markdown(" ".join(line.strip() for line in markup.strip().splitlines()), unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    render_html(f'<div class="page-title">{esc(title)}</div><div class="page-subtitle">{esc(subtitle)}</div>')


def card(name: str):
    """White rounded card. `name` must be unique on the page."""
    return st.container(border=True, key=f"card_{name}")


def card_title(text: str, note: str = "") -> None:
    note_html = f'<div class="card-note">{esc(note)}</div>' if note else ""
    render_html(f'<div class="card-title">{esc(text)}</div>{note_html}')


def kpi_card(icon: str, label: str, value, sub: str = "", color: str = COLORS["blue"]) -> None:
    render_html(f"""
        <div class="kpi"><div class="kpi-icon" style="background:{color}1A;">{icon}</div>
        <div><div class="kpi-label">{esc(label)}</div><div class="kpi-value">{esc(value)}</div>
        <div class="kpi-sub" style="color:{color};">{esc(sub)}</div></div></div>
    """)


def badge(text: str, color: str) -> str:
    return f'<span class="badge" style="background:{color}1A;color:{color};">{esc(text)}</span>'


def empty_note(message: str) -> None:
    render_html(f'<div class="empty-note">{esc(message)}</div>')


def progress_bar(label: str, score: float, color: str) -> str:
    return (f'<div class="bar-row"><div class="bar-head"><span>{esc(label)}</span><b>{score:.0f}%</b></div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{score:.0f}%;background:{color};"></div></div></div>')


def bar_only(score: float, color: str) -> str:
    return f'<div class="bar-track"><div class="bar-fill" style="width:{score:.0f}%;background:{color};"></div></div>'


def level_color(score: float) -> str:
    return rec.LEVEL_COLORS[rec.skill_level(score)]


def skill_chart(skills: pd.DataFrame) -> go.Figure:
    """The one chart: horizontal bars, weakest skill at the top, coloured by level."""
    data = skills.sort_values("score")
    fig = go.Figure(go.Bar(x=data["score"], y=data["name"], orientation="h", marker_color=[level_color(s) for s in data["score"]],
                           text=data["score"], texttemplate="%{text}%", textposition="outside", hovertemplate="%{y}: %{x}%<extra></extra>"))
    fig.update_xaxes(range=[0, 108], showgrid=False, visible=False)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_layout(height=max(260, 48 * len(data) + 40), margin=dict(l=8, r=8, t=8, b=8), bargap=0.4,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Segoe UI, Roboto, Helvetica, Arial, sans-serif", size=13, color="#334155"))
    return fig
