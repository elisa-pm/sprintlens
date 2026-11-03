import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sprintlens import generate_data as gd  # noqa: E402
from sprintlens import metrics as m  # noqa: E402
from sprintlens import retro_analyzer as ra  # noqa: E402


@pytest.fixture(scope="module")
def data():
    return gd.generate_issues(seed=11)


def test_generation_is_deterministic():
    a = gd.generate_issues(seed=5)[1]
    b = gd.generate_issues(seed=5)[1]
    pd.testing.assert_frame_equal(a, b)


def test_every_sprint_has_issues(data):
    sprints, issues = data
    assert set(issues.sprint_id) == set(sprints.sprint_id)


def test_completed_never_before_started(data):
    _, issues = data
    done = issues[issues.completed.notna()]
    assert (done.completed >= done.started).all()


def test_summary_rates_are_consistent(data):
    sprints, issues = data
    s = m.sprint_summary(sprints, issues)
    assert ((s.completion_rate + s.carryover_rate - 1).abs() < 1e-9).all()
    assert (s.completed_pts >= 0).all()


def test_burndown_ends_at_carryover(data):
    sprints, issues = data
    for sid in sprints.sprint_id:
        bd = m.burndown(sprints, issues, sid)
        carry = issues[(issues.sprint_id == sid) & issues.completed.isna()].points.sum()
        assert bd.remaining.iloc[-1] == carry


def test_wip_is_non_negative(data):
    sprints, issues = data
    assert (m.wip_daily(sprints, issues, 3).wip >= 0).all()


def test_forecast_monotonic():
    r = m.forecast_sprints([20, 25, 30], 100)
    assert r["p50"] <= r["p85"] <= r["p95"]
    assert m.forecast_sprints([20], 0) == {"p50": 0, "p85": 0, "p95": 0}


def test_retro_parse_and_classify(tmp_path):
    f = tmp_path / "sprint_01.md"
    f.write_text(
        "# Sprint 1\n## What went well\n- Standups were short.\n"
        "## What did not go well\n- Acceptance criteria were unclear.\n- QA started late.\n"
        "## Action items\n- Write a Definition of Ready.\n",
        encoding="utf-8",
    )
    items = ra.classify_offline(ra.parse_retro(f))
    assert [i.section for i in items] == ["well", "improve", "improve", "action"]
    assert items[1].theme == "Requirements clarity"
    assert items[2].theme == "Testing and quality"


def test_llm_mode_uses_valid_answers_and_falls_back(tmp_path):
    f = tmp_path / "sprint_02.md"
    f.write_text("## What did not go well\n- Thing one.\n- QA started late.\n", encoding="utf-8")
    items = ra.parse_retro(f)

    def fake(prompt: str) -> str:
        return json.dumps([{"id": 0, "theme": "Scope change"}, {"id": 1, "theme": "Not a real theme"}])

    ra.classify_llm(items, fake)
    assert items[0].theme == "Scope change"  # accepted
    assert items[1].theme == "Testing and quality"  # invalid label ignored, offline rule kept


def test_llm_failure_does_not_break(tmp_path):
    f = tmp_path / "sprint_03.md"
    f.write_text("## What did not go well\n- Blocked by an external dependency.\n", encoding="utf-8")
    items = ra.parse_retro(f)

    def boom(prompt: str) -> str:
        raise RuntimeError("network down")

    ra.classify_llm(items, boom)
    assert items[0].theme == "Dependencies and blockers"


def test_report_contains_sections():
    items = ra.classify_offline(ra.load_retros(Path(__file__).resolve().parents[1] / "data/retros"))
    report = ra.build_report(items)
    for heading in ("## Recurring themes", "## Risks to watch", "## Draft action items", "## Method"):
        assert heading in report
