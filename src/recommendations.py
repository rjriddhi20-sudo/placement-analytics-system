"""Scores, rule-based recommendations and the optional Gemini layer.

The local (rule-based) engine always works. Gemini is only an optional extra:
the app never depends on it and never stores or shows the API key.
"""
import json
import os
import urllib.error
import urllib.request

import pandas as pd

# Weights for the six core skills. Any skill you add yourself gets DEFAULT_WEIGHT.
CORE_WEIGHTS = {"dsa": 0.20, "aptitude": 0.15, "core cs": 0.20, "development": 0.20, "ai/ml": 0.10, "communication": 0.15}
DEFAULT_WEIGHT = 0.10

TIPS = {
    "dsa": "Practice arrays, linked lists, trees, graphs and dynamic programming.",
    "aptitude": "Practice quantitative aptitude, logical reasoning and verbal ability.",
    "core cs": "Revise DBMS, Operating Systems, Computer Networks and OOP.",
    "development": "Build more projects and strengthen Git, APIs and deployment.",
    "ai/ml": "Practice Python, data preprocessing, machine learning algorithms and model evaluation.",
    "communication": "Practice technical interviews, presentations and group discussions.",
    "sql": "Practice joins, GROUP BY, subqueries, indexes and normalisation on real datasets.",
}
LEVEL_COLORS = {"High Priority": "#DC2626", "Needs Improvement": "#F97316", "Good": "#2563EB", "Excellent": "#16A34A"}


def skill_level(score: float) -> str:
    if score < 60:
        return "High Priority"
    if score < 75:
        return "Needs Improvement"
    if score < 85:
        return "Good"
    return "Excellent"


def tip_for(skill_name: str) -> str:
    return TIPS.get(skill_name.strip().lower(),
                    f"Practise {skill_name} a little every day, build one small exercise and review your mistakes weekly.")


def overall_score(skills: pd.DataFrame) -> float:
    """Plain average of all skill scores."""
    return round(float(skills["score"].mean()), 1) if len(skills) else 0.0


def readiness_score(skills: pd.DataFrame) -> float:
    """Weighted average (see CORE_WEIGHTS), so DSA/Core CS/Development count more than the rest."""
    if skills.empty:
        return 0.0
    weights = [CORE_WEIGHTS.get(name.strip().lower(), DEFAULT_WEIGHT) for name in skills["name"]]
    return round(sum(s * w for s, w in zip(skills["score"], weights)) / sum(weights), 1)


def readiness_label(score: float) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 80:
        return "Very Good"
    if score >= 70:
        return "Good"
    if score >= 60:
        return "Average"
    return "Needs Improvement"


def build_recommendations(skills: pd.DataFrame) -> list[dict]:
    """One recommendation per skill, weakest first."""
    items = []
    for name, score in zip(skills["name"], skills["score"]):
        level = skill_level(score)
        items.append({"name": name, "score": int(score), "level": level, "color": LEVEL_COLORS[level],
                      "text": tip_for(name) if level != "Excellent" else f"Excellent. Keep {name} sharp with regular mock tests."})
    return sorted(items, key=lambda item: item["score"])


def roles_to_target(readiness: float) -> tuple[str, str]:
    """(preparation level, roles to aim for). A suggestion only, not a hiring guarantee."""
    if readiness >= 80:
        return "Strong preparation", "Software Engineer / SDE / Developer"
    if readiness >= 70:
        return "Good preparation", "Graduate Engineer Trainee / Junior Developer"
    return "Building fundamentals", "Internship / Trainee / Junior roles while strengthening fundamentals"


# ------------------------------------------------------------------ optional Gemini layer
class GeminiError(Exception):
    """Raised when the optional AI call fails; the app then keeps using the local engine."""


def gemini_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def gemini_recommendations(skills: pd.DataFrame, assessments: pd.DataFrame, timeout: int = 25) -> str:
    """Ask Gemini for short, practical advice. The key is read from the environment and sent in a header."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise GeminiError("GEMINI_API_KEY is not configured.")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    skill_lines = "\n".join(f"- {n}: {int(s)}%" for n, s in zip(skills["name"], skills["score"]))
    recent = assessments.head(5)
    test_lines = "\n".join(f"- {n} ({c}): {s:.0f}% - {note}" for n, c, s, note in
                           zip(recent["name"], recent["category"], recent["score"], recent["notes"])) or "- none yet"
    prompt = ("You are a placement mentor for an Indian BTech student. Based on the data below, give a short, practical "
              "plan: for the 3 weakest skills give 2 concrete actions each for the next 2 weeks. Maximum 180 words, "
              "plain bullet points, no introduction.\n\nSkills:\n" + skill_lines + "\n\nRecent assessments:\n" + test_lines)
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1200}}).encode("utf-8")
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", data=body, method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.load(response)
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except urllib.error.HTTPError as error:
        raise GeminiError(f"Gemini returned an error (HTTP {error.code}). Check your key and model name.") from None
    except (urllib.error.URLError, TimeoutError):
        raise GeminiError("Could not reach Gemini. Check your internet connection.") from None
    except (KeyError, IndexError, ValueError):
        raise GeminiError("Gemini returned an unexpected response.") from None
