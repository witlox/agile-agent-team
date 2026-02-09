# Domain Context: SaaS Project Management (TaskFlow)

**Product**: TaskFlow — Collaborative Task Management for Software Teams
**Industry**: SaaS B2B Software
**Target Market**: Software development teams (5-50 people)

This document provides domain context that all team members should understand, layered by seniority.

---

## Product Overview

Task Flow is a task management and collaboration tool designed specifically for agile software teams. It combines kanban boards, sprint planning, time tracking, and team analytics in one integrated platform.

### Core Value Proposition
- **For developers**: Integrated git workflows, code review links, deployment tracking
- **For product**: Story mapping, roadmap visualization, stakeholder dashboards
- **For managers**: Velocity tracking, burndown charts, resource allocation

### Target Customers
- Startups (5-20 engineers): Need structure without enterprise complexity
- Scale-ups (20-100 engineers): Multiple teams, need coordination
- Remote-first companies: Async collaboration, timezone-aware features

---

## Key Features

### Kanban Boards
- Customizable columns, WIP limits
- Card dependencies, blockers
- Swimlanes (by team, priority, assignee)
- Board templates for common workflows

### Sprint Management
- Sprint planning with capacity planning
- Burndown/burnup charts
- Velocity tracking (story points, tasks)
- Sprint retrospectives with action items

### Integrations
- **Git**: GitHub, GitLab, Bitbucket (PR links, deployment status)
- **Communication**: Slack, Microsoft Teams (notifications, bot commands)
- **CI/CD**: Jenkins, CircleCI, GitHub Actions (build status on cards)
- **Time Tracking**: Toggl, Harvest, native time tracking

### Analytics
- Cycle time, lead time, flow efficiency
- Team velocity trends
- Bottleneck identification
- Custom dashboards

---

## Technical Architecture (High-Level)

### Frontend
- React SPA with TypeScript
- Real-time updates (WebSockets)
- Offline-capable (Service Workers)
- Mobile-responsive

### Backend
- Node.js + TypeScript (REST + GraphQL)
- PostgreSQL (primary data store)
- Redis (caching, pub/sub)
- Elasticsearch (search)

### Infrastructure
- AWS (multi-region: us-east-1, eu-west-1)
- Kubernetes (EKS)
- CloudFront CDN
- S3 (file attachments, exports)

---

## Domain Concepts (All Seniority Levels Learn)

### Cards (Tasks/Stories)
- **Types**: Story, bug, epic, spike
- **Properties**: Title, description, points, assignees, labels, due date
- **Lifecycle**: Backlog → Ready → In Progress → Review → Done
- **Metadata**: Created date, completed date, cycle time

### Sprints
- Time-boxed (1-4 weeks, typically 2)
- Velocity measured in story points
- Capacity planning based on team availability
- Can span calendar month boundaries (edge case!)

### Teams
- Multi-team support (team hierarchy)
- Team-specific boards
- Cross-team dependencies
- Shared backlog or team backlogs

### Permissions
- Organization → Team → Project hierarchy
- Roles: Admin, Manager, Member, Guest
- RBAC (role-based access control)
- Resource-based permissions (own cards)

---

## Common User Workflows

### Developer Daily Workflow
1. Check board for assigned tasks
2. Move card to "In Progress"
3. Create branch (git integration suggests branch name)
4. Work on feature, push commits
5. Create PR (linked to card automatically)
6. Move to "Review" when PR ready
7. After merge, move to "Done"

### Product Owner Workflow
1. Groom backlog (prioritize, refine stories)
2. Sprint planning (drag stories into sprint)
3. Monitor sprint progress (burndown chart)
4. Accept completed stories
5. Stakeholder reporting (export metrics)

### Manager Workflow
1. Review team velocity trends
2. Identify bottlenecks (cards stuck in columns)
3. Capacity planning for next sprint
4. Cross-team dependency tracking
5. Resource allocation

---

## This context is the foundation. Juniors learn the basics, mids understand edge cases, seniors see system implications. See layered files for seniority-specific knowledge.
