"""Generate a fully synthetic Scrum dataset.

Nothing here comes from a real employer, client, or team. The data tells a
deliberate story so the dashboard has something to show: a team starts with
unclear stories and high carryover, introduces a Definition of Ready at sprint 5,
and improves over the following sprints.

Outputs (written to the target directory):
    sprints.csv        one row per sprint
    issues.csv         one row per sprint commitment (carried-over work appears again)
    retros/sprint_NN.md  one retrospective note per sprint
"""
from __future__ import annotations

import argparse
import math
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SPRINT_DAYS = 14
N_SPRINTS = 12
FIRST_MONDAY = date(2025, 1, 6)
TEAM = ["Avery", "Blake", "Casey", "Devon", "Emery", "Finley"]
POINT_SCALE = [1, 2, 3, 5, 8]
POINT_WEIGHTS = [2, 4, 5, 3, 1]
DOR_SPRINT = 5  # sprint in which the Definition of Ready is introduced


def phase(sprint: int) -> dict:
    """Behaviour of the team in a given sprint."""
    if sprint < DOR_SPRINT:
        return {"completion": 0.80, "cycle_median": 7.5, "scope_creep": 0.28, "block": 0.35, "capacity": 40}
    ramp = min(1.0, (sprint - DOR_SPRINT + 1) / 4)
    return {
        "completion": 0.80 + 0.12 * ramp,
        "cycle_median": 7.5 - 2.5 * ramp,
        "scope_creep": 0.28 - 0.20 * ramp,
        "block": 0.35 - 0.22 * ramp,
        "capacity": 40 + 4 * ramp,
    }


def _cycle_days(rng: random.Random, median: float, points: int) -> int:
    value = rng.lognormvariate(math.log(median), 0.45) * (points / 3) ** 0.3
    return max(1, round(value))


def generate_issues(seed: int = 11) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = random.Random(seed)
    sprint_rows, issue_rows = [], []
    carry: list[dict] = []
    counter = 100

    for s in range(1, N_SPRINTS + 1):
        start = FIRST_MONDAY + timedelta(days=SPRINT_DAYS * (s - 1))
        end = start + timedelta(days=SPRINT_DAYS - 1)
        ph = phase(s)
        sprint_rows.append(
            {"sprint_id": s, "name": f"Sprint {s}", "start": start, "end": end}
        )

        committed: list[dict] = []
        for c in carry:
            row = dict(c)
            row["carried_in"] = True
            row["added_mid_sprint"] = False
            committed.append(row)
        carry = []

        target = ph["capacity"] + rng.randint(-3, 3)
        while sum(r["points"] for r in committed) < target:
            counter += 1
            mid = rng.random() < ph["scope_creep"]
            offset = rng.randint(4, 9) if mid else rng.randint(0, 4)
            committed.append(
                {
                    "issue_id": f"SL-{counter}",
                    "type": rng.choices(["Story", "Bug", "Task"], weights=[6, 2, 2])[0],
                    "points": rng.choices(POINT_SCALE, weights=POINT_WEIGHTS)[0],
                    "assignee": rng.choice(TEAM),
                    "started": start + timedelta(days=offset),
                    "carried_in": False,
                    "added_mid_sprint": mid,
                }
            )

        for r in committed:
            blocked = rng.randint(1, 4) if rng.random() < ph["block"] else 0
            if r["carried_in"]:
                done = rng.random() < 0.80
                completed = start + timedelta(days=rng.randint(0, 9)) if done else None
            else:
                done = rng.random() < ph["completion"]
                completed = None
                if done:
                    completed = r["started"] + timedelta(
                        days=_cycle_days(rng, ph["cycle_median"], r["points"]) + blocked
                    )
                    if completed > end:
                        done = False
                        completed = None
            if completed is not None and completed < r["started"]:
                completed = r["started"]
            issue_rows.append(
                {
                    "sprint_id": s,
                    "issue_id": r["issue_id"],
                    "type": r["type"],
                    "points": r["points"],
                    "assignee": r["assignee"],
                    "started": r["started"],
                    "completed": completed,
                    "blocked_days": blocked,
                    "carried_in": r["carried_in"],
                    "added_mid_sprint": r["added_mid_sprint"],
                    "status": "Done" if completed is not None else "Carried over",
                }
            )
            if completed is None:
                carry.append({k: r[k] for k in ("issue_id", "type", "points", "assignee", "started")})

    sprints = pd.DataFrame(sprint_rows)
    issues = pd.DataFrame(issue_rows)
    for col in ("start", "end"):
        sprints[col] = pd.to_datetime(sprints[col])
    for col in ("started", "completed"):
        issues[col] = pd.to_datetime(issues[col])
    return sprints, issues


# ---------------------------------------------------------------------------
# Retrospective notes
# ---------------------------------------------------------------------------

WELL = {
    "early": [
        "Daily standups stayed short and focused.",
        "Pairing on the checkout bug unblocked the team quickly.",
        "Stakeholder demo was well received.",
        "Good communication in the team channel during the release.",
    ],
    "late": [
        "The Definition of Ready checklist caught two unclear stories before planning.",
        "Acceptance criteria were written before sprint start, which reduced rework.",
        "Smaller stories finished earlier in the sprint and kept work in progress low.",
        "Daily standups surfaced a dependency early and it was resolved in a day.",
        "Demo feedback was incorporated mid-sprint without disrupting the plan.",
        "Automated regression tests shortened QA turnaround.",
    ],
}

IMPROVE = {
    "early": [
        "Stories entered the sprint with unclear acceptance criteria and needed rework.",
        "Several stories were blocked waiting on an external dependency from another team.",
        "New scope was added mid-sprint without removing anything.",
        "QA started late and testing was compressed into the final two days.",
        "Too many items were in progress at once, so little was finished.",
        "Capacity was overestimated because planned leave was not considered.",
        "Requirements changed after the sprint started.",
        "Handoffs between design and development were slow.",
    ],
    "late": [
        "One external dependency still delayed a story by three days.",
        "Estimates for larger stories remain inconsistent.",
        "Test environment instability cost half a day.",
        "Backlog refinement ran long and not everyone attended.",
        "Release notes were written late.",
    ],
}

ACTIONS = {
    "early": [
        "Draft a Definition of Ready checklist for the next refinement session.",
        "Limit work in progress to two items per person.",
        "Agree on a scope change rule: swap, do not add.",
        "Start QA on each story as soon as development completes.",
        "Track planned leave before sprint planning to set realistic capacity.",
    ],
    "late": [
        "Add a dependency check to refinement and raise blockers in standup.",
        "Split any story over five points before it enters a sprint.",
        "Book a stable test environment window for each sprint.",
        "Timebox refinement to 60 minutes with a fixed agenda.",
    ],
}


def generate_retros(out_dir: Path, seed: int = 7) -> None:
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    for s in range(1, N_SPRINTS + 1):
        key = "early" if s < DOR_SPRINT else "late"
        well = rng.sample(WELL[key], k=3)
        improve = rng.sample(IMPROVE[key], k=3 if key == "early" else 2)
        if key == "late" and s % 3 == 0:  # occasional relapse keeps the data realistic
            improve.append(rng.choice(IMPROVE["early"]))
        actions = rng.sample(ACTIONS[key], k=2)
        lines = [f"# Sprint {s} Retrospective", "", "## What went well", ""]
        lines += [f"- {t}" for t in well]
        lines += ["", "## What did not go well", ""]
        lines += [f"- {t}" for t in improve]
        lines += ["", "## Action items", ""]
        lines += [f"- {t}" for t in actions]
        (out_dir / f"sprint_{s:02d}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic sprint data.")
    parser.add_argument("--out", default="data", help="output directory")
    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sprints, issues = generate_issues(args.seed)
    sprints.to_csv(out / "sprints.csv", index=False)
    issues.to_csv(out / "issues.csv", index=False)
    generate_retros(out / "retros", args.seed)
    print(f"Wrote {len(sprints)} sprints, {len(issues)} issue rows, {N_SPRINTS} retros to {out}/")


if __name__ == "__main__":
    main()
