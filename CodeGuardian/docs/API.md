# REST API

Base path: `/api/v1/`. All endpoints except token issuance require authentication by session or DRF token.

## Authentication

```http
POST /api/v1/auth/token/
Content-Type: application/json

{"username": "analyst", "password": "your-password"}
```

Use the returned token:

```http
Authorization: Token <token>
```

## Scans

```http
GET /api/v1/scans/
POST /api/v1/scans/
GET /api/v1/scans/{id}/
DELETE /api/v1/scans/{id}/
```

Create request uses `multipart/form-data`:

| Field | Required | Description |
|---|---|---|
| `name` | no | Display name; defaults to `API security scan` |
| `source_file` | yes | `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.java`, or `.zip` |

Create response includes status, score, files, findings, severity counts, and tool versions.

## Findings

```http
GET /api/v1/findings/
GET /api/v1/findings/?scan=<uuid>
GET /api/v1/findings/?severity=CRITICAL
```

## Files, reports, analytics

```http
GET /api/v1/files/
GET /api/v1/reports/
GET /api/v1/analytics/summary/
GET /api/v1/recommendations/
```

## Errors

| Status | Meaning |
|---:|---|
| 400 | Invalid upload, unsafe archive, or scanner failure |
| 401 | Missing or invalid credentials |
| 403 | Authenticated but not permitted |
| 404 | Object does not exist or is not visible to the user |
