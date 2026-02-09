# Mid-Level Domain Knowledge (TaskFlow)

**Cumulative**: Load AFTER 00_saas + 01_junior

## What Mids Learn (2-4 years)

### System Integration Patterns
- How GitHub webhook delivers events
- Rate limiting on third-party APIs (Slack, GitHub)
- Real-time updates via WebSocket vs. polling trade-offs
- Multi-tenant data isolation strategies

### Edge Cases from Experience
- Calendar boundaries: Sprint ending on month-end, holidays
- Timezone handling: Team distributed across UTC-8 to UTC+8
- Concurrent edits: Two users move same card simultaneously
- Data migration: Customer switches from Jira, need import

### Performance Considerations
- Board with 1000+ cards (virtual scrolling needed)
- Search across millions of cards (Elasticsearch)
- Real-time for 50 concurrent users on one board
- Attachment uploads (large files, progress tracking)

### Questions Mids Ask in Planning
- "How does this scale?"
- "What if the integration is down?"
- "Do we need a migration?"
- "What's the rollback plan?"
