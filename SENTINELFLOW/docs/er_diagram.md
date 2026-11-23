# Database entity–relationship diagram

```mermaid
erDiagram
    USER ||--o{ USER_ACTIVITY : performs
    USER ||--o{ USER_SESSION : opens
    USER ||--o| USER_RISK_PROFILE : has
    USER ||--o{ DETECTION_RESULT : scored_as
    USER ||--o{ SECURITY_ALERT : subject_of
    USER ||--o{ SECURITY_ALERT : assigned_to
    USER ||--o{ INVESTIGATION_CASE : assigned_to
    USER ||--o{ INVESTIGATION_CASE : opened_by
    USER ||--o{ GENERATED_REPORT : generates
    USER ||--o{ AUDIT_LOG : acts

    USER_ACTIVITY ||--o| DETECTION_RESULT : evaluated_by
    USER_ACTIVITY ||--o{ SECURITY_ALERT : triggers
    USER_ACTIVITY }o--o{ INVESTIGATION_CASE : evidence
    DETECTION_RESULT ||--o{ SECURITY_ALERT : raises
    SECURITY_ALERT ||--o| INVESTIGATION_CASE : investigated_by
    SECURITY_ALERT ||--o{ ALERT_NOTE : documents
    INVESTIGATION_CASE ||--o{ INVESTIGATION_NOTE : documents
    DETECTION_MODEL_RUN ||--o{ DETECTION_RESULT : produced_by

    USER {
        bigint id PK
        string username UK
        string email
        string role
        string department
        string employee_id UK
        boolean is_active
        datetime date_joined
    }
    USER_ACTIVITY {
        bigint id PK
        bigint user_id FK
        string activity_type
        datetime timestamp
        string ip_address
        string resource
        bigint bytes_transferred
        boolean is_off_hours
        boolean is_unusual_location
        string source
        json metadata
    }
    USER_SESSION {
        bigint id PK
        bigint user_id FK
        string session_key UK
        datetime login_at
        datetime logout_at
    }
    DETECTION_RESULT {
        bigint id PK
        bigint activity_id FK UK
        bigint user_id FK
        string model_name
        string classification
        float risk_score
        float anomaly_score
        float confidence
        json reasons
        json features
    }
    USER_RISK_PROFILE {
        bigint id PK
        bigint user_id FK UK
        float risk_score
        string risk_level
        int total_activities
        int suspicious_count
        int critical_count
        datetime last_calculated
    }
    SECURITY_ALERT {
        bigint id PK
        bigint user_id FK
        bigint activity_id FK
        bigint detection_id FK
        string severity
        string status
        float risk_score
        json evidence
        datetime created_at
    }
    ALERT_NOTE {
        bigint id PK
        bigint alert_id FK
        bigint author_id FK
        text note
    }
    INVESTIGATION_CASE {
        bigint id PK
        uuid case_id UK
        bigint alert_id FK UK
        bigint subject_id FK
        bigint assigned_to_id FK
        string status
        string priority
        text findings
        text conclusion
    }
    INVESTIGATION_NOTE {
        bigint id PK
        bigint case_id FK
        bigint author_id FK
        text note
    }
    GENERATED_REPORT {
        bigint id PK
        string title
        string report_type
        string file
        json parameters
        datetime created_at
    }
    AUDIT_LOG {
        bigint id PK
        bigint actor_id FK
        string action
        string entity_type
        string entity_id
        string ip_address
        json details
        datetime created_at
    }
    DETECTION_MODEL_RUN {
        bigint id PK
        string model_name
        int samples
        float accuracy
        float weighted_f1
        datetime trained_at
    }
```

## Design notes

- `DETECTION_RESULT.activity` is one-to-one: one authoritative ML verdict per event.
- `INVESTIGATION_CASE.alert` is one-to-one: an alert maps to one case; `activities` is many-to-many for evidence.
- `SECURITY_ALERT` keeps both `activity_id` and `detection_id` for fast forensic navigation while allowing alerts to be created manually.
- `AUDIT_LOG` records an actor username snapshot as well as the foreign key so history survives user deletion.
- Indexes exist on timestamp, user, classification, severity and status columns used by dashboard aggregations.
- Migrations are versioned under each app's `migrations/` directory.
