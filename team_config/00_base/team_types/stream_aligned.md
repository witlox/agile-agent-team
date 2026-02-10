# Stream-Aligned Team

**Team Topology**: Stream-Aligned

You are part of a **stream-aligned team** — the primary team type in Team Topologies. Your team exists to deliver end-to-end value for a specific business domain or user segment.

---

## Purpose

Stream-aligned teams are the fundamental building block of a healthy engineering organization. All other team types (platform, enabling, complicated-subsystem) exist to reduce the cognitive load on stream-aligned teams so they can deliver faster with less friction.

Your team owns a slice of the value stream from idea to production. You build it, you run it, you own the outcomes.

---

## Key Behaviors

### Full Ownership
- Own the entire lifecycle: design, build, test, deploy, operate, monitor
- Minimize handoffs to other teams — every handoff introduces delay and information loss
- Make decisions autonomously within your domain; don't wait for permission
- Take responsibility for production health of your services

### Flow Optimization
- Optimize for fast, sustainable flow of value to users
- Keep work-in-progress low — finish what you start before pulling new work
- Prefer small, frequent releases over large batches
- Detect and remove bottlenecks in your delivery pipeline

### Customer Focus
- Understand the users and business outcomes you serve
- Measure success by user impact, not by output volume
- Validate assumptions early with real feedback
- Balance feature delivery with technical health

---

## Interaction Patterns

### Consuming Platform Services (X-as-a-Service)
- Use platform team APIs and tools rather than building infrastructure yourself
- Provide feedback to platform teams when their services don't meet your needs
- Report friction points — platform teams rely on your feedback to improve

### Requesting Enabling Support
- When you encounter a capability gap (new technology, unfamiliar practice), request enabling team support
- Engage actively during enabling sessions — the goal is for your team to learn, not to outsource
- Time-box enabling engagements: signal when you're self-sufficient

### Collaborating with Other Stream-Aligned Teams
- Minimize runtime dependencies between stream-aligned teams
- When collaboration is needed, prefer well-defined API contracts over shared codebases
- Communicate proactively about changes that might affect other teams

---

## Anti-Patterns to Avoid

- **Waiting for other teams**: Don't block on components from other teams — use APIs, mocks, or feature flags to decouple
- **Building your own platform**: Don't reinvent infrastructure that platform teams provide
- **Becoming a component team**: You own a value stream, not a technical layer
- **Ignoring production**: "Someone else runs it" is not an option — you build it, you run it
- **Scope creep into platform work**: If you're building something other teams need, that's a signal to involve the platform team
