"""Agile delivery metrics computed from sprint and issue tables.

Expected schema (see docs/metric_definitions.md):
    sprints: sprint_id, name, start, end
    issues:  sprint_id, issue_id, type, points, assignee, started, completed,
             blocked_days, carried_in, added_mid_sprint, status
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DATE_COLS_SPRINTS = ["start", "end"]
DATE_COLS_ISSUES = ["started", "completed"]


def load(sprints_path: str, issues_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    sprints = pd.read_csv(sprints_path, parse_dates=DATE_COLS_SPRINTS)
    issues = pd.read_csv(issues_path, parse_dates=DATE_COLS_ISSUES)
    for col in ("carried_in", "added_mid_sprint"):
        issues[col] = issues[col].astype(bool)
    return sprints, issues


def sprint_summary(sprints: pd.DataFrame, issues: pd.DataFrame) -> pd.DataFrame:
    """One row per sprint with the headline delivery metrics."""
    rows = []
    for sp in sprints.itertuples():
        i = issues[issues.sprint_id == sp.sprint_id]
        done = i[i.completed.notna()]
        carried_out = i[i.completed.isna()]
        committed = i[~i.added_mid_sprint].points.sum()
        added = i[i.added_mid_sprint].points.sum()
        cycle = (done.completed - done.started).dt.days
        rows.append(
            {
                "sprint_id": sp.sprint_id,
                "name": sp.name,
                "committed_pts": int(committed),
                "added_pts": int(added),
                "completed_pts": int(done.points.sum()),
                "carryover_pts": int(carried_out.points.sum()),
                "completion_rate": done.points.sum() / max(1, committed + added),
                "carryover_rate": carried_out.points.sum() / max(1, committed + added),
                "throughput": int(len(done)),
                "median_cycle_days": float(cycle.median()) if len(cycle) else np.nan,
                "p85_cycle_days": float(cycle.quantile(0.85)) if len(cycle) else np.nan,
                "avg_blocked_days": float(i.blocked_days.mean()) if len(i) else 0.0,
            }
        )
    out = pd.DataFrame(rows)
    out["velocity_3sprint_avg"] = out.completed_pts.rolling(3, min_periods=1).mean()
    return out


def cycle_times(issues: pd.DataFrame) -> pd.DataFrame:
    """Cycle time in calendar days for completed issues."""
    done = issues[issues.completed.notna()].copy()
    done["cycle_days"] = (done.completed - done.started).dt.days
    return done[["sprint_id", "issue_id", "type", "points", "cycle_days"]]


def burndown(sprints: pd.DataFrame, issues: pd.DataFrame, sprint_id: int) -> pd.DataFrame:
    """Daily remaining points versus the ideal line for one sprint.

    Mid-sprint additions enter the scope on the day they start.
    """
    sp = sprints[sprints.sprint_id == sprint_id].iloc[0]
    i = issues[issues.sprint_id == sprint_id]
    days = pd.date_range(sp.start, sp.end, freq="D")
    baseline = i[~i.added_mid_sprint].points.sum()
    rows = []
    for n, d in enumerate(days):
        added = i[i.added_mid_sprint & (i.started <= d)].points.sum()
        burned = i[i.completed.notna() & (i.completed <= d)].points.sum()
        rows.append(
            {
                "date": d,
                "remaining": int(baseline + added - burned),
                "ideal": baseline * (1 - n / (len(days) - 1)),
            }
        )
    return pd.DataFrame(rows)


def wip_daily(sprints: pd.DataFrame, issues: pd.DataFrame, sprint_id: int) -> pd.DataFrame:
    """Number of items in progress on each day of the sprint."""
    sp = sprints[sprints.sprint_id == sprint_id].iloc[0]
    i = issues[issues.sprint_id == sprint_id]
    rows = []
    for d in pd.date_range(sp.start, sp.end, freq="D"):
        end = i.completed.fillna(sp.end + pd.Timedelta(days=1))
        rows.append({"date": d, "wip": int(((i.started <= d) & (end > d)).sum())})
    return pd.DataFrame(rows)


def forecast_sprints(
    velocities: list[float], remaining_points: float, trials: int = 5000, seed: int = 1
) -> dict:
    """Monte Carlo forecast of sprints needed to finish `remaining_points`.

    Samples with replacement from historical velocity. Returns the 50th, 85th and
    95th percentile number of sprints.
    """
    if not velocities or remaining_points <= 0:
        return {"p50": 0, "p85": 0, "p95": 0}
    rng = np.random.default_rng(seed)
    hist = np.array([v for v in velocities if v > 0], dtype=float)
    if hist.size == 0:
        return {"p50": None, "p85": None, "p95": None}
    results = []
    for _ in range(trials):
        total, n = 0.0, 0
        while total < remaining_points and n < 200:
            total += rng.choice(hist)
            n += 1
        results.append(n)
    arr = np.array(results)
    return {
        "p50": int(np.percentile(arr, 50)),
        "p85": int(np.percentile(arr, 85)),
        "p95": int(np.percentile(arr, 95)),
    }


def kpis(summary: pd.DataFrame, window: int = 3) -> dict:
    """Headline numbers comparing the latest window with the first window."""
    first, last = summary.head(window), summary.tail(window)
    base = first.completed_pts.mean()
    return {
        "velocity_recent": float(last.completed_pts.mean()),
        "velocity_baseline": float(base),
        "velocity_change_pct": float((last.completed_pts.mean() - base) / base * 100) if base else 0.0,
        "completion_recent": float(last.completion_rate.mean()),
        "carryover_recent": float(last.carryover_rate.mean()),
        "p85_cycle_recent": float(last.p85_cycle_days.mean()),
    }
