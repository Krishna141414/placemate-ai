"""Week-by-week preparation plan.

The structure of the plan is decided by rules: skill gaps first, then one
topic per round of the company's process in order, and mock interviews in
the final week. The number of weeks follows the application deadline. A
language model only writes the short summary at the top (see
`agent/steps.py`), so the plan itself never depends on which provider is
available.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any

from app.tools.catalog import Company

MIN_WEEKS, MAX_WEEKS = 2, 4
MAX_TASKS_PER_WEEK = 6

TOPICS: dict[str, dict[str, Any]] = {
    "dsa": {
        "focus": "Data structures and algorithms",
        "guide": "Data Structures and Algorithms Preparation Guide",
        "tasks": [
            "Arrays, strings and hash maps: 20 problems, complexity written before checking any solution",
            "Linked lists, stacks and queues: 15 problems",
            "Two timed problems in 45 minutes, three times this week",
        ],
    },
    "dsa_advanced": {
        "focus": "Trees, graphs and dynamic programming",
        "guide": "Data Structures and Algorithms Preparation Guide",
        "tasks": [
            "Trees and heaps: traversals, lowest common ancestor, k-th largest",
            "Graphs: BFS, DFS and connected components",
            "Dynamic programming: knapsack, LCS and LIS patterns",
        ],
    },
    "aptitude": {
        "focus": "Aptitude",
        "guide": "Aptitude Test Preparation Guide",
        "tasks": [
            "30 quantitative questions a day with a timer",
            "One reasoning puzzle type a day (seating, series, blood relations)",
            "One full timed test at the end of the week; review every wrong answer",
        ],
    },
    "sql": {
        "focus": "SQL",
        "guide": "SQL Preparation Guide",
        "tasks": [
            "Joins, GROUP BY and HAVING: 10 queries a day",
            "Window functions: ROW_NUMBER, RANK, LAG and running totals",
            "Write five queries by hand on paper and explain each clause aloud",
        ],
    },
    "system_design": {
        "focus": "System design basics",
        "guide": "System Design Basics Guide",
        "tasks": [
            "Low-level design: a parking lot and a rate limiter, as classes",
            "Read up on idempotency, transactions and caching",
            "Explain one design in 15 minutes to a friend, starting with questions",
        ],
    },
    "projects": {
        "focus": "Your projects",
        "guide": "Resume Writing Guide",
        "tasks": [
            "Walk through every project on your resume: design choices, what you would change",
            "Prepare a two-minute explanation of your strongest project",
        ],
    },
    "practical": {
        "focus": "Practical round",
        "guide": None,
        "tasks": [],
    },
    "group_discussion": {
        "focus": "Group discussion",
        "guide": "HR Interview Preparation Guide",
        "tasks": ["Practise two group discussions with friends on current industry topics"],
    },
    "communication": {
        "focus": "Communication",
        "guide": "HR Interview Preparation Guide",
        "tasks": ["Record three one-minute talks on random topics and listen back", "Read one passage aloud every day"],
    },
    "mock": {
        "focus": "Mock interviews and HR",
        "guide": "HR Interview Preparation Guide",
        "tasks": [
            "Two mock technical interviews with a friend or senior",
            "Prepare four STAR stories: conflict, failure, leadership, learning",
            "Tailor your resume to the role and print three copies",
            "Read the company profile again: bond, location, rounds",
        ],
    },
}

CODING_SKILLS = {"data structures", "algorithms", "python", "java", "c++", "c", "javascript"}


def weeks_until(deadline: date | None, today: date) -> int:
    if deadline is None or deadline <= today:
        return MAX_WEEKS
    return max(MIN_WEEKS, min(MAX_WEEKS, math.ceil((deadline - today).days / 7)))


def _round_topics(company: Company) -> list[str]:
    topics: list[str] = []
    codes = CODING_SKILLS & set(company.required_skills)
    for round_name in company.rounds:
        name = round_name.lower()
        if "aptitude" in name:
            topics.append("aptitude")
        if "coding" in name or ("online assessment" in name and codes):
            topics.append("dsa")
            if company.category == "Dream":
                topics.append("dsa_advanced")
        elif "online assessment" in name:
            topics.append("aptitude")
        if "sql" in name:
            topics.append("sql")
        if "system design" in name or "hiring manager" in name:
            topics.append("system_design")
        if "technical" in name and "interview" in name:
            topics.append("projects")
        if any(word in name for word in ("take-home", "assignment", "lab", "presentation", "written", "task")):
            topics.append(f"practical:{round_name}")
        if "group discussion" in name:
            topics.append("group_discussion")
        if "communication" in name:
            topics.append("communication")
    if "sql" in company.required_skills:
        topics.append("sql")
    if "system design" in company.required_skills + company.preferred_skills:
        topics.append("system_design")
    return list(dict.fromkeys(topics))  # ordered, no duplicates


def _topic_block(key: str, company: Company) -> dict[str, Any]:
    if key.startswith("skill:"):
        skill = key.split(":", 1)[1]
        return {
            "focus": f"Close the gap: {skill}",
            "guide": None,
            "tasks": [
                f"Learn the basics of {skill} with one small exercise a day",
                f"Build or extend one project so your resume shows {skill}",
            ],
        }
    if key.startswith("practical:"):
        round_name = key.split(":", 1)[1]
        return {
            "focus": round_name,
            "guide": None,
            "tasks": [
                f"Read what the {round_name} involves in the {company.name} profile",
                f"Do one practice run of a {round_name.lower()} under the same time limit",
            ],
        }
    return TOPICS[key]


def build_prep_plan(
    company: Company,
    *,
    missing_skills: list[str],
    process_rounds: list[str],
    tips: list[dict[str, str]],
    today: date | None = None,
) -> dict[str, Any]:
    today = today or date.today()
    weeks = weeks_until(company.apply_by, today)

    keys = [f"skill:{skill}" for skill in missing_skills[:3]] + _round_topics(company)
    keys = [key for key in dict.fromkeys(keys) if key != "mock"]
    blocks = [_topic_block(key, company) for key in keys]

    # Spread the topics over every week but the last, in order, then finish
    # with mock interviews.
    study_weeks = max(1, weeks - 1)
    per_week = max(1, math.ceil(len(blocks) / study_weeks)) if blocks else 1
    plan_weeks: list[dict[str, Any]] = []
    for week in range(study_weeks):
        chunk = blocks[week * per_week : (week + 1) * per_week]
        if not chunk:
            chunk = [TOPICS["projects"]] if week == 0 else [TOPICS["dsa"] if CODING_SKILLS & set(company.required_skills) else TOPICS["aptitude"]]
        plan_weeks.append(_week(week + 1, chunk))
    plan_weeks.append(_week(weeks, [TOPICS["mock"]]))

    return {
        "title": f"{weeks}-week plan for {company.name}",
        "company_id": company.id,
        "company_name": company.name,
        "role": company.role,
        "category": company.category,
        "apply_by": company.apply_by.isoformat() if company.apply_by else None,
        "weeks_count": weeks,
        "rounds": process_rounds or company.rounds,
        "focus_skills": missing_skills,
        "weeks": plan_weeks,
        "tips": tips[:6],
        "summary": "",
        "summary_citations": [],
        "summary_sources": [],
        "summary_provider": "",
    }


def _week(number: int, blocks: list[dict[str, Any]]) -> dict[str, Any]:
    tasks: list[str] = []
    for block in blocks:
        tasks.extend(block["tasks"])
    guides = [block["guide"] for block in blocks if block.get("guide")]
    return {
        "week": number,
        "focus": " + ".join(block["focus"] for block in blocks),
        "tasks": tasks[:MAX_TASKS_PER_WEEK],
        "guides": list(dict.fromkeys(guides)),
    }


def template_summary(company: Company, missing_skills: list[str], rounds: list[str]) -> str:
    """Used when no model could write the summary."""
    parts = [f"{company.name} has {len(rounds)} rounds: {', '.join(rounds)}."]
    if missing_skills:
        parts.append(f"The plan starts with the required skills your resume does not show yet: {', '.join(missing_skills)}.")
    parts.append("Each later week follows one round of the process, and the final week is for mock interviews.")
    return " ".join(parts)
