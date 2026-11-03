# Product Backlog

Ordered by value and dependency. Estimates in story points. Status as of release v1.0.

## Definition of Ready

- Story has a clear user value statement.
- Acceptance criteria are written and testable.
- Dependencies are identified.
- Estimate is 5 points or fewer. Larger items are split first.

## Definition of Done

- Acceptance criteria met and demonstrated.
- Unit tests written and passing in CI.
- Documentation updated.
- No real organizational data introduced.

## Epic A: Delivery metrics

| ID | User story | Acceptance criteria | Pts | Status |
|---|---|---|---|---|
| A1 | As a Scrum Master, I want velocity, completion, and carryover per sprint so that I can show delivery trends. | Rates are correct on sample data; completion plus carryover equals 100 percent. | 3 | Done |
| A2 | As a Scrum Master, I want a burndown for any sprint so that I can discuss scope changes. | Mid-sprint additions raise the line; final value equals carryover. | 3 | Done |
| A3 | As a team member, I want cycle time and work in progress so that I can see where work waits. | Boxplot by sprint; daily WIP chart. | 3 | Done |
| A4 | As a Product Owner, I want a forecast range so that I can avoid single-date promises. | P50, P85, P95 sprints for a given backlog size. | 5 | Done |
| A5 | As a Scrum Master, I want to upload my own CSVs so that I can use real data. | Valid files replace sample data. | 2 | Done |

## Epic B: Retrospective intelligence

| ID | User story | Acceptance criteria | Pts | Status |
|---|---|---|---|---|
| B1 | As a Scrum Master, I want retro notes parsed from Markdown so that I do not re-enter them. | Sections and bullets parsed by sprint number. | 2 | Done |
| B2 | As a Scrum Master, I want each bullet classified into a theme so that I can count patterns. | One theme per bullet from fixed taxonomy. | 3 | Done |
| B3 | As a Scrum Master, I want recurring and worsening themes flagged so that I focus retrospectives. | Recurring means 3 or more sprints; trend compares halves. | 3 | Done |
| B4 | As a Scrum Master, I want draft action items so that I can start the conversation. | One suggested action per focus theme; owner left to the team. | 2 | Done |
| B5 | As a Scrum Master, I want optional LLM classification so that nuance is captured. | Falls back to offline rules on any failure. | 5 | Done |

## Epic C: Quality and trust

| ID | User story | Acceptance criteria | Pts | Status |
|---|---|---|---|---|
| C1 | As a maintainer, I want automated tests and CI so that changes are safe. | Tests run on every push. | 3 | Done |
| C2 | As a reader, I want metric definitions documented so that numbers can be trusted. | Every metric has a formula and caveat. | 2 | Done |

## Next up

| ID | User story | Pts | Priority |
|---|---|---|---|
| D1 | As a Scrum Master, I want a Jira CSV column mapper so that import needs no manual editing. | 3 | High |
| D2 | As a Scrum Master, I want to tag action items and see whether the related theme declines. | 5 | High |
| D3 | As a Product Owner, I want a cumulative flow diagram. | 5 | Medium |
| D4 | As a Scrum Master, I want configurable theme taxonomies per team. | 3 | Medium |
| D5 | As a maintainer, I want a Docker image for one-command setup. | 2 | Low |
