# REST API reference

Base URL: `/api/v1/`. Interactive browsable API available at `/api-auth/login/`.

## Authentication

| Method | Use |
| --- | --- |
| Session | Log in via `/accounts/login/`, then send the CSRF token with state-changing requests |
| Token | `POST /api/v1/auth/token/` with username/password, then send `Authorization: Token <key>` |

All endpoints require authentication. `ADMIN`/`ANALYST` may write; `VIEWER` accounts receive read-only access. Subject-scoped querysets automatically restrict viewers to their own records.

## Endpoints

| Method | Path | Description | Roles |
| --- | --- | --- | --- |
| GET | `/activities/` | List activities. Filters: `activity_type`, `user`, `days`, `classification` via related queries | All |
| POST | `/activities/` | Ingest an activity and run ML detection | Admin, Analyst |
| GET | `/activities/{id}/` | Retrieve one activity | All |
| POST | `/activities/{id}/reanalyze/` | Re-run inference on an activity | Admin, Analyst |
| GET | `/detections/` | List detection results (`?classification=CRITICAL`) | All |
| GET | `/detections/{id}/` | Detection detail with reasons and feature vector | All |
| GET | `/risk-profiles/` | Ranked user risk profiles | All |
| GET | `/models/` | Trained model runs and metrics | All |
| GET | `/alerts/` | Alerts (`?severity=`, `?status=`) | All |
| POST | `/alerts/{id}/status/` | Update status: `{"status":"INVESTIGATING","notes":"..."}` | Admin, Analyst |
| POST | `/alerts/{id}/note/` | Add investigation note | Admin, Analyst |
| POST | `/alerts/{id}/investigate/` | Create or reuse an investigation case | Admin, Analyst |
| GET/POST | `/investigations/` | List or open cases | All / Admin+Analyst |
| POST | `/investigations/{id}/note/` | Add case note | Admin, Analyst |
| POST | `/investigations/{id}/close/` | Close case and resolve linked alert | Admin, Analyst |
| GET | `/analytics/summary/` | Live dashboard metrics (`?days=14`) | Admin, Analyst |
| GET | `/users/` | Provisioned user accounts | All |

List endpoints are paginated (25 results per page) and support `?page=`.

## Examples

```powershell
# 1. Obtain a token
curl -X POST http://127.0.0.1:8000/api/v1/auth/token/ `
  -H "Content-Type: application/json" `
  -d '{"username":"sentinel_analyst","password":"Sentinel@2026!"}'

# 2. Ingest a synthetic event
curl -X POST http://127.0.0.1:8000/api/v1/activities/ `
  -H "Authorization: Token <token>" -H "Content-Type: application/json" `
  -d '{"user":4,"activity_type":"DOWNLOAD","timestamp":"2026-11-23T21:15:00Z","bytes_transferred":524288000,"resource":"/shared/finance/export.csv","ip_address":"203.0.113.44"}'

# 3. Read live analytics
curl -H "Authorization: Token <token>" "http://127.0.0.1:8000/api/v1/analytics/summary/?days=30"

# 4. Triage an alert
curl -X POST http://127.0.0.1:8000/api/v1/alerts/1/status/ `
  -H "Authorization: Token <token>" -H "Content-Type: application/json" `
  -d '{"status":"INVESTIGATING","notes":"Reviewing proxy logs"}'
```

Successful ingestion returns the saved activity plus derived `classification` and `risk_score`.

## Validation and errors

| Status | Meaning |
| --- | --- |
| 400 | Field validation error (e.g. negative byte count, invalid status) |
| 403 | Unauthenticated or insufficient role |
| 404 | Unknown resource |
| 405 | Unsupported method |
| 429 | User throttle limit reached (1000/hour) |

Validation failures return field-level DRF error objects. All state-changing API calls are recorded in `AuditLog` by `AuditRequestMiddleware`, with sensitive fields redacted.
