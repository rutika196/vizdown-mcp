# Git Branching Strategy

Our team's Git workflow: main → develop → feature branches, with release
branches and hotfix support. Shows the full lifecycle of a feature from
creation through review, merge, release, and hotfix.

```mermaid
gitGraph
    commit id: "v1.0.0" tag: "v1.0.0"
    branch develop
    checkout develop
    commit id: "setup CI"
    commit id: "add linting"

    branch feature/auth
    checkout feature/auth
    commit id: "auth: JWT service"
    commit id: "auth: login endpoint"
    commit id: "auth: MFA support"
    checkout develop
    merge feature/auth id: "merge auth" tag: "auth-complete"

    branch feature/orders
    checkout feature/orders
    commit id: "orders: model"
    commit id: "orders: API"
    commit id: "orders: tests"
    checkout develop
    merge feature/orders id: "merge orders"

    branch release/1.1
    checkout release/1.1
    commit id: "bump version 1.1"
    commit id: "fix: edge case"
    checkout main
    merge release/1.1 id: "v1.1.0" tag: "v1.1.0"
    checkout develop
    merge release/1.1 id: "back-merge 1.1"

    checkout main
    branch hotfix/cve-fix
    commit id: "patch CVE-2025-1234"
    checkout main
    merge hotfix/cve-fix id: "v1.1.1" tag: "v1.1.1"
    checkout develop
    merge hotfix/cve-fix id: "back-merge hotfix"

    checkout develop
    commit id: "refactor: cleanup"
    commit id: "feat: dashboard"
```
