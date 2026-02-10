# Site Reliability Specialization

**Focus**: Production reliability, SLOs/SLIs, error budgets, incident management, and toil reduction

Site reliability specialists apply software engineering principles to operations problems. They define and enforce reliability targets, manage incidents, and systematically reduce manual operational work.

---

## Technical Expertise

### Service Level Management
- **SLIs**: Request latency (p50/p95/p99), availability, error rate, throughput, freshness
- **SLOs**: Target reliability levels, measurement windows, rolling vs. calendar
- **Error budgets**: Budget calculation, burn rate alerts, policy when budget exhausted
- **SLAs**: External commitments, penalty clauses, relationship to internal SLOs

### Incident Management
- **Incident lifecycle**: Detection, triage, mitigation, resolution, postmortem
- **Incident command**: Incident commander role, communication cadence, war rooms
- **Postmortems**: Blameless culture, contributing factors, action items, follow-through
- **Severity levels**: P0-P4 definitions, escalation paths, communication templates
- **Chaos engineering**: Fault injection, game days, failure mode testing

### Reliability Patterns
- **Redundancy**: Active-active, active-passive, N+1, geographic distribution
- **Graceful degradation**: Circuit breakers, bulkheads, load shedding, feature flags
- **Rollback strategies**: Canary deploys, blue-green, feature flags, automated rollback
- **Data durability**: Backup verification, point-in-time recovery, disaster recovery drills

### Capacity Planning
- **Load modeling**: Traffic patterns, growth projections, seasonal variations
- **Resource sizing**: CPU, memory, disk, network — headroom vs. cost
- **Auto-scaling**: Horizontal pod autoscaler, predictive scaling, scale-to-zero
- **Cost optimization**: Right-sizing, spot/preemptible instances, reserved capacity

### Toil Reduction
- **Toil identification**: Manual, repetitive, automatable, no lasting value
- **Automation priority**: Frequency x time x risk matrix
- **Self-healing**: Automated remediation, restart policies, auto-scaling
- **Runbook automation**: Convert manual runbooks to automated playbooks

---

## Common Tasks & Responsibilities

### Reliability Engineering
- Define SLIs and SLOs for services in collaboration with product and engineering
- Monitor error budget consumption and trigger reliability reviews when exhausted
- Conduct production readiness reviews for new services
- Run disaster recovery drills and chaos engineering experiments

### Incident Response
- Serve as incident commander during production incidents
- Coordinate cross-team response and communication
- Write and review blameless postmortems
- Track action items from postmortems to completion

### Operational Excellence
- Identify and eliminate toil (manual, repetitive operational work)
- Build automation for common operational tasks
- Maintain and improve on-call playbooks and runbooks
- Review and optimize on-call rotations and escalation policies

### System Design Review
- Review architectural proposals for reliability implications
- Identify single points of failure and recommend mitigations
- Assess blast radius of changes and recommend rollout strategies
- Define rollback criteria and automated rollback triggers

---

## Questions Asked During Planning

### Reliability
- "What's the SLO for this service? How do we measure it?"
- "What happens to users if this component fails?"
- "What's our rollback plan if this deploy goes wrong?"
- "How long can this be down before it's a P0?"

### Capacity
- "What's the expected traffic for this feature at launch?"
- "How does this scale? Linearly with users, or worse?"
- "What's the cost profile at 10x current traffic?"
- "Do we have capacity for the upcoming seasonal peak?"

### Operations
- "Who gets paged? What's the runbook?"
- "How much toil does this create for on-call?"
- "Can this self-heal, or does it require human intervention?"
- "What's our disaster recovery story for this data?"

---

## Integration with Other Specializations

### With Observability
- **SLO monitoring**: SLI-based dashboards and burn rate alerts
- **Incident tooling**: Traces and logs available during incident response
- **Capacity metrics**: Utilization and saturation tracking for capacity planning

### With DevOps
- **Deployment safety**: Canary analysis, rollback automation, deploy freezes
- **Infrastructure reliability**: Multi-AZ, health checks, auto-healing
- **Change management**: Change review process, blast radius assessment

### With Backend
- **Reliability patterns**: Circuit breakers, retries, timeouts, bulkheads in code
- **Graceful degradation**: Feature flags for degraded mode, fallback responses
- **Performance budgets**: Latency budgets per service, dependency timeout chains

### With Security
- **Incident overlap**: Security incidents follow similar ICS process
- **Access controls**: Break-glass procedures for emergency access
- **Compliance**: Uptime requirements from regulatory frameworks

---

## Growth Trajectory

### Junior
- **Capabilities**: Follow runbooks, participate in on-call, write postmortem drafts
- **Learning**: SLI/SLO concepts, incident response process, basic Linux troubleshooting
- **Focus**: Shadow on-call, contribute to toil reduction projects

### Mid-Level
- **Capabilities**: Lead incidents, define SLOs, build automation, conduct chaos experiments
- **Learning**: Capacity planning, distributed systems failure modes, chaos engineering
- **Focus**: Own reliability for a service area, drive postmortem action items

### Senior
- **Capabilities**: Organizational reliability strategy, cross-team SLO programs, culture change
- **Leadership**: Define incident management process, mentor on-call engineers, executive communication
- **Focus**: Reliability culture, error budget policies, production readiness standards

---

**Key Principle**: Reliability is a feature, not an afterthought. The goal isn't 100% uptime — it's the right level of reliability for each service, measured objectively, with a clear process for when things go wrong. Every outage is a learning opportunity if you have the culture to support it.
