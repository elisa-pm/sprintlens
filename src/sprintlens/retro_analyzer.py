"""Retrospective analyzer.

Reads retrospective notes written in Markdown, classifies each bullet into a fixed
theme taxonomy, and produces a report with recurring themes, trends, risks, and
draft action items.

Two classification modes:
    offline (default)  keyword rules, deterministic, needs no network or API key
    llm                uses the Anthropic API when ANTHROPIC_API_KEY is set

Expected note format (headings are matched loosely, case-insensitive):
    ## What went well
    - bullet
    ## What did not go well      (or "What to improve")
    - bullet
    ## Action items
    - bullet

Privacy: only run this on notes you are allowed to share. In llm mode the text of
each bullet is sent to the API. Use anonymized or synthetic notes for demos.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

# theme -> (keywords, suggested action)
TAXONOMY: dict[str, tuple[list[str], str]] = {
    "Requirements clarity": (
        ["acceptance criteria", "unclear", "requirement", "ambigu", "definition of ready", "refinement", "rework"],
        "Introduce or enforce a Definition of Ready and review acceptance criteria with the Product Owner before planning.",
    ),
    "Dependencies and blockers": (
        ["depend", "blocked", "blocker", "waiting on", "external", "handoff"],
        "Add a dependency check to refinement and raise blockers in the daily standup the same day.",
    ),
    "Scope change": (
        ["mid-sprint", "scope", "added", "changed after", "new work"],
        "Adopt a swap rule: new mid-sprint work must replace an item of equal size.",
    ),
    "Testing and quality": (
        ["qa", "test", "regression", "defect", "bug", "environment"],
        "Start testing as each story completes and secure a stable test environment window per sprint.",
    ),
    "Work in progress and flow": (
        ["in progress", "wip", "too many items", "finished", "smaller stories", "split"],
        "Set a WIP limit per person and split stories above five points before they enter a sprint.",
    ),
    "Capacity and estimation": (
        ["capacity", "estimat", "leave", "overestimat", "velocity", "sizing"],
        "Record planned leave before planning and calibrate estimates against the last three sprints.",
    ),
    "Communication and collaboration": (
        ["communicat", "standup", "pairing", "collaborat", "meeting", "attend", "demo", "stakeholder"],
        "Timebox ceremonies with a fixed agenda and confirm attendance of required roles.",
    ),
    "Release and documentation": (
        ["release", "documentation", "release notes", "deploy"],
        "Draft release notes during the sprint, not at the end.",
    ),
}
OTHER = "Other"

SECTION_PATTERNS = {
    "well": re.compile(r"went well|keep|positive", re.I),
    "improve": re.compile(r"not go well|improve|didn.t|did not|problem|challenge", re.I),
    "action": re.compile(r"action", re.I),
}


@dataclass
class RetroItem:
    sprint: int
    section: str  # well | improve | action
    text: str
    theme: str = OTHER


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_retro(path: Path) -> list[RetroItem]:
    match = re.search(r"(\d+)", path.stem)
    if not match:
        raise ValueError(f"Cannot infer sprint number from file name: {path.name}")
    sprint = int(match.group(1))
    items: list[RetroItem] = []
    section: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            section = next((k for k, p in SECTION_PATTERNS.items() if p.search(stripped)), None)
        elif section and re.match(r"^[-*]\s+", stripped):
            items.append(RetroItem(sprint, section, re.sub(r"^[-*]\s+", "", stripped)))
    return items


def load_retros(directory: str | Path) -> list[RetroItem]:
    items: list[RetroItem] = []
    for p in sorted(Path(directory).glob("*.md")):
        items.extend(parse_retro(p))
    return items


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_text_offline(text: str) -> str:
    lowered = text.lower()
    best, best_score = OTHER, 0
    for theme, (keywords, _) in TAXONOMY.items():
        score = sum(1 for k in keywords if k in lowered)
        if score > best_score:
            best, best_score = theme, score
    return best


def classify_offline(items: list[RetroItem]) -> list[RetroItem]:
    for it in items:
        it.theme = classify_text_offline(it.text)
    return items


def make_anthropic_completer(model: str | None = None) -> Callable[[str], str]:
    """Return a function that sends a prompt to the Anthropic API and returns text."""
    import anthropic  # imported lazily so offline mode has no dependency on it

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    model_name = model or os.environ.get("SPRINTLENS_MODEL", "claude-sonnet-5-5")

    def complete(prompt: str) -> str:
        msg = client.messages.create(
            model=model_name,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")

    return complete


def classify_llm(items: list[RetroItem], complete: Callable[[str], str]) -> list[RetroItem]:
    """Classify items with an LLM. Any item the model skips falls back to offline rules."""
    themes = list(TAXONOMY) + [OTHER]
    numbered = "\n".join(f"{n}: {it.text}" for n, it in enumerate(items))
    prompt = (
        "You classify Scrum retrospective bullets into exactly one theme each.\n"
        f"Allowed themes: {json.dumps(themes)}.\n"
        'Return only a JSON array of objects like {"id": 0, "theme": "..."} covering every id.\n\n'
        f"Bullets:\n{numbered}"
    )
    classify_offline(items)  # baseline, overwritten where the model answers validly
    try:
        raw = complete(prompt)
        match = re.search(r"\[.*\]", raw, re.S)
        for row in json.loads(match.group(0)) if match else []:
            idx, theme = row.get("id"), row.get("theme")
            if isinstance(idx, int) and 0 <= idx < len(items) and theme in themes:
                items[idx].theme = theme
    except Exception as exc:  # network, parsing, or auth problems must not break the report
        print(f"LLM classification failed, using offline rules: {exc}")
    return items


# ---------------------------------------------------------------------------
# Aggregation and reporting
# ---------------------------------------------------------------------------

def to_frame(items: list[RetroItem]) -> pd.DataFrame:
    return pd.DataFrame([it.__dict__ for it in items])


def theme_matrix(df: pd.DataFrame, section: str = "improve") -> pd.DataFrame:
    """Theme x sprint counts for one section."""
    sub = df[df.section == section]
    if sub.empty:
        return pd.DataFrame()
    return sub.pivot_table(index="theme", columns="sprint", values="text", aggfunc="count", fill_value=0)


def analyze(df: pd.DataFrame, recurring_min_sprints: int = 3) -> pd.DataFrame:
    """Per-theme summary for improvement items: mentions, spread, trend, status."""
    matrix = theme_matrix(df, "improve")
    if matrix.empty:
        return pd.DataFrame()
    sprints = sorted(matrix.columns)
    half = len(sprints) // 2 or 1
    early, late = sprints[:half], sprints[half:]
    last3 = sprints[-3:]
    rows = []
    for theme, counts in matrix.iterrows():
        e, l = counts[early].sum(), counts[late].sum()
        trend = "improving" if l < e else "worsening" if l > e else "stable"
        rows.append(
            {
                "theme": theme,
                "mentions": int(counts.sum()),
                "sprints_mentioned": int((counts > 0).sum()),
                "recent_mentions": int(counts[last3].sum()),
                "trend": trend,
                "recurring": bool((counts > 0).sum() >= recurring_min_sprints),
            }
        )
    out = pd.DataFrame(rows).sort_values(["mentions", "sprints_mentioned"], ascending=False)
    return out.reset_index(drop=True)


def draft_actions(summary: pd.DataFrame, limit: int = 4) -> list[dict]:
    """Draft actions for themes that are recurring or still active in recent sprints."""
    actions = []
    focus = summary[(summary.recurring) | (summary.recent_mentions > 0)]
    for row in focus.head(limit).itertuples():
        text = TAXONOMY.get(row.theme, ([], "Discuss this theme in the next retrospective and agree an owner."))[1]
        actions.append({"theme": row.theme, "action": text, "owner": "To be agreed by the team", "review": "Next retrospective"})
    return actions


def risks(summary: pd.DataFrame) -> list[str]:
    out = []
    for row in summary.itertuples():
        if row.trend == "worsening" and row.recent_mentions > 0:
            out.append(f"{row.theme}: mentions are increasing ({row.recent_mentions} in the last three sprints).")
        elif row.recurring and row.recent_mentions >= 2:
            out.append(f"{row.theme}: recurring across {row.sprints_mentioned} sprints and still active.")
    return out


def build_report(items: list[RetroItem], mode: str = "offline", narrative: str | None = None) -> str:
    df = to_frame(items)
    summary = analyze(df)
    n_sprints = df.sprint.nunique()
    positives = (
        df[df.section == "well"].groupby("theme").size().sort_values(ascending=False).head(3)
    )
    lines = [
        "# Retrospective Analysis",
        "",
        f"Sprints analyzed: {n_sprints}. Items classified: {len(df)}. Mode: {mode}.",
        "",
    ]
    if narrative:
        lines += ["## Summary", "", narrative.strip(), ""]
    lines += ["## Recurring themes", ""]
    if summary.empty:
        lines += ["No improvement items found.", ""]
    else:
        lines += ["| Theme | Mentions | Sprints | Recent (last 3) | Trend | Recurring |", "|---|---|---|---|---|---|"]
        for r in summary.itertuples():
            lines.append(
                f"| {r.theme} | {r.mentions} | {r.sprints_mentioned} | {r.recent_mentions} | {r.trend} | {'yes' if r.recurring else 'no'} |"
            )
        lines.append("")
        lines += ["## Risks to watch", ""]
        flagged = risks(summary)
        lines += [f"- {x}" for x in flagged] or ["- No worsening or persistent themes detected."]
        lines += ["", "## Draft action items", ""]
        for a in draft_actions(summary):
            lines.append(f"- **{a['theme']}**: {a['action']} Owner: {a['owner']}. Review: {a['review']}.")
        lines.append("")
    if not positives.empty:
        lines += ["## Practices worth keeping", ""]
        lines += [f"- {theme} ({count} positive mentions)" for theme, count in positives.items()]
        lines.append("")
    lines += [
        "## Method",
        "",
        "Each retrospective bullet is assigned one theme from a fixed taxonomy. A theme is recurring when it "
        "appears under improvement items in at least three sprints. Trend compares the first and second half of the "
        "analyzed sprints. Draft actions are suggestions for the team to refine, not decisions.",
        "",
    ]
    return "\n".join(lines)


def narrative_llm(summary: pd.DataFrame, complete: Callable[[str], str]) -> str | None:
    if summary.empty:
        return None
    prompt = (
        "You are a Scrum Master. Write a three-sentence plain-English summary of these retrospective "
        "theme statistics for a team. Be factual, avoid blame, and do not use em dashes.\n\n"
        + summary.to_csv(index=False)
    )
    try:
        return complete(prompt)
    except Exception as exc:
        print(f"LLM summary failed, omitting: {exc}")
        return None


def run(retro_dir: str, out_path: str, use_llm: bool = False) -> str:
    items = load_retros(retro_dir)
    if not items:
        raise SystemExit(f"No retrospective bullets found in {retro_dir}")
    narrative = None
    mode = "offline"
    if use_llm:
        complete = make_anthropic_completer()
        classify_llm(items, complete)
        narrative = narrative_llm(analyze(to_frame(items)), complete)
        mode = "llm"
    else:
        classify_offline(items)
    report = build_report(items, mode, narrative)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(report, encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze sprint retrospective notes.")
    parser.add_argument("--retros", default="data/retros")
    parser.add_argument("--out", default="reports/retro_report.md")
    parser.add_argument("--llm", action="store_true", help="classify with the Anthropic API")
    args = parser.parse_args()
    run(args.retros, args.out, args.llm)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
