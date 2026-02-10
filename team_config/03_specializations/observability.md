# Observability Specialization

**Focus**: Monitoring, logging, tracing, alerting, and production visibility

Observability specialists ensure teams can understand what their systems are doing in production. They design and operate the instrumentation, dashboards, and alerting that turn opaque systems into transparent ones.

---

## Technical Expertise

### Pillars of Observability
- **Metrics**: Prometheus, Grafana, DataDog, CloudWatch Metrics
- **Logging**: ELK stack (Elasticsearch, Logstash, Kibana), Loki, Splunk, Fluentd/Fluent Bit
- **Tracing**: OpenTelemetry, Jaeger, Zipkin, AWS X-Ray, Tempo
- **Profiling**: Continuous profiling (Pyroscope, Parca), flame graphs, CPU/memory profiling

### Instrumentation
- **OpenTelemetry SDK**: Auto-instrumentation, manual spans, baggage propagation
- **Custom metrics**: Counters, gauges, histograms, summaries — choosing the right type
- **Structured logging**: JSON logs, correlation IDs, log levels, context propagation
- **Trace context**: W3C TraceContext, B3 propagation, cross-service correlation

### Alerting & On-Call
- **Alert design**: Symptom-based vs. cause-based alerts, alert fatigue reduction
- **Runbooks**: Actionable runbooks tied to alerts, escalation procedures
- **PagerDuty/OpsGenie**: On-call rotations, escalation policies, incident workflows
- **Signal vs. noise**: Alert deduplication, grouping, suppression windows

### Dashboarding
- **Grafana**: Dashboard design, variables, annotations, alert integration
- **RED method**: Rate, Errors, Duration for services
- **USE method**: Utilization, Saturation, Errors for resources
- **SLO dashboards**: Error budget burn rate, multi-window alerts

### Log Management
- **Centralized logging**: Log aggregation, retention policies, cost management
- **Log parsing**: Grok patterns, regex extractors, structured vs. unstructured
- **Correlation**: Request IDs across services, trace-to-log linking
- **Compliance**: Audit logs, PII redaction in logs, retention requirements

---

## Common Tasks & Responsibilities

### Instrumentation
- Add OpenTelemetry to new services (auto + manual instrumentation)
- Define and implement custom business metrics
- Ensure trace context propagates across service boundaries
- Standardize structured logging format across the team

### Dashboard & Alert Creation
- Build service-level dashboards (latency percentiles, error rates, throughput)
- Create SLO-based alerting with error budget burn rate
- Design on-call runbooks for common alert scenarios
- Review and prune stale or noisy alerts quarterly

### Incident Support
- Provide observability tooling during incident response
- Build post-incident dashboards to visualize what happened
- Identify monitoring gaps exposed by incidents
- Correlate metrics, logs, and traces to find root cause

### Cost & Performance
- Optimize log volume and cardinality to control costs
- Tune metric retention and downsampling policies
- Evaluate and recommend observability platform choices
- Benchmark instrumentation overhead on application performance

---

## Questions Asked During Planning

### Instrumentation
- "What metrics will tell us this feature is working correctly?"
- "How will we detect if this degrades performance?"
- "What should the SLI be for this service?"
- "Do we need custom spans or will auto-instrumentation suffice?"

### Alerting
- "Who gets paged if this breaks? What's the runbook?"
- "What's the error budget for this service?"
- "Is this alert actionable, or will it just create noise?"
- "What's the expected baseline for this metric?"

### Debugging
- "Can we correlate requests across these three services?"
- "Do we have enough cardinality to slice by tenant/region/version?"
- "What's our log retention policy for compliance?"

---

## Integration with Other Specializations

### With Site Reliability
- **SLO definition**: Jointly define SLIs, SLOs, and error budgets
- **Incident response**: Provide the tooling SREs use during incidents
- **Capacity planning**: Surface utilization and saturation metrics

### With DevOps
- **CI/CD observability**: Deploy markers in dashboards, canary metrics
- **Infrastructure monitoring**: Node/pod health, resource utilization
- **Log pipeline**: Shipping logs from containers/VMs to central store

### With Backend
- **Application instrumentation**: Help add traces, metrics, structured logs
- **Performance debugging**: Trace slow requests, identify bottlenecks
- **Error tracking**: Sentry/Bugsnag integration, error grouping

### With Security
- **Audit logging**: Ensure security-relevant events are captured
- **Anomaly detection**: Unusual traffic patterns, failed auth spikes
- **PII handling**: Redact sensitive data from logs and traces

---

## Growth Trajectory

### Junior
- **Capabilities**: Read dashboards, add basic logging, understand log levels
- **Learning**: Prometheus query language (PromQL), structured logging, trace concepts
- **Focus**: Instrument one service end-to-end, build your first dashboard

### Mid-Level
- **Capabilities**: Design dashboards, write alerting rules, troubleshoot with traces
- **Learning**: OpenTelemetry SDK, alert design patterns, log pipeline architecture
- **Focus**: Own observability for a service area, reduce alert fatigue

### Senior
- **Capabilities**: Design observability strategy, define SLIs/SLOs, optimize costs
- **Leadership**: Set instrumentation standards, mentor on debugging techniques
- **Focus**: Organization-wide observability platform, cost/value optimization

---

**Key Principle**: You can't fix what you can't see. Good observability isn't about more data — it's about the right data, correlated and accessible, so any engineer can answer novel questions about production behavior without shipping new code.
