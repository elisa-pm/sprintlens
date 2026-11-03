# Product Requirements Document: SprintLens

Status: v1.0 delivered. Owner: Product Owner (author).

## 1. Problem statement

Scrum teams collect delivery data and retrospective notes but rarely connect them. Metrics live in a tracker, retrospective notes live in a wiki, and recurring problems are noticed only when someone remembers them. As a result, action items are repeated, improvements are not verified, and stakeholders receive anecdotes instead of forecasts.

## 2. Users and jobs to be done

| User | Job to be done |
|---|---|
| Scrum Master | Prepare a retrospective with evidence and track whether actions worked |
| Product Owner | Forecast delivery as a range and explain trade-offs to stakeholders |
| Developers and QA | See their own flow without being measured as individuals |

## 3. Goals and success measures

| Goal | Measure | Target |
|---|---|---|
| Reduce time to prepare a sprint review and retrospective | Minutes to produce metrics and themes | Under 10 minutes from export |
| Make recurring issues visible | Themes flagged as recurring | Detects any theme in 3 or more sprints |
| Support predictable delivery | Forecast gives P50, P85, P95 sprints | Available for any remaining backlog size |
| Increase trust in the data | Metric definitions documented and tested | 100 percent of metrics defined |

## 4. Non-goals

- Individual performance scoring or ranking.
- Replacing the tracker. SprintLens reads exports only.
- Cross-team velocity comparison.
- Automated decisions. Draft actions are suggestions.

## 5. Scope

### In scope (v1)

1. Velocity, completion rate, carryover rate per sprint.
2. Burndown with scope additions.
3. Cycle time distribution and daily work in progress.
4. Monte Carlo delivery forecast.
5. Retrospective parser, theme classification, recurring and worsening flags, draft actions.
6. Optional LLM classification and summary.
7. CSV upload and synthetic sample data.

### Out of scope (v1)

Live Jira API integration, authentication, multi-team views, cumulative flow diagram.

## 6. Functional requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| F1 | Compute sprint summary metrics | Given issues and sprints, completion plus carryover rate equals 100 percent for each sprint |
| F2 | Render burndown | Final remaining points equal carried-over points |
| F3 | Compute cycle time | Completed date is never earlier than start date; p85 is reported |
| F4 | Forecast | P50 is less than or equal to P85, which is less than or equal to P95 |
| F5 | Parse retro notes | Bullets are assigned to well, improve, or action by heading |
| F6 | Classify themes | Every bullet receives one theme from a fixed taxonomy |
| F7 | Flag recurring themes | A theme under improvement items in 3 or more sprints is marked recurring |
| F8 | LLM mode resilience | Invalid or failed model output falls back to offline rules without error |
| F9 | Bring your own data | Uploaded CSVs matching the schema replace the sample data |

## 7. Non-functional requirements

- Runs locally with no external services in default mode.
- Deterministic sample data (fixed seed).
- Automated tests run in CI on every push.
- No real organizational data in the repository.

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Metrics misused to compare people or teams | Documented limitations; team usage guide states metrics are for team learning |
| LLM misclassification | Fixed taxonomy, offline fallback, human review of draft actions |
| Sensitive text sent to an API | Offline default, explicit warning, synthetic sample data |
| Story points are not comparable across teams | Documented; no cross-team views in scope |

## 9. Open questions

- Which tracker exports should be supported first (Jira CSV, Azure DevOps, Linear)?
- Should themes be configurable per team?
- Is a cumulative flow diagram worth the added complexity?
