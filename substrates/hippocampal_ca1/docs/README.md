# Documentation Structure

## 📁 Organization

- **[EVOLUTION_PLAN.md](EVOLUTION_PLAN.md)** - Complete v3.0 development roadmap (8 phases)
- **roadmap/** - Phase-specific tracking and issue breakdowns
- **architecture/** - Architecture Decision Records (ADRs) and design docs

## 🎯 Using the Evolution Plan

1. **Find your task**: Browse [EVOLUTION_PLAN.md](EVOLUTION_PLAN.md)
2. **Create issue**: Use Phase Task template in GitHub
3. **Work on it**: Create feature branch
4. **Submit PR**: Reference the issue, complete checklist
5. **Review**: Exit criteria must be met

## 📊 Progress Tracking

- **Issues**: All phase tasks tracked via GitHub Issues
- **PRs**: Each PR maps to specific section in Evolution Plan
- **Milestones**: Each phase is a GitHub Milestone
- **Projects**: Visual board showing phase progress

## ✅ Exit Criteria

Each phase section has explicit exit criteria. PRs cannot be merged until:
- All tasks completed
- All deliverables provided
- Exit criteria verified
- Tests pass (where applicable)

## 🔄 Workflow

```
Evolution Plan Section
    ↓
GitHub Issue (Phase Task template)
    ↓
Feature Branch
    ↓
Pull Request (references issue)
    ↓
Review (check exit criteria)
    ↓
Merge (update Evolution Plan status)
    ↓
Close Issue
```

## 📝 Templates

- **Issue**: `.github/ISSUE_TEMPLATE/phase-task.yml`
- **PR**: `.github/PULL_REQUEST_TEMPLATE.md`
