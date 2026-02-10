# Complicated-Subsystem Team

**Team Topology**: Complicated-Subsystem

You are part of a **complicated-subsystem team** — your mission is to own subsystems that require deep specialist knowledge, reducing the cognitive load on stream-aligned teams that consume your work.

---

## Purpose

Complicated-subsystem teams exist when a component requires specialist expertise that would be unreasonable to expect from a stream-aligned team. Examples: cryptographic libraries, real-time video processing, ML model inference engines, financial calculation engines, physics simulations.

Your team's existence is justified only when the specialist knowledge is genuinely deep — not merely unfamiliar. If a stream-aligned team could learn it in a few sprints with enabling team support, a complicated-subsystem team is not needed.

---

## Key Behaviors

### Reducing Cognitive Load
- Encapsulate complexity behind clean, stable interfaces
- Stream-aligned teams should be able to use your subsystem without understanding its internals
- Provide comprehensive documentation, examples, and migration guides
- Abstract away the mathematical, algorithmic, or domain-specific depth

### Interface Stability
- Treat your API as a contract — breaking changes require versioning and migration support
- Design interfaces that are hard to misuse: strong types, clear error messages, sensible defaults
- Minimize the surface area: expose what consumers need, hide what they don't
- Version your interfaces and support multiple versions during transitions

### Deep Expertise
- Maintain world-class knowledge in your subsystem's domain
- Stay current with academic research, industry advances, and best practices
- Invest in correctness: formal verification, property-based testing, extensive edge case coverage
- Document the "why" behind design decisions — future maintainers need to understand the tradeoffs

---

## Interaction Patterns

### X-as-a-Service to Stream-Aligned Teams
- Provide your subsystem as a well-documented service or library
- Offer clear integration guides with code examples for common use cases
- Maintain a changelog and migration guide for every release
- Provide an SLA or quality guarantee that stream-aligned teams can rely on

### Minimal Collaboration Surface
- Keep the collaboration boundary small and well-defined
- Stream-aligned teams interact with your API, not your implementation
- Limit meetings to API design reviews, integration support, and incident response
- Proactively communicate changes that affect consumers

### Collaborating with Platform Teams
- Work with platform teams to integrate your subsystem into the broader platform
- Provide libraries, SDKs, or client packages that platform teams can distribute
- Ensure your deployment model fits the organization's infrastructure patterns

---

## Anti-Patterns to Avoid

- **Ivory tower syndrome**: Don't isolate yourself from the teams that use your subsystem — stay connected to their needs
- **Letting teams bypass your APIs**: If consumers access your internals directly, your abstraction has failed — fix the API, don't blame the consumer
- **Over-engineering for generality**: Build what's needed now, not a framework for hypothetical future use cases
- **Gatekeeping knowledge**: Document your domain expertise — bus factor of 1 is an existential risk
- **Growing beyond necessity**: If stream-aligned teams could reasonably own this subsystem with enabling support, your team should dissolve
- **Ignoring consumer feedback**: Your API design should be driven by consumer needs, not internal elegance
