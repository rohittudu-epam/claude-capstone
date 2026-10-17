# Workflow State Model

## State Definitions

| State | Description |
|-------|-------------|
| `PENDING` | Stage has not started; prerequisites may not be met |
| `READY` | All prerequisites are satisfied; stage can begin |
| `IN_PROGRESS` | Agent is actively working on this stage |
| `VALIDATING` | Agent has completed work; orchestrator is checking outputs |
| `COMPLETED` | Output validated, quality gate passed |
| `BLOCKED` | Cannot proceed — missing prerequisite, max retries, or unresolvable issue |
| `FAILED` | Quality gate failed; eligible for retry |
| `AWAITING_APPROVAL` | Human approval required before proceeding |
| `REJECTED` | Human rejected the output; revision needed |

## State Transition Diagram

```
                    ┌──────────┐
                    │ PENDING  │
                    └────┬─────┘
                         │ prerequisites satisfied
                         ▼
                    ┌──────────┐
                    │  READY   │
                    └────┬─────┘
                         │ agent begins work
                         ▼
                    ┌──────────────┐
              ┌─────│ IN_PROGRESS  │──────────┐
              │     └──────┬───────┘          │
              │            │ agent done       │ human gate
              │            ▼                  ▼
              │     ┌──────────────┐   ┌──────────────────┐
              │     │ VALIDATING   │   │AWAITING_APPROVAL │
              │     └──────┬───────┘   └────────┬─────────┘
              │       pass │ │ fail       approve│ │reject
              │            │ │                   │ │
              │            ▼ ▼                   ▼ ▼
              │  ┌──────────┐ ┌────────┐  ┌──────────┐
              │  │COMPLETED │ │ FAILED │  │ REJECTED │
              │  └──────────┘ └───┬────┘  └────┬─────┘
              │                   │ retry       │ revise
              │                   │             │
              │                   ▼             │
              │              ┌──────────────┐   │
              └──────────────│ IN_PROGRESS  │◄──┘
                             └──────┬───────┘
                                    │ max retries
                                    ▼
                             ┌──────────┐
                             │ BLOCKED  │
                             └──────────┘
```

## Transition Rules

| From | To | Condition |
|------|----|-----------|
| PENDING | READY | All prerequisite stages are COMPLETED |
| READY | IN_PROGRESS | Orchestrator starts the agent |
| IN_PROGRESS | VALIDATING | Agent reports work is done |
| IN_PROGRESS | AWAITING_APPROVAL | Human gate required (stages 1, 5) |
| VALIDATING | COMPLETED | Quality gate passes |
| VALIDATING | FAILED | Quality gate fails |
| FAILED | IN_PROGRESS | Retry initiated (retries < max_retries) |
| FAILED | BLOCKED | retries >= max_retries (default: 2) |
| AWAITING_APPROVAL | COMPLETED | User approves |
| AWAITING_APPROVAL | REJECTED | User rejects |
| REJECTED | IN_PROGRESS | Feedback incorporated, re-executing |
| BLOCKED | — | Terminal state; requires human intervention |
| COMPLETED | — | Terminal state for that stage |

## State File Schema

```json
{
  "workflow_id": "string (UUID)",
  "started_at": "string (ISO-8601)",
  "user_story_source": "string",
  "stages": {
    "<stage_name>": {
      "status": "PENDING|READY|IN_PROGRESS|VALIDATING|COMPLETED|BLOCKED|FAILED|AWAITING_APPROVAL|REJECTED",
      "agent": "string (agent filename)",
      "artifacts": ["string (file paths)"],
      "started_at": "string|null",
      "completed_at": "string|null",
      "retries": "integer",
      "notes": "string"
    }
  },
  "current_stage": "string",
  "overall_status": "IN_PROGRESS|COMPLETED|BLOCKED|FAILED"
}
```
