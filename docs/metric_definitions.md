# Metric Definitions and Data Schema

## Input schema

### sprints.csv

| Column | Type | Description |
|---|---|---|
| sprint_id | int | Sprint number |
| name | text | Display name |
| start | date | First day of the sprint |
| end | date | Last day of the sprint |

### issues.csv

One row per sprint commitment. Work not finished in a sprint appears again in the next sprint with `carried_in = true`.

| Column | Type | Description |
|---|---|---|
| sprint_id | int | Sprint in which the item was committed |
| issue_id | text | Unique item key |
| type | text | Story, Bug, or Task |
| points | int | Story points |
| assignee | text | Optional, not used in any metric |
| started | date | Date work began |
| completed | date | Date work finished, empty if not finished in the sprint |
| blocked_days | int | Days the item was blocked |
| carried_in | bool | Item was carried over from the previous sprint |
| added_mid_sprint | bool | Item entered after sprint start |
| status | text | Done or Carried over |

### Mapping a Jira export

| SprintLens column | Typical Jira field |
|---|---|
| issue_id | Issue key |
| type | Issue Type |
| points | Story Points |
| started | Date moved to In Progress (from changelog) |
| completed | Resolved |
| sprint_id | Sprint (take the sprint of commitment) |

## Metrics

| Metric | Formula | Caveat |
|---|---|---|
| Planned points | Points of items present at sprint start plus mid-sprint additions | Carried-in items count as planned |
| Velocity (completed points) | Sum of points where `completed` is set | Team-specific; not comparable across teams |
| Velocity, 3-sprint average | Rolling mean of completed points over 3 sprints | Smooths noise, lags change |
| Completion rate | Completed points divided by planned points | Rewards small commitments if used as a target |
| Carryover rate | Unfinished points divided by planned points | Equals 1 minus completion rate |
| Cycle time | Calendar days from `started` to `completed` | Carried-in items include time in earlier sprints |
| Cycle time p85 | 85th percentile of cycle time | Use for service-level expectations |
| Work in progress | Items started but not completed on a given day | Count of items, not points |
| Burndown remaining | Baseline plus added points minus completed points, by day | Added scope raises the line |
| Forecast | Monte Carlo: sample historical velocity with replacement until remaining points are met; report P50, P85, P95 sprints | Assumes the future resembles the sampled history |
| Velocity change | Mean velocity of last 3 sprints versus first 3 | Sensitive to the window and to scope changes |

## Retrospective analysis

| Term | Definition |
|---|---|
| Theme | One of a fixed set of categories (see `TAXONOMY` in `retro_analyzer.py`) |
| Recurring | Theme appears under improvement items in 3 or more sprints |
| Trend | Mentions in the second half of sprints compared with the first half: improving, stable, or worsening |
| Risk flag | Recurring and active in the last 3 sprints, or worsening with recent mentions |
