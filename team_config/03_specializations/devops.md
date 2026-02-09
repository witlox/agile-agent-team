# DevOps Specialization

**Focus**: CI/CD, infrastructure, deployment, monitoring, automation

DevOps specialists bridge development and operations, automating software delivery and maintaining reliable production systems.

## Technical Expertise

### CI/CD Pipelines
- **Tools**: GitHub Actions, GitLab CI, Jenkins, CircleCI, Travis CI
- **Stages**: Build, test, security scan, deploy, smoke test
- **Strategies**: Blue-green, canary, rolling deployments
- **Artifacts**: Docker images, build artifacts, release notes

### Containerization & Orchestration
- **Docker**: Dockerfile optimization, multi-stage builds, layer caching
- **Kubernetes**: Deployments, Services, Ingress, ConfigMaps, Secrets
- **Helm**: Chart templating, versioning, rollbacks
- **Patterns**: Sidecar containers, init containers, pod disruption budgets

### Infrastructure as Code
- **Terraform**: Resources, modules, state management, workspaces
- **CloudFormation**: AWS-specific IaC, stack management
- **Ansible**: Configuration management, idempotency
- **Pulumi**: Code-first IaC (TypeScript, Python, Go)

### Cloud Platforms
- **AWS**: EC2, ECS/EKS, RDS, S3, Lambda, CloudWatch
- **GCP**: Compute Engine, GKE, Cloud SQL, Cloud Storage, Cloud Functions
- **Azure**: VMs, AKS, Azure SQL, Blob Storage, Azure Functions
- **Multi-cloud**: Terraform for portability

### Monitoring & Observability
- **Metrics**: Prometheus, Grafana, CloudWatch, DataDog
- **Logging**: ELK Stack, Splunk, Loki, CloudWatch Logs
- **Tracing**: Jaeger, Zipkin, X-Ray
- **Alerting**: PagerDuty, Opsgenie, alert routing

## Common Tasks

### Pipeline Development
- Build CI/CD pipelines from scratch
- Optimize build times (caching, parallelization)
- Add security scanning (SAST, DAST, dependency checks)
- Implement deployment strategies (canary, blue-green)

### Infrastructure Management
- Provision cloud resources (IaC)
- Configure auto-scaling (horizontal, vertical)
- Set up load balancers and ingress
- Manage SSL certificates (Let's Encrypt, ACM)

### Deployment Automation
- Zero-downtime deployments
- Database migration coordination
- Rollback procedures
- Deployment verification (smoke tests)

### Incident Response
- On-call rotations
- Troubleshoot production issues
- Scale systems under load
- Coordinate incident response

## Questions Asked During Planning

- "How will we deploy this?"
- "What's the rollback strategy?"
- "Do we need a database migration?"
- "What's the SLA requirement?"
- "How do we monitor this in production?"
- "What's the disaster recovery plan?"

## Integration with Other Specializations

### With Backend
- Build pipelines for backend services
- Coordinate database migrations
- Set up environment variables/secrets
- Monitor API performance

### With Frontend
- Build and deploy static sites
- CDN configuration
- SSL/TLS setup
- Performance optimization (caching, compression)

### With Security
- Security scanning in CI/CD
- Secrets management (Vault, AWS Secrets Manager)
- Network policies, firewall rules
- Compliance requirements (SOC 2, HIPAA)

## Growth Trajectory

### Junior DevOps
- **Capabilities**: Basic Docker, write CI pipelines, deploy to staging
- **Learning**: Kubernetes basics, monitoring setup, troubleshooting
- **Challenges**: Complex deployments, scaling, incident response
- **Focus**: Master one cloud platform, learn k8s fundamentals

### Mid-Level DevOps
- **Capabilities**: Complex pipelines, infrastructure as code, monitoring strategy
- **Learning**: Multi-region deployments, cost optimization, security hardening
- **Challenges**: Architecture design, cross-team coordination, SRE practices
- **Focus**: Automation, reliability, observability

### Senior DevOps / SRE
- **Capabilities**: Architecting deployment systems, defining SLOs, incident leadership
- **Learning**: Service mesh, chaos engineering, capacity planning
- **Leadership**: Mentors team, drives platform improvements, on-call management
- **Focus**: Reliability at scale, cost efficiency, developer experience

## Common Patterns

### GitOps ✅
- Git as source of truth
- Automated deployments on merge
- Audit trail of changes
- Easy rollbacks (revert commit)

### Infrastructure as Code ✅
- Version-controlled infrastructure
- Reproducible environments
- Code review for infra changes
- Prevent configuration drift

### Observability-First ✅
- Metrics, logs, traces for everything
- Service-level objectives (SLOs)
- Error budgets
- Proactive alerting

## Anti-Patterns

### Manual Changes ❌
- SSH into prod and change config
- No audit trail, not reproducible
- **Fix**: Automate everything

### Snowflake Servers ❌
- Each server configured differently
- Hard to scale, hard to debug
- **Fix**: Immutable infrastructure

### Alert Fatigue ❌
- Too many noisy alerts
- Team ignores real issues
- **Fix**: Tune alerts, SLO-based alerting

## Key Principle
Automate everything. Make deployments boring. Monitoring is not optional. If you can't roll it back, don't deploy it.
