# Senior Domain Knowledge (TaskFlow)

**Cumulative**: Load AFTER 00_saas + 01_junior + 02_mid

## What Seniors Know (5-10+ years in SaaS)

### Historical Incidents (Pattern Recognition)
- **2022 Q2 Outage**: WebSocket connection storm when US East region had latency spike
  - Learning: Circuit breakers on WebSocket reconnects
- **2023 Q1 Data Loss**: Race condition in concurrent card updates
  - Learning: Optimistic locking with version numbers
- **2023 Q3 Scale Issue**: Elasticsearch cluster couldn't handle search load during trial surge
  - Learning: Separate clusters for trial vs. paid customers

### Architectural Evolution
- **v1.0 (2020)**: Monolith, PostgreSQL only
- **v2.0 (2021)**: Microservices (boards, users, integrations)
- **v2.5 (2022)**: Added Elasticsearch, Redis caching
- **v3.0 (2023)**: Multi-region active-active
- Each change has trade-offs seniors remember

### Regulatory & Compliance
- **GDPR**: Data export, right to be forgotten, data residency (EU customers)
- **SOC 2 Type II**: Audit requirements, access logging, encryption at rest
- **Data retention**: Delete archived data after 90 days (configurable)

### Cross-Team Impact Questions
- "How does this affect Team B's service?"
- "What's the data migration for existing customers?"
- "Do we need a feature flag?"
- "What's the support team rollout plan?"
- "Compliance implications?"

### Product Strategy Context
- Competing with Jira (enterprise), Linear (startups)
- Focus: Developer experience, not PM features
- Pricing: Per-user SaaS, annual contracts for enterprise
- Roadmap: AI-powered sprint planning (2024 H2)
