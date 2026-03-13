# SaaS Multi-Tenant Database Schema

Full relational schema for a multi-tenant SaaS platform with organizations,
users, roles, projects, tasks, comments, billing, and audit logging.

```mermaid
erDiagram
    ORGANIZATIONS {
        uuid id PK
        string name
        string slug UK
        string plan_tier
        int max_seats
        datetime created_at
        datetime updated_at
    }
    USERS {
        uuid id PK
        uuid org_id FK
        string email UK
        string password_hash
        string first_name
        string last_name
        string avatar_url
        string role
        boolean is_active
        datetime last_login
        datetime created_at
    }
    PROJECTS {
        uuid id PK
        uuid org_id FK
        uuid owner_id FK
        string name
        string description
        string status
        string color
        date start_date
        date due_date
        datetime created_at
    }
    TASKS {
        uuid id PK
        uuid project_id FK
        uuid assignee_id FK
        uuid parent_task_id FK
        string title
        text description
        string priority
        string status
        int story_points
        date due_date
        int position
        datetime completed_at
        datetime created_at
    }
    COMMENTS {
        uuid id PK
        uuid task_id FK
        uuid author_id FK
        text body
        boolean is_edited
        datetime created_at
        datetime updated_at
    }
    TAGS {
        uuid id PK
        uuid org_id FK
        string name
        string color
    }
    TASK_TAGS {
        uuid task_id FK
        uuid tag_id FK
    }
    ATTACHMENTS {
        uuid id PK
        uuid task_id FK
        uuid uploaded_by FK
        string filename
        string content_type
        bigint size_bytes
        string storage_url
        datetime created_at
    }
    INVOICES {
        uuid id PK
        uuid org_id FK
        decimal amount
        string currency
        string status
        date period_start
        date period_end
        datetime paid_at
        datetime created_at
    }
    AUDIT_LOG {
        uuid id PK
        uuid org_id FK
        uuid user_id FK
        string action
        string entity_type
        uuid entity_id
        jsonb old_values
        jsonb new_values
        inet ip_address
        datetime created_at
    }

    ORGANIZATIONS ||--o{ USERS : "has members"
    ORGANIZATIONS ||--o{ PROJECTS : "owns"
    ORGANIZATIONS ||--o{ TAGS : "defines"
    ORGANIZATIONS ||--o{ INVOICES : "billed via"
    ORGANIZATIONS ||--o{ AUDIT_LOG : "tracked in"
    USERS ||--o{ PROJECTS : "owns"
    USERS ||--o{ TASKS : "assigned to"
    USERS ||--o{ COMMENTS : "writes"
    USERS ||--o{ ATTACHMENTS : "uploads"
    USERS ||--o{ AUDIT_LOG : "performs"
    PROJECTS ||--o{ TASKS : "contains"
    TASKS ||--o{ TASKS : "subtask of"
    TASKS ||--o{ COMMENTS : "discussed in"
    TASKS ||--o{ ATTACHMENTS : "has"
    TASKS ||--o{ TASK_TAGS : "labeled with"
    TAGS ||--o{ TASK_TAGS : "applied to"
```

## Schema Notes

- **Multi-tenancy** via `org_id` foreign key on most tables
- **Hierarchical tasks** — `parent_task_id` self-reference for subtasks
- **Soft positions** — `position` integer for drag-and-drop reordering within projects
- **Audit trail** — Every mutation logged with old/new JSON values + IP address
- **Billing** — Invoices track per-period charges with payment status
