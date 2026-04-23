# Skill Registry — inventory-service

Generated: 2026-04-23

## Project Conventions

| File | Purpose |
|------|---------|
| `AGENTS.md` (hotel-ddd) | Base rules: bounded context, conventional commits, PR targets, skill usage |
| `docs/git-workflow.md` (hotel-ddd) | Branch naming, merge strategy, commit rules |
| `.github/pull_request_template.md` (hotel-ddd) | PR checklist template |

## Project Skills (hotel-ddd monorepo — `.agent/skills/`)

| Skill | Trigger | Path |
|-------|---------|------|
| `hotel-architecture-boundaries` | When creating or moving code between DDD layers or services | `.agent/skills/hotel-architecture-boundaries/SKILL.md` |
| `hotel-code-quality` | When writing, reviewing, or refactoring code | `.agent/skills/hotel-code-quality/SKILL.md` |
| `hotel-git-commit` | When preparing or suggesting a commit | `.agent/skills/hotel-git-commit/SKILL.md` |
| `hotel-pr-convention` | When creating or reviewing a Pull Request | `.agent/skills/hotel-pr-convention/SKILL.md` |
| `hotel-testing-convention` | When writing, reviewing, or improving tests | `.agent/skills/hotel-testing-convention/SKILL.md` |

## User Skills (`~/.config/opencode/skills/`)

| Skill | Trigger |
|-------|---------|
| `branch-pr` | Creating PRs following issue-first enforcement |
| `go-testing` | Writing Go tests, using teatest |
| `issue-creation` | Creating GitHub issues |
| `judgment-day` | Adversarial dual review protocol |
| `sdd-apply` | Implementing SDD change tasks |
| `sdd-archive` | Archiving completed SDD changes |
| `sdd-design` | Writing technical design for a change |
| `sdd-explore` | Exploring/investigating before a change |
| `sdd-init` | Initializing SDD in a project |
| `sdd-onboard` | SDD onboarding walkthrough |
| `sdd-propose` | Creating change proposals |
| `sdd-spec` | Writing delta specs |
| `sdd-tasks` | Breaking down change tasks |
| `sdd-verify` | Verifying implementation vs specs |
| `skill-creator` | Creating new AI agent skills |
| `skill-registry` | Updating skill registry |

## Priority (from AGENTS.md)

1. Architecture boundaries (`hotel-architecture-boundaries`)
2. Code quality (`hotel-code-quality`)
3. Testing conventions (`hotel-testing-convention`)
4. PR conventions (`hotel-pr-convention`)
5. Commit conventions (`hotel-git-commit`)
