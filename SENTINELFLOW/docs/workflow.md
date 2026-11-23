# End-to-end workflows

> SENTINELFLOW · **23/11/2026**

This document describes the five operational flows that power the application. Diagrams use Mermaid and render natively on GitHub.

---

## 1. Activity ingestion

Events can enter from five sources. Every path converges on validation, persistence, and detection.

```mermaid
flowchart TD
    A1[Web event form] --> V
    A2[REST API POST /activities/] --> V
    A3[Login / logout signals] --> V
    A4[Django admin] --> V
    A5[CSV seed command] --> V

    V{Form / serializer validation}
    V -->|invalid| E[400 / form errors + audit]
    V -->|valid| P[Save UserActivity]
    P --> A[AuditRequestMiddleware logs actor + entity]
    P --> D[Run detection pipeline]
    D --> R[Return detail page or JSON response]
```

**Validation rules**

- `activity_type`, `timestamp`, `ip_address`, `resource` are required.
- `bytes_transferred` must be a non-negative integer.
- Viewers cannot write; the API enforces read-only permissions.
- Sensitive POST fields are redacted before audit persistence.

---

## 2. Detection and scoring

```mermaid
flowchart LR
    S[UserActivity] --> F1[1-hour window features]
    S --> F2[24-hour window features]
    F1 --> X[14 ordered features<br/>ml/features.py]
    F2 --> X
    X --> SC[StandardScaler]
    SC --> RF[RandomForestClassifier<br/>class probabilities × 0.70]
    SC --> IF[IsolationForest<br/>anomaly index × 0.30]
    RF --> M[Weighted risk score 0–100]
    IF --> M
    RULES[Explainable rule signals] --> M
    M --> C{Classification}
    C -->|risk below 40| N[NORMAL]
    C -->|risk 40 to 69| SUS[SUSPICIOUS]
    C -->|risk 70 or above| CRIT[CRITICAL]
    N --> DR[DetectionResult]
    SUS --> DR
    CRIT --> DR
    DR --> RP[Recompute UserRiskProfile]
```

**Fallback behaviour**

If `ml/artifacts/*.joblib` is missing, `ml/predict.py` uses deterministic rules only and records `model_name="RULE_BASED_FALLBACK"`. The application never fails because a model file is absent.

---

## 3. Alert creation and triage

```mermaid
sequenceDiagram
    autonumber
    participant D as DetectionResult
    participant A as Alert Engine
    participant DB as Database
    participant AN as Analyst

    D->>A: Suspicious / critical classification
    A->>DB: Find existing open alert for user + activity
    alt duplicate exists
        A->>DB: Update severity / evidence / timestamp
    else new alert
        A->>DB: Create SecurityAlert with evidence snapshot
    end
    AN->>DB: Open alert, add AlertNote, assign owner
    AN->>DB: Change status OPEN → INVESTIGATING
```

Deduplication key: `(user_id, activity_id, status in open states)`. Re-scoring an activity strengthens the existing alert instead of flooding the queue.

---

## 4. Investigation workflow

```mermaid
stateDiagram-v2
    [*] --> OpenAlert
    OpenAlert --> CaseCreated: create_case_from_alert()
    CaseCreated --> EvidenceLinked: attach UserActivity records
    EvidenceLinked --> NotesAdded: InvestigationNote entries
    NotesAdded --> FindingsRecorded: analyst writes findings
    FindingsRecorded --> Resolved: conclusion + status RESOLVED
    Resolved --> Closed: report generated + status CLOSED
    FindingsRecorded --> FalsePositive: status FALSE_POSITIVE
    FalsePositive --> Closed
    Closed --> [*]
```

A case carries a UUID `case_id`, priority, assigned analyst, linked alert, evidence activities, findings, conclusion, and a chronological note stream.

---

## 5. Reporting and analytics

```mermaid
flowchart TB
    DB[(Live database)] --> SVC[apps/analytics/services.py]
    SVC --> D1[Activity trend]
    SVC --> D2[Risk mix]
    SVC --> D3[Severity mix]
    SVC --> D4[Activity breakdown]
    D1 & D2 & D3 & D4 --> JS[Chart.js dashboards]
    DB --> RB[apps/reports/pdf.py]
    RB --> PDF1[Alert report]
    RB --> PDF2[Risk assessment]
    RB --> PDF3[Activity history]
    RB --> PDF4[Investigation dossier]
    PDF1 & PDF2 & PDF3 & PDF4 --> GEN[GeneratedReport record]
    GEN --> DL[Authenticated PDF download]
```

No dashboard value is cached in source code. Every metric is derived from `UserActivity`, `DetectionResult`, `UserRiskProfile`, `SecurityAlert` and `InvestigationCase` at request time.

---

## Operational runbook

| Situation | Action |
| --- | --- |
| First setup | `python manage.py migrate` → `python -m ml.generate_dataset` → `python -m ml.train` → `python manage.py seed_synthetic_data --activities 600` |
| Refresh models | `python manage.py train_models --regenerate` then restart workers |
| Verify routes | `python scripts/smoke_check.py` |
| Verify code | `python manage.py check` and `python manage.py test` |
| Rotate demo password | `python manage.py seed_synthetic_data --activities 1000 --password "NewStrong!"` or change users in admin |
| Production | Follow [deployment.md](deployment.md) |
