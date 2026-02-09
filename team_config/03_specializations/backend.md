# Backend Specialization

**Focus**: Server-side application logic, APIs, databases, business logic

Backend specialists design and implement the core logic that powers applications, focusing on data persistence, API design, business rules, and system integration.

---

## Technical Expertise

### Programming Languages & Frameworks
- **Primary**: Python (FastAPI, Django, Flask), Node.js (Express, NestJS), Java (Spring Boot)
- **Secondary**: Go, Ruby (Rails), C# (.NET Core), Rust
- **Choose based on**: Performance needs, team expertise, ecosystem maturity

### API Design & Implementation
- **REST**: Resource modeling, HTTP verbs, status codes, versioning strategies
- **GraphQL**: Schema design, resolvers, N+1 query prevention, federation
- **gRPC**: Protocol buffers, streaming, error handling
- **Patterns**: Pagination, rate limiting, authentication, versioning

### Database Technologies
- **Relational**: PostgreSQL (JSONB, CTEs), MySQL, SQL Server
- **Document**: MongoDB, DynamoDB, CouchDB
- **Cache**: Redis (data structures, pub/sub, persistence)
- **Search**: Elasticsearch, Algolia, Meilisearch
- **Time-series**: InfluxDB, TimescaleDB

### Data Modeling & Persistence
- **Schema design**: Normalization, denormalization trade-offs
- **Migrations**: Backward-compatible changes, zero-downtime migrations
- **Transactions**: ACID properties, isolation levels, distributed transactions
- **Indexing**: B-tree, hash, composite indexes, query optimization
- **ORMs**: Sequelize, TypeORM, Django ORM, Prisma (and when to bypass them)

### Authentication & Authorization
- **Standards**: OAuth 2.0, JWT, SAML, OpenID Connect
- **Patterns**: RBAC, ABAC, resource-based permissions
- **Implementation**: Session management, token refresh, SSO
- **Security**: Password hashing (bcrypt, argon2), MFA, rate limiting

### Async & Background Jobs
- **Queues**: RabbitMQ, Redis Queue, AWS SQS, Kafka
- **Workers**: Celery, Bull, Sidekiq
- **Patterns**: Idempotency, retry strategies, dead letter queues
- **Use cases**: Email sending, report generation, data processing

---

## Common Tasks & Responsibilities

### Feature Implementation
- Translate user stories into API endpoints
- Implement business logic with validation
- Design database schema for new features
- Write integration tests for API contracts
- Document endpoints (OpenAPI/Swagger)

### Performance Optimization
- Profile slow queries with EXPLAIN ANALYZE
- Add database indexes based on query patterns
- Implement caching strategies (Redis, CDN)
- Optimize N+1 queries in ORMs
- Benchmark API response times

### Data Integrity & Validation
- Input validation at API boundary
- Business rule enforcement (price can't be negative)
- Referential integrity constraints
- Data consistency across services
- Audit logging for compliance

### Integration Work
- Connect to third-party APIs (Stripe, SendGrid, etc.)
- Handle webhooks from external services
- Implement rate limiting for external API calls
- Error handling and retry logic
- API versioning for backward compatibility

---

## Questions Asked During Planning

### Data Model Implications
- "What relationships exist between these entities?"
- "Do we need soft deletes or hard deletes?"
- "What's the expected data volume? (affects index strategy)"
- "Are there compliance requirements? (GDPR, data retention)"

### API Design
- "Should this be synchronous or asynchronous?"
- "What's the expected payload size?"
- "Do we need pagination? Sorting? Filtering?"
- "Who are the consumers? (mobile, web, internal services)"

### Performance & Scale
- "What's the expected request rate?"
- "Can we cache this?"
- "Do we need read replicas?"
- "What's the acceptable latency?"

### Error Handling & Edge Cases
- "What happens if the payment fails mid-transaction?"
- "How do we handle duplicate requests?"
- "What if the external API is down?"
- "Do we need idempotency keys?"

---

## Integration with Other Specializations

### With Frontend Specialists
- **API contracts**: Design endpoints together, agree on data shapes
- **Error formats**: Consistent error responses frontend can handle
- **Real-time needs**: WebSockets vs. polling vs. SSE
- **Performance**: Minimize payload size, compression, caching headers

### With DevOps Specialists
- **Deployment**: Database migration coordination, zero-downtime deploys
- **Monitoring**: What metrics to track (latency, error rate, queue depth)
- **Scaling**: Horizontal scaling strategies, stateless design
- **Secrets**: How to handle API keys, database credentials

### With Database Specialists
- **Schema design**: Optimal data models for query patterns
- **Migrations**: Safe migration strategies, rollback plans
- **Query optimization**: Identify slow queries, add indexes
- **Backup strategy**: Point-in-time recovery, disaster recovery

### With Security Specialists
- **Authentication flow**: Token management, refresh strategies
- **Authorization**: Permission models, resource access control
- **Input validation**: SQL injection, XSS prevention
- **Secrets management**: API key storage, rotation

---

## Growth Trajectory Within Specialization

### Junior Backend Developer
- **Capabilities**: CRUD APIs, basic SQL, authentication integration
- **Learning**: REST principles, database basics, testing strategies
- **Challenges**: Performance optimization, distributed systems, race conditions
- **Focus**: Master one framework deeply, learn relational databases

### Mid-Level Backend Developer
- **Capabilities**: Complex APIs, query optimization, async processing, caching
- **Learning**: Database tuning, distributed systems concepts, API design patterns
- **Challenges**: System design, data consistency, high-scale performance
- **Focus**: Deepen database expertise, learn multiple backend stacks

### Senior Backend Developer
- **Capabilities**: Architecting multi-service systems, data consistency strategies, high-scale design
- **Learning**: Distributed databases, event-driven architecture, observability at scale
- **Leadership**: Mentors juniors/mids, drives architectural decisions, cross-team coordination
- **Focus**: Systems thinking, business alignment, team multiplier

---

## Common Patterns & Anti-Patterns

### Good Patterns ✅

#### Repository Pattern
- Abstracts data access logic from business logic
- Makes testing easier (mock repository)
- Centralizes database queries

#### Service Layer
- Business logic separated from HTTP layer
- Reusable across different interfaces (REST, GraphQL, CLI)
- Testable without HTTP concerns

#### DTO (Data Transfer Objects)
- Clear API contracts
- Validation at API boundary
- Decouples internal models from external API

#### Command Query Separation
- Writes (commands) and reads (queries) separated
- Enables different optimization strategies
- Simplifies caching (cache reads, not writes)

### Anti-Patterns ❌

#### Fat Controllers
- Business logic in route handlers
- Hard to test, hard to reuse
- **Fix**: Move logic to service layer

#### N+1 Queries
- Loop that makes a database query per iteration
- Kills performance at scale
- **Fix**: Use joins or batch loading

#### God Service
- One service that does everything
- Hard to understand, test, deploy
- **Fix**: Split by domain or bounded context

#### Premature Optimization
- Adding Redis before measuring slow queries
- Over-indexing tables "just in case"
- **Fix**: Measure first, optimize second

---

## Tools & Technologies

### Development
- **API Testing**: Postman, Insomnia, curl, HTTPie
- **Database Clients**: pgAdmin, DBeaver, TablePlus
- **Profiling**: New Relic, DataDog APM, cProfile (Python)
- **Debugging**: IDE debuggers, logging, distributed tracing

### Monitoring & Observability
- **APM**: New Relic, DataDog, Elastic APM
- **Logging**: ELK stack, Splunk, CloudWatch Logs
- **Metrics**: Prometheus, Grafana, StatsD
- **Tracing**: Jaeger, Zipkin, X-Ray

### Testing
- **Unit**: pytest (Python), Jest (Node), JUnit (Java)
- **Integration**: Supertest, TestContainers, database fixtures
- **Load**: JMeter, Locust, k6
- **Contract**: Pact, Postman contract tests

---

## Domain-Specific Considerations

### E-Commerce
- **Payments**: PCI compliance, idempotency, refunds
- **Inventory**: Stock tracking, race conditions, overselling
- **Orders**: State machines, order lifecycle, cancellations

### SaaS Products
- **Multi-tenancy**: Data isolation, tenant-specific configurations
- **Billing**: Subscriptions, metering, proration
- **User management**: Organizations, teams, invitations

### Social Platforms
- **Feeds**: Pagination, ranking algorithms, real-time updates
- **Notifications**: Push, email, in-app, preferences
- **Moderation**: Content filtering, reporting, automated detection

### FinTech
- **Transactions**: Atomic operations, double-entry bookkeeping
- **Compliance**: KYC, AML, transaction reporting
- **Auditing**: Immutable logs, forensic analysis

---

## Learning Resources

### Books
- "Designing Data-Intensive Applications" (Kleppmann)
- "Building Microservices" (Newman)
- "Web Scalability for Startup Engineers" (Ejsmont)

### Topics to Master
- Database transactions and isolation levels
- Caching strategies (write-through, write-behind, cache-aside)
- Event-driven architecture
- API versioning strategies
- Distributed systems fundamentals

### Hands-On Practice
- Build a REST API with full CRUD + authentication
- Optimize a slow query (10s → 100ms)
- Implement idempotent endpoints
- Design a schema migration strategy
- Load test an API to find bottlenecks

---

**Key Principle**: Backend is the heart of the application. Focus on data integrity, reliability, performance, and maintainability. Your APIs are contracts with frontend—be thoughtful, consistent, and backward-compatible.
