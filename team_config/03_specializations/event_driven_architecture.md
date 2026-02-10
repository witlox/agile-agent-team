# Event-Driven Architecture Specialization

**Focus**: Messaging systems, event sourcing, CQRS, async workflows, and stream processing

Event-driven architecture specialists design systems where components communicate through events rather than direct calls. They build the messaging infrastructure and patterns that enable loose coupling, temporal decoupling, and scalable async workflows.

---

## Technical Expertise

### Messaging Platforms
- **Apache Kafka**: Topics, partitions, consumer groups, exactly-once semantics, Kafka Connect
- **RabbitMQ**: Exchanges (direct, topic, fanout), queues, dead-letter exchanges, federation
- **AWS**: SQS, SNS, EventBridge, Kinesis Data Streams
- **GCP/Azure**: Pub/Sub, Event Hubs, Service Bus
- **NATS**: JetStream, request-reply, subject hierarchies

### Event Sourcing
- **Event store design**: Append-only logs, stream-per-aggregate, snapshots
- **Projections**: Read model rebuilding, catch-up subscriptions, projection versioning
- **Temporal queries**: Point-in-time state reconstruction, audit trail
- **Schema evolution**: Event versioning, upcasting, backward compatibility
- **Frameworks**: Axon, EventStoreDB, Marten, custom implementations

### CQRS (Command Query Responsibility Segregation)
- **Write model**: Command handlers, aggregate roots, domain events
- **Read model**: Denormalized projections, materialized views, query-optimized stores
- **Eventual consistency**: Consistency boundaries, read-your-writes patterns
- **When to use CQRS**: High read/write ratio disparity, complex domains, audit requirements

### Saga & Workflow Patterns
- **Orchestration sagas**: Central coordinator, compensating transactions, Temporal/Cadence
- **Choreography sagas**: Event-driven coordination, eventual consistency
- **Compensation**: Rollback strategies, semantic undo, partial failure handling
- **Workflow engines**: Temporal, Camunda, AWS Step Functions, Apache Airflow

### Stream Processing
- **Frameworks**: Kafka Streams, Apache Flink, Spark Structured Streaming
- **Windowing**: Tumbling, sliding, session windows, watermarks
- **State management**: Local state stores, changelog topics, queryable state
- **Exactly-once**: Idempotent producers, transactional consumers, deduplication

---

## Common Tasks & Responsibilities

### System Design
- Design event-driven architectures for new features and services
- Define event schemas and contracts (Avro, Protobuf, JSON Schema)
- Choose between choreography and orchestration for multi-step workflows
- Implement saga patterns for distributed transactions

### Messaging Infrastructure
- Set up and configure Kafka/RabbitMQ clusters
- Design topic/queue topologies, partitioning strategies, and retention policies
- Implement dead-letter queues and poison message handling
- Monitor consumer lag, throughput, and partition balance

### Event Schema Management
- Maintain schema registry (Confluent Schema Registry, AWS Glue)
- Enforce backward/forward compatibility rules
- Version events and handle schema evolution gracefully
- Document event catalogs and ownership

### Reliability & Operations
- Ensure exactly-once or at-least-once delivery guarantees
- Implement idempotent consumers for safe reprocessing
- Design for replay: rebuild read models from event streams
- Monitor and alert on consumer lag, failed messages, and throughput anomalies

---

## Questions Asked During Planning

### Architecture
- "Should this be synchronous (API call) or asynchronous (event)?"
- "What's the consistency requirement? Can we be eventually consistent?"
- "Do we need event sourcing, or is simple pub/sub enough?"
- "What happens if the consumer is down for an hour?"

### Reliability
- "What's our delivery guarantee — at-least-once or exactly-once?"
- "How do we handle poison messages (messages that always fail)?"
- "Can consumers be idempotent? What's the deduplication key?"
- "What's the replay strategy if we need to rebuild a projection?"

### Schema & Contracts
- "Who owns this event? Who are the consumers?"
- "Is this a domain event (fact) or a command (intent)?"
- "How do we evolve this schema without breaking consumers?"
- "Do we need a schema registry?"

---

## Integration with Other Specializations

### With Backend
- **Event publishing**: Transactional outbox pattern, change data capture
- **API vs. events**: When to use request-response vs. event-driven communication
- **Domain modeling**: Aggregate boundaries determine event stream boundaries

### With Data Engineering
- **Event streaming to data lake**: Kafka Connect sinks, CDC to warehouse
- **Real-time analytics**: Stream processing for live dashboards and metrics
- **Schema alignment**: Shared event schemas between operational and analytical systems

### With Distributed Systems
- **Consistency**: CAP theorem implications for event-driven systems
- **Ordering**: Total order vs. partial order, partition-level ordering guarantees
- **Failure modes**: Split brain, duplicate delivery, out-of-order processing

### With Site Reliability
- **Monitoring**: Consumer lag as an SLI, dead-letter queue depth alerts
- **Incident recovery**: Event replay for data recovery, consumer reset procedures
- **Capacity**: Partition count planning, broker sizing, retention vs. cost

---

## Growth Trajectory

### Junior
- **Capabilities**: Publish and consume events, basic Kafka/RabbitMQ usage
- **Learning**: Pub/sub patterns, message serialization, idempotent consumers
- **Focus**: Implement simple event-driven features, understand async vs. sync trade-offs

### Mid-Level
- **Capabilities**: Design event schemas, implement sagas, manage schema evolution
- **Learning**: Event sourcing, CQRS, stream processing, exactly-once semantics
- **Focus**: Own event-driven subsystems, design topic topologies

### Senior
- **Capabilities**: Architecture-level event strategy, platform design, organizational standards
- **Leadership**: Define event contracts across teams, mentor on async patterns
- **Focus**: Event mesh/platform strategy, cross-team event governance, consistency trade-offs

---

**Key Principle**: Events represent facts — things that happened. Design them as immutable records of business-meaningful state changes. Good event-driven systems are loosely coupled, independently deployable, and can reconstruct any state from the event log. But don't use events where a simple API call would do — complexity must be justified.
