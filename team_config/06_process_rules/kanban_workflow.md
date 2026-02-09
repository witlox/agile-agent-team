# Kanban Workflow

## Board Structure

```
[ Backlog ] → [ Ready ] → [ In Progress ] → [ Review ] → [ Done ]
```

### Column Definitions

**Backlog**
- All potential work items
- Not refined or estimated yet
- PO prioritizes top items

**Ready**
- Acceptance criteria defined
- Estimated and prioritized
- No blockers
- Ready to be pulled

**In Progress**
- Actively being worked
- WIP limit: 4 items maximum
- Must be paired work (for production)

**Review**
- Code complete, tests passing
- Awaiting final QA/PO approval
- WIP limit: 2 items maximum

**Done**
- Meets all DoD criteria
- Deployed to staging
- Accepted by PO

## Work in Progress (WIP) Limits

**Why WIP Limits?**
- Focus on finishing over starting
- Reduce context switching
- Surface bottlenecks early
- Improve flow efficiency

**Current Limits**:
- In Progress: 4
- Review: 2

**When WIP limit is reached**:
- Help finish existing work
- Don't start new work
- Investigate what's blocking flow

## Pull System

**Don't assign work - pull it**

1. Check Kanban board
2. Pull highest-priority Ready item
3. Move to In Progress
4. Find pairing partner
5. Work until Done

## Flow Metrics

Track these per sprint:
- **Cycle time**: Time from In Progress → Done
- **Throughput**: Items completed per sprint
- **WIP age**: How long items stay In Progress
- **Blocked time**: Time spent waiting on external dependencies

## Blockers

**How to handle blocked items**:
1. Add "BLOCKED" label to card
2. Note what you're waiting for
3. Notify relevant person (dev lead, PO, etc.)
4. Work on different item while blocked
5. Resolve blocker ASAP
6. Update card when unblocked
