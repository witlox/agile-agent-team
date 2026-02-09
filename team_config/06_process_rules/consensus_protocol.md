# Consensus & Escalation Protocol

## Decision Tiers

### Tier 1: Pair Decides (No Escalation)
- Code structure within module
- Test strategy for feature
- Refactoring existing code
- Algorithm selection

### Tier 2: Dev Lead Decides (Escalate from Pair)
- Cross-module architecture
- New dependencies
- Performance trade-offs affecting multiple features

### Tier 3: PO + Dev Lead (Escalate from Dev Lead)
- Scope changes mid-sprint
- Technical debt vs. feature priority
- Timeline adjustments

### Tier 4: Stakeholder (Escalate from PO)
- Product direction pivots
- Major technical rewrites
- Resource constraints

## Escalation Format
1. Context: What decision?
2. Options: What trade-offs?
3. Recommendation: What does pair/lead suggest?
4. Urgency: Blocking or can defer?

## Deadlock Resolution
If PO and Dev Lead can't agree:
- Team weighted vote (technical = dev lead 70%, business = PO 70%)
- If vote < 60% consensus, escalate to stakeholder
