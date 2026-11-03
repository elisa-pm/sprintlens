# How I Would Use This With a Team

## Principles

1. Metrics describe the system, not individuals. Assignee data is never charted or ranked.
2. Numbers start conversations. They do not end them.
3. Prefer ranges to dates. Forecasts are communicated as P50 and P85.
4. Changes are experiments. Each action item has a hypothesis and a review point.

## Cadence

| Moment | Activity | SprintLens view |
|---|---|---|
| Sprint planning | Compare planned points with the 3-sprint average and the last carryover rate | Velocity tab |
| Daily standup | Glance at WIP and the burndown when work looks stuck | Burndown, Flow |
| Backlog refinement | Check cycle time p85 to judge whether stories are small enough | Flow tab |
| Sprint review | Share the forecast range with stakeholders | Forecast tab |
| Retrospective | Open the theme heatmap and draft actions, then let the team decide | Retro insights |

## Retrospective routine (30 minutes)

1. Show the three most important numbers from the sprint: completion, carryover, cycle time p85.
2. Show recurring and worsening themes. Ask the team whether the classification matches their experience.
3. Review last sprint's action items. Did the related theme or metric move?
4. Choose at most two new actions. Name an owner and a review date.
5. Record the actions in the notes for the next analysis.

## Example experiment

Hypothesis: a Definition of Ready will reduce rework caused by unclear stories.
Signal: "Requirements clarity" mentions decline and carryover falls within three sprints.
Review: sprint 8 retrospective.

## Anti-patterns to avoid

- Using velocity as a performance target. Teams will inflate estimates.
- Comparing teams. Points are local to a team.
- Treating draft actions as decisions. The team owns the improvements.
- Sending sensitive notes to an external API without approval.

## Adapting to Kanban

Ignore the sprint-based views. Use cycle time p85, work in progress, and the forecast with weekly throughput in place of velocity.
