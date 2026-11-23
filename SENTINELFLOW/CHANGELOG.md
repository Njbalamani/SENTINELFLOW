# Changelog

All notable changes to SENTINELFLOW are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

**Repository snapshot date: 23/11/2026**

## [1.1.0] — 2026-11-23

### Added
- Automatic `.env` loading via `python-dotenv`; real environment variables still take precedence.
- Environment-driven production security controls: HTTPS redirect, secure session/CSRF cookies, HSTS, trusted CSRF origins, trusted-proxy header handling, SameSite and referrer policies.
- Anonymous API throttling (20/hour) alongside the existing authenticated limit (1000/hour).
- Token endpoint at `POST /api/v1/auth/token/` and matching API documentation/test coverage.
- Application version constant and version display in the sidebar footer.
- `scripts/smoke_check.py` for end-to-end route verification against a seeded database.
- Architecture, ER diagram, API and deployment documentation.
- This changelog.

### Fixed
- `/audit/` route previously resolved to `/audit/audit/`; it now resolves correctly.
- `ModelRunSerializer` crashed with a string `read_only_fields` value; fields are now explicitly declared.
- Audit trail template crashed when an audit record had no actor; system actors now render as `system`.
- API ingestion response now includes `classification` and `risk_score`.
- Pandas feature names are preserved through scaling, removing scikit-learn feature-name warnings.
- Password validator setting corrected to `NumericPasswordValidator`.
- ML ensemble test now skips unless both joblib model files and metadata exist, so a fresh clone without artifacts passes cleanly.

## [1.0.0] — 2026-11-23

### Added
- Initial full-stack Django application: custom user/roles, activity monitoring, hybrid ML detection, risk profiles, alerts, investigations, live analytics, PDF reports, audit logging, REST API, custom UI, synthetic data tooling, and 40 automated tests.
