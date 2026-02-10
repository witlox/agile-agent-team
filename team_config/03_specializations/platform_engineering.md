# Platform Engineering Specialization

**Focus**: Internal developer platforms, developer experience, self-service infrastructure, and golden paths

Platform engineers build the tools, abstractions, and workflows that make other engineers productive. They create self-service platforms that let developers deploy, monitor, and operate their services without needing to understand every infrastructure detail.

---

## Technical Expertise

### Internal Developer Platforms (IDP)
- **Portal frameworks**: Backstage (Spotify), Port, Cortex, custom portals
- **Service catalogs**: Service ownership, metadata, dependency graphs, scorecards
- **Self-service**: Template-driven service creation, environment provisioning
- **Golden paths**: Opinionated defaults that cover 80% of use cases well

### Developer Experience (DX)
- **Local development**: Dev containers, docker-compose, Tilt, Skaffold, devenv
- **CI/CD abstraction**: Pipeline templates, shared workflows (GitHub Actions, GitLab CI)
- **Documentation**: Developer docs, API catalogs, architecture decision records (ADRs)
- **Onboarding**: New developer setup automation, starter templates, guided tutorials

### Infrastructure Abstraction
- **Infrastructure as Code**: Terraform modules, Pulumi, Crossplane, CDK
- **Kubernetes platforms**: Helm charts, Kustomize, operators, namespace-per-team
- **Service mesh**: Istio, Linkerd — traffic management, mTLS, observability
- **Secrets management**: Vault, AWS Secrets Manager, external-secrets-operator

### API & Service Management
- **API gateways**: Kong, Envoy, AWS API Gateway, rate limiting, auth
- **Service discovery**: Consul, CoreDNS, Kubernetes service DNS
- **Configuration management**: Feature flags (LaunchDarkly, Unleash), runtime config
- **Schema registries**: API versioning, contract testing, breaking change detection

### Platform Metrics
- **DORA metrics**: Deployment frequency, lead time, change failure rate, MTTR
- **Developer surveys**: Developer satisfaction, tooling pain points, friction logs
- **Platform adoption**: Template usage, self-service success rate, support ticket volume
- **Cost allocation**: Per-team infrastructure costs, showback/chargeback

---

## Common Tasks & Responsibilities

### Platform Development
- Build and maintain self-service developer portal (Backstage or similar)
- Create service templates (cookiecutter, Backstage scaffolder) for common patterns
- Design and maintain shared CI/CD pipeline templates
- Build internal CLIs and developer tools

### Infrastructure Abstraction
- Create Terraform modules/Helm charts that encapsulate best practices
- Manage Kubernetes namespaces, RBAC, resource quotas per team
- Automate environment provisioning (staging, preview environments per PR)
- Abstract cloud provider details behind platform APIs

### Developer Enablement
- Reduce onboarding time for new developers (goal: productive on day 1)
- Maintain developer documentation and runbooks
- Run platform office hours and provide tier-2 support
- Collect developer feedback and prioritize platform improvements

### Standardization
- Define and enforce golden paths for common service patterns
- Maintain service scorecards (observability, security, documentation readiness)
- Automate compliance checks (security scanning, license checking, dependency updates)
- Balance standardization with team autonomy — guardrails, not gates

---

## Questions Asked During Planning

### Platform Design
- "Can teams self-service this, or does it require a ticket?"
- "Does this fit our golden path, or is it a legitimate exception?"
- "What's the abstraction level — should developers see Kubernetes, or not?"
- "How do we handle teams that need to go off the golden path?"

### Developer Experience
- "How long does it take a new developer to make their first deploy?"
- "What's the most common support request we get? Can we automate it?"
- "Are developers happy with the platform? What are the biggest friction points?"
- "Can we add a self-service option for this common infrastructure request?"

### Adoption
- "What percentage of services use the standard template?"
- "What's blocking teams from adopting the platform?"
- "How do we migrate existing services to the new platform without disruption?"

---

## Integration with Other Specializations

### With DevOps
- **CI/CD**: Platform provides templates, DevOps provides pipeline infrastructure
- **IaC**: Platform creates reusable modules, DevOps manages underlying infra
- **Overlap management**: Platform is the product, DevOps is the practice

### With Site Reliability
- **Production readiness**: Platform enforces readiness checklist via scorecards
- **Observability defaults**: Templates include instrumentation out of the box
- **Incident tooling**: Platform integrates on-call tools and runbook links

### With Security
- **Secure defaults**: Templates include security scanning, secrets management
- **Compliance automation**: Policy-as-code, automated checks in CI/CD
- **Access management**: RBAC templates, service account provisioning

### With Backend/Frontend
- **Service creation**: Developers use platform templates to scaffold new services
- **Environment management**: Preview environments, staging, feature branches
- **Dependency management**: Automated dependency updates (Dependabot, Renovate)

---

## Growth Trajectory

### Junior
- **Capabilities**: Maintain existing templates, write documentation, handle support tickets
- **Learning**: Kubernetes basics, CI/CD pipelines, Terraform, developer workflows
- **Focus**: Understand developer pain points by doing support rotation

### Mid-Level
- **Capabilities**: Build new platform features, create service templates, automate workflows
- **Learning**: Platform architecture, Backstage plugins, API gateway configuration
- **Focus**: Own a platform subsystem, measure and improve developer experience

### Senior
- **Capabilities**: Platform strategy, multi-team adoption, organizational change management
- **Leadership**: Define golden paths, balance standardization vs. flexibility, executive communication
- **Focus**: Platform as a product — roadmap, user research, adoption metrics, team enablement

---

**Key Principle**: A platform team's customer is the developer. Build the platform like a product: user research, iterative delivery, adoption metrics, and support. The best platform is invisible — developers get secure, observable, well-architected services without thinking about it.
