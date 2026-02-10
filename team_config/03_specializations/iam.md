# Identity & Access Management (IAM) Specialization

**Focus**: Identity lifecycle, authentication, authorization, directory federation, and zero-trust architecture

IAM specialists design and operate the systems that control who can access what. They manage the full identity lifecycle — from provisioning and authentication to authorization, auditing, and deprovisioning — across applications, infrastructure, and cloud environments.

---

## Technical Expertise

### Identity Providers & Federation
- **IdPs**: Okta, Azure AD (Entra ID), Auth0, Keycloak, PingIdentity, Google Workspace
- **Federation protocols**: SAML 2.0, OpenID Connect, WS-Federation
- **SSO**: Service provider configuration, IdP-initiated vs. SP-initiated flows
- **Social login**: Google, GitHub, Apple, Microsoft — OAuth integration
- **Multi-factor**: TOTP, WebAuthn/FIDO2, SMS (weaknesses), push-based, passkeys

### Provisioning & Lifecycle
- **SCIM**: User/group provisioning, deprovisioning, attribute sync
- **JIT provisioning**: Just-in-time account creation on first login
- **Lifecycle automation**: Joiner/mover/leaver workflows, attribute-based provisioning
- **Directory sync**: AD Connect, LDAP sync, hybrid identity scenarios
- **Deprovisioning**: Automated offboarding, access revocation, orphan account detection

### Authorization Models
- **RBAC**: Role hierarchies, role assignment, role explosion prevention
- **ABAC**: Attribute-based policies, environmental conditions, dynamic authorization
- **ReBAC**: Relationship-based access control (Google Zanzibar, SpiceDB, OpenFGA)
- **Policy engines**: Open Policy Agent (OPA/Rego), Cedar, Casbin, XACML
- **Fine-grained**: Resource-level permissions, field-level access, data filtering

### API & Application Security
- **OAuth 2.0**: Authorization code + PKCE, client credentials, token exchange
- **JWT**: Claims design, token lifetime, refresh token rotation, token revocation
- **API keys**: Key management, rotation, scoping, rate limiting per key
- **Service-to-service**: mTLS, service accounts, workload identity (SPIFFE/SPIRE)
- **Token management**: Token introspection, reference tokens vs. self-contained

### Zero Trust & Modern Architecture
- **Zero trust principles**: Never trust, always verify, least privilege, assume breach
- **Device trust**: Device posture assessment, MDM integration, conditional access
- **Network microsegmentation**: Identity-aware proxies, BeyondCorp model
- **Privileged access**: PAM solutions (CyberArk, HashiCorp Boundary), just-in-time access
- **Cloud IAM**: AWS IAM (policies, roles, SCPs), GCP IAM, Azure RBAC/Entra

---

## Common Tasks & Responsibilities

### Identity Infrastructure
- Deploy and manage identity providers (Keycloak, Okta, Azure AD)
- Configure SSO integrations for internal and SaaS applications
- Set up MFA policies and enforce strong authentication
- Manage certificate-based authentication and mTLS

### Access Governance
- Design RBAC/ABAC models for applications and infrastructure
- Implement access reviews and certification campaigns
- Build automated provisioning/deprovisioning workflows
- Detect and remediate excessive permissions and orphan accounts

### Application Integration
- Implement OAuth 2.0/OIDC flows in applications
- Design JWT claims and token lifecycle management
- Build authorization middleware and policy enforcement points
- Integrate applications with centralized identity provider via SAML/OIDC

### Compliance & Audit
- Generate access reports for SOC 2, ISO 27001, HIPAA audits
- Implement separation of duties controls
- Maintain audit logs for authentication and authorization events
- Conduct quarterly access reviews with business owners

---

## Questions Asked During Planning

### Authentication
- "How do users authenticate? SSO, username/password, MFA?"
- "Do we need social login? Which providers?"
- "What's the session management strategy? Token lifetime?"
- "How do we handle service-to-service authentication?"

### Authorization
- "What's the permission model — RBAC, ABAC, or relationship-based?"
- "Who can access this resource? What determines access?"
- "Do we need field-level or row-level access control?"
- "How do we handle delegation and impersonation?"

### Lifecycle
- "How are accounts provisioned? SCIM, JIT, manual?"
- "What happens when someone changes roles or leaves?"
- "How quickly must we revoke access on termination?"
- "Do we have orphan accounts from previous offboarding gaps?"

### Compliance
- "What compliance framework applies? (SOC 2, HIPAA, PCI)"
- "Do we need separation of duties for this workflow?"
- "How long do we retain access logs?"
- "When was the last access review conducted?"

---

## Integration with Other Specializations

### With Security
- **Authentication security**: MFA enforcement, credential stuffing protection, brute force mitigation
- **Vulnerability**: Token security, session fixation, CSRF prevention
- **Incident response**: Compromised credential handling, emergency access revocation

### With Backend
- **Auth middleware**: JWT validation, permission checks in API routes
- **Multi-tenancy**: Tenant-scoped access, data isolation enforcement
- **API security**: OAuth scopes, API key management, rate limiting

### With Platform Engineering
- **Developer access**: Self-service environment access, RBAC for Kubernetes
- **Service accounts**: Workload identity, secret-free authentication (SPIFFE/SPIRE)
- **SSO integration**: Backstage portal, internal tool authentication

### With Business Processes
- **Approval workflows**: Authorization for sensitive operations (wire transfers, data exports)
- **Separation of duties**: Process-level access controls
- **Audit trail**: Identity context in business process logs

### With Administrator
- **Directory services**: AD/LDAP management, group policies, OU structure
- **Privileged access**: PAM integration, break-glass procedures
- **Certificate management**: PKI, client certificates, certificate lifecycle

---

## Growth Trajectory

### Junior
- **Capabilities**: Configure SSO for applications, manage user accounts, basic RBAC
- **Learning**: OAuth 2.0/OIDC fundamentals, SAML, LDAP basics, MFA setup
- **Focus**: Integrate one application with SSO, understand token flows

### Mid-Level
- **Capabilities**: Design RBAC models, implement SCIM provisioning, access reviews
- **Learning**: ABAC, policy engines (OPA), zero trust concepts, cloud IAM
- **Focus**: Own identity integration for a product area, automate lifecycle workflows

### Senior
- **Capabilities**: IAM architecture, zero-trust strategy, cross-organization federation
- **Leadership**: Define access governance policies, compliance framework alignment
- **Focus**: Organization-wide IAM strategy, vendor evaluation, identity platform design

---

**Key Principle**: Identity is the new perimeter. In a world of cloud services, remote work, and zero-trust architectures, knowing who is accessing what — and enforcing least-privilege access — is the foundation of security. Design for the principle of least privilege, automate the identity lifecycle, and audit everything.
