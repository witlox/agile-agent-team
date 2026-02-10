# Sprint Review / Demo

**When**: Last day of sprint, after QA review, before retrospective
**Duration**: 1-2 hours
**Participants**: Team + PO (Stakeholders join every 3 sprints via webhook)
**Purpose**: Demo completed work, get PO acceptance, gather feedback

## Important: Stakeholder Participation

**Regular Sprint Review** (most sprints):
- Team + PO only
- PO represents stakeholder interests (voice of customer)
- Fast feedback loop (within simulation time)

**Major Stakeholder Review** (Every 3 sprints, configurable):
- Team + PO + Real stakeholders (researchers, users)
- Happens ASYNCHRONOUSLY via webhook notification + feedback collection
- Review accumulated work from 3 sprints
- Stakeholders provide strategic feedback (file drop or HTTP callback)
- Configurable timeout: auto_approve, po_proxy, or block
- Slow feedback loop (human time scale)

## Overview

Sprint Review is **NOT**:
- ❌ A status report ("we're 75% done")
- ❌ A code review (that happened in QA)
- ❌ A planning session (that's next sprint)

Sprint Review **IS**:
- ✅ A demo of **working software**
- ✅ PO accepting or rejecting completed stories
- ✅ PO providing feedback (representing stakeholders)
- ✅ Collaborative discussion about what to build next

## PO's Dual Role

In regular sprint reviews, **PO represents stakeholder interests**:
- **Voice of the customer**: "Users need this to be simpler"
- **Business perspective**: "This doesn't deliver enough value"
- **Strategic alignment**: "Let's focus on enterprise features next"

This keeps the feedback loop **fast** (within simulation time). Real stakeholders review every 3 sprints via webhook notification and file/callback feedback collection.

## Format

### Regular Sprint Review (Most Sprints)

For each completed story:
1. **Team demonstrates** (5-10 min)
2. **PO reviews acceptance criteria** (2-3 min)
3. **PO accepts/rejects** (1 min)
4. **PO provides feedback** (2-3 min)
5. **Capture follow-up items** (as needed)

### Major Stakeholder Review (Every 3 Sprints, Configurable)

After 3 sprints of accumulated work:
1. **Webhook notification sent** (rich sprint summary to Slack/Teams/Matrix/generic)
2. **Team prepares demo** (highlights from 3 sprints)
3. **Stakeholders review asynchronously** (file drop or HTTP callback)
4. **Strategic feedback captured** (roadmap adjustments, priorities, new stories)
5. **Simulation RESUMES** with stakeholder feedback applied to backlog

---

## Your Role as the Demonstrator

### Before Sprint Review

1. **Prepare your demo**:
   - Test that the feature actually works
   - Prepare test data / demo accounts
   - Have a backup plan if live demo fails (screenshots, video)
   - Practice your walkthrough (5 minutes max)

2. **Know the acceptance criteria**:
   - Review the original story
   - Can you prove each criterion is met?
   - What edge cases did you handle?

3. **Anticipate questions**:
   - "How does this handle [edge case]?"
   - "Can this scale to [large number]?"
   - "How does this integrate with [existing feature]?"

### During Your Demo

1. **Start with context** (30 seconds):
   - Story ID and title
   - **Why** we built this (business value)
   - **Who** worked on it (pair names)

2. **Demo the happy path** (3 minutes):
   - Show the feature from a user's perspective
   - Walk through the primary use case
   - Narrate what you're doing: "As a user, I navigate to..."

3. **Demo edge cases** (1-2 minutes):
   - Show error handling
   - Show validation
   - Show any special cases from acceptance criteria

4. **Highlight interesting tech** (1 minute):
   - Only if it's impressive or innovative
   - "We used Redis for 10x faster auth lookups"
   - Don't dive into code details

### Example Demo Script

**Story**: US-042 - Add two-factor authentication

> **Context** (30s):
> "Story US-042: Add two-factor authentication. This unlocks $500K in enterprise deals by meeting SOC2 compliance requirements. Marcus and I paired on the implementation, with Maya and Priya on the backend services."
>
> **Demo happy path** (3m):
> "Let me show you the user enrollment flow. I'm logged in as a test user. I navigate to Security Settings... click 'Enable Two-Factor Authentication'... the system generates a QR code... I scan it with Google Authenticator... enter the 6-digit code... and now 2FA is enabled."
>
> "Next login, I'll be prompted for the code. Here I am logged out... entering my password... now it asks for my authenticator code... I enter it... and I'm in."
>
> **Demo edge cases** (1m):
> "If I lose my phone, I can use backup codes. Here are the 10 single-use codes generated during enrollment. Let me try one... works! Now that code is invalidated."
>
> "If I enter the wrong code 3 times, I'm locked out and need to reset via email."
>
> **Tech highlight** (30s):
> "Under the hood, we're using RFC 6238 TOTP with Redis for rate limiting. Average auth time is under 100ms."

---

## PO's Review Process

The PO will check each acceptance criterion:

### Acceptance Criteria for US-042
- ✅ Users can enable 2FA with authenticator app
- ✅ QR code enrollment flow works
- ✅ Backup codes provided (10 single-use codes)
- ✅ Forced re-auth if device changes
- ❌ Admin can enforce 2FA for organization (not implemented)

### PO Decisions

**✅ ACCEPTED**
- All acceptance criteria met
- Story moves to "Done"
- Team celebrates! 🎉

**❌ REJECTED**
- Critical criteria not met
- Story returns to "In Progress"
- Must be fixed before next sprint review
- Example: "Admin enforcement is a must-have for the enterprise contract"

**🤔 ACCEPTED WITH NOTES**
- All criteria met, but improvements identified
- Story moves to "Done"
- Follow-up stories created for improvements
- Example: "Works great, but UX could be smoother - let's refine in next sprint"

---

## Responding to PO Feedback

### PO Asks: "Can you add [new feature]?"

**Good response**:
> "That's a great idea! Let's add it to the backlog and you can prioritize it for an upcoming sprint."

**Bad response**:
> "Sure, we can add that this week!" ← **Don't scope creep mid-sprint!**

### PO Asks: "Why didn't you implement [thing]?"

**Good response**:
> "That wasn't in the original acceptance criteria. If it's important, we can add it as a follow-up story."

**Bad response**:
> "We didn't have time" ← Makes team look unprofessional

### PO Says: "The UX isn't intuitive"

**Good response**:
> "Thanks for the feedback. Can you show me where you got confused? We can improve that in the next iteration."

**Bad response**:
> "It works fine for us" ← Defensive, dismisses feedback

---

## Major Stakeholder Review (Every 5 Sprints)

When real stakeholders join (researchers, users), the dynamic is different:

### Stakeholder Review Purpose
- **Strategic alignment**: Are we building the right product?
- **Priority validation**: Should we continue current direction?
- **Roadmap adjustments**: What should next sprints focus on?
- **Research feedback**: How well is the simulated team performing?

### What Stakeholders Review
- **Cumulative demos**: Highlights from recent sprints of work
- **Velocity trends**: Story points delivered per sprint
- **Quality metrics**: Test coverage, acceptance rate, cycle time
- **Team dynamics**: Pairing patterns, meta-learnings, improvements

### Stakeholder Feedback Format
Stakeholders respond via file drop or HTTP callback:
- JSON feedback with decision (approved/rejected/approved_with_changes)
- Priority changes (reorder or deprioritize existing stories)
- New stories (added directly to backlog)
- Configurable timeout action: auto_approve, po_proxy, or block

### Integration Back Into Simulation
After stakeholder feedback is received (or timeout triggers):
1. Feedback stored in SharedContextDB
2. Priority changes applied to backlog
3. New stories added to backlog
4. `stakeholder_feedback` event published on message bus
5. Next sprints reflect stakeholder input

---

## Your Role as a Team Member (Not Presenting)

1. **Support the presenter**:
   - Jump in if they forget something
   - Answer technical questions if presenter is stuck
   - Encourage and celebrate their work

2. **Take notes on feedback**:
   - What stakeholders liked
   - What stakeholders want improved
   - New feature ideas that emerge

3. **Be ready to clarify**:
   - Technical implementation details (if stakeholder asks)
   - Trade-offs made during development
   - Why certain decisions were made

---

## Anti-Patterns

### ❌ The Technical Deep Dive
> "Let me show you the code... here's the JWT library we used... and this is how we implemented the Redis cache layer... we used a singleton pattern here..."

**Fix**: Show the feature from a user's perspective, not code.

### ❌ The Apology Tour
> "Sorry this isn't perfect... we ran out of time... the UI is a bit rough... there are some bugs..."

**Fix**: Confidently demo what works. If PO accepts it, it's good enough.

### ❌ The Incomplete Demo
> "This part works, but we haven't tested this other part yet."

**Fix**: Only demo **done** features. If it's not done, don't present it.

### ❌ The Blame Game
> "We would have finished, but the QA team was slow" or "The requirements changed mid-sprint"

**Fix**: As a team, we own outcomes. Discuss process issues in retrospective, not in front of stakeholders.

### ❌ The Sales Pitch
> "This feature will revolutionize how users interact with our platform!"

**Fix**: Be enthusiastic but honest. Let the PO handle the business value messaging.

---

## After Sprint Review

### If Your Story Was Accepted ✅
- **Celebrate** with your team
- **Document** any follow-up items
- **Update** Kanban to "Done"
- **Deploy** to production (if not already)

### If Your Story Was Rejected ❌
- **Don't take it personally** - acceptance criteria are the contract
- **Understand what's missing** - get specific details from PO
- **Prioritize fixes** - this blocks other work
- **Learn for next sprint** - how to better understand requirements

### If Feedback Was Mixed 🤔
- **Separate "must fix" from "nice to have"**
- **PO decides** what goes in backlog
- **Don't commit** to adding features without PO approval

---

## Tips by Role

### For Developers
- **Practice your demo beforehand** - smooth demos build confidence
- **Focus on user value** - not technical implementation
- **Handle failures gracefully** - if demo breaks, have a backup
- **Accept feedback professionally** - stakeholders are trying to help

### For Testers
- **Highlight quality** - "We added 50 test cases covering edge cases"
- **Demo test automation** - if stakeholders care about quality
- **Point out what wasn't tested** - be honest about coverage gaps

### For Dev Lead
- **Facilitate smooth flow** - keep demos on time
- **Field technical questions** - let presenters focus on demo
- **Mediate disagreements** - if PO and team disagree on acceptance
- **Capture action items** - ensure follow-ups are documented

### For QA Lead
- **Validate acceptance criteria** - ensure PO checks all criteria
- **Highlight quality achievements** - test coverage, performance benchmarks
- **Identify risks** - what didn't get tested thoroughly

---

## Success Metrics

A good sprint review has:
- ✅ **High acceptance rate** - Most stories meet acceptance criteria
- ✅ **Positive stakeholder feedback** - They're excited about what they see
- ✅ **Minimal surprises** - PO knew what to expect from daily updates
- ✅ **Clear action items** - Follow-up stories captured in backlog
- ✅ **Team pride** - Everyone feels good about what they built

A struggling sprint review has:
- ❌ **Low acceptance rate** - Many stories rejected
- ❌ **Confused stakeholders** - "I thought you were building X, not Y"
- ❌ **Major bugs discovered** - QA missed critical issues
- ❌ **Scope debates** - Arguing about what was "in scope"
- ❌ **Team demoralized** - Feels like failure

---

## Remember

Sprint Review is about:
- **Transparency** - Show working software honestly
- **Collaboration** - Get feedback to build better
- **Adaptation** - Use learnings to improve next sprint
- **Celebration** - Recognize the team's hard work

It's **NOT** about:
- Perfect code
- 100% complete features
- Impressing stakeholders
- Defending decisions

Be honest, be proud, be open to feedback. The goal is to build the right thing, not to look good.
