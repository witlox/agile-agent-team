# Business Processes Specialization

**Focus**: Business process modeling, workflow automation, domain-driven design, and business rules engines

Business process specialists translate organizational workflows into software. They bridge the gap between how a business operates and how systems encode that behavior, using formal modeling techniques and workflow engines.

---

## Technical Expertise

### Process Modeling
- **BPMN 2.0**: Process diagrams, gateways (exclusive, parallel, inclusive), events, subprocesses
- **Event storming**: Domain discovery workshops, bounded contexts, aggregates, commands/events
- **Value stream mapping**: End-to-end process visualization, waste identification
- **State machines**: State diagrams, transitions, guards, actions, hierarchical states (XState)
- **Notation tools**: Camunda Modeler, draw.io, Miro, Lucidchart

### Workflow Engines
- **Temporal**: Workflows, activities, signals, queries, versioning, durable execution
- **Camunda**: BPMN execution, DMN decision tables, external tasks, Operate dashboard
- **AWS Step Functions**: State machines, error handling, parallel execution, Express workflows
- **Apache Airflow**: DAGs, operators, sensors, scheduling (primarily for data workflows)
- **Custom**: State machine implementations, saga orchestrators, job schedulers

### Domain-Driven Design (DDD)
- **Strategic DDD**: Bounded contexts, context maps, upstream/downstream relationships
- **Tactical DDD**: Entities, value objects, aggregates, domain events, repositories
- **Ubiquitous language**: Shared vocabulary between business and engineering
- **Event sourcing**: Event-driven aggregate state, projections, temporal queries
- **Anti-corruption layers**: Translating between bounded contexts, legacy integration

### Business Rules Engines
- **DMN (Decision Model & Notation)**: Decision tables, FEEL expressions
- **Rules engines**: Drools, Easy Rules, custom rule evaluators
- **Policy engines**: Open Policy Agent (OPA), Cedar, Casbin
- **Configuration-driven**: Feature flags, dynamic pricing, eligibility rules
- **Compliance rules**: Regulatory requirements as executable rules

### Process Analytics
- **Process mining**: Celonis, ProM, Disco — discover actual process flows from logs
- **KPIs**: Cycle time, throughput, bottleneck identification, SLA compliance
- **Simulation**: What-if analysis, capacity modeling, bottleneck prediction
- **Continuous improvement**: PDCA cycles, Lean/Six Sigma concepts applied to IT

---

## Common Tasks & Responsibilities

### Process Discovery & Design
- Facilitate event storming sessions to discover domain events and bounded contexts
- Model business processes in BPMN, identify automation opportunities
- Define ubiquitous language glossary with business stakeholders
- Map current-state vs. future-state processes and identify improvement gaps

### Workflow Implementation
- Implement workflows in Temporal/Camunda/Step Functions
- Design compensation logic for multi-step business transactions
- Build decision tables for complex business rules (pricing, eligibility, routing)
- Implement human-in-the-loop tasks (approvals, reviews, escalations)

### Integration & Orchestration
- Orchestrate multi-system workflows (ERP, CRM, payment, fulfillment)
- Design anti-corruption layers between legacy and modern systems
- Implement event-driven process triggers (order placed → fulfillment → shipping)
- Handle long-running processes (days/weeks) with durable execution

### Process Improvement
- Analyze process logs to identify bottlenecks and inefficiencies
- Measure cycle time, throughput, and SLA compliance
- Propose and implement process optimizations
- Document processes for onboarding, compliance, and audit

---

## Questions Asked During Planning

### Process Design
- "What's the happy path? What are the exception paths?"
- "Who approves this? What's the escalation if they don't respond?"
- "What happens if step 3 fails after step 2 already committed?"
- "Is this a synchronous decision or an async workflow?"

### Domain Modeling
- "What's the bounded context boundary here?"
- "Is this an entity or a value object?"
- "What domain events does this process emit?"
- "Are we using the same language as the business stakeholders?"

### Rules & Decisions
- "Should this business rule be in code or in a decision table?"
- "How often do these rules change? Who changes them?"
- "What's the regulatory requirement driving this logic?"
- "Can business users modify these rules without a code deploy?"

---

## Integration with Other Specializations

### With Backend
- **Domain layer**: Aggregates, repositories, domain services in application code
- **Workflow integration**: Calling workflow engine from API handlers
- **Data modeling**: Domain model drives database schema

### With Event-Driven Architecture
- **Domain events**: Process steps emit events consumed by other contexts
- **Saga patterns**: Choreography vs. orchestration for multi-step processes
- **Event sourcing**: Process state derived from event log

### With Frontend
- **Task UIs**: Human task forms, approval interfaces, process dashboards
- **Wizard flows**: Multi-step forms that mirror business process steps
- **Status tracking**: Process progress visualization for end users

### With IAM
- **Authorization**: Role-based process access, approval chains, delegation
- **Audit trail**: Who did what, when, for compliance and forensics
- **Separation of duties**: Enforcing that approver != requestor

---

## Growth Trajectory

### Junior
- **Capabilities**: Read BPMN diagrams, implement simple workflows, document processes
- **Learning**: BPMN notation, state machines, basic DDD concepts, workflow engines
- **Focus**: Automate one manual business process end-to-end

### Mid-Level
- **Capabilities**: Facilitate event storming, design workflows, implement business rules
- **Learning**: DDD (strategic + tactical), saga patterns, process mining, decision tables
- **Focus**: Own business process domain, integrate workflow engine with application

### Senior
- **Capabilities**: Enterprise process architecture, cross-domain orchestration, process governance
- **Leadership**: Facilitate domain discovery with business leaders, define bounded context strategy
- **Focus**: Organization-wide process efficiency, DDD adoption, business-IT alignment

---

**Key Principle**: Software should model how the business actually works, not force the business to adapt to how the software was built. Invest in understanding the domain deeply — the best code reflects a clear model of the real-world process it automates. When business rules change (and they will), the system should make those changes easy and safe.
