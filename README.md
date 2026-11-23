<div align="center">

# SENTINELFLOW

### AI-Powered Insider Threat Detection System

**Repository snapshot · 23/11/2026 · Version 1.1.0**

[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)](SENTINELFLOW/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776ab?logo=python&logoColor=white)](SENTINELFLOW/requirements.txt)
[![Django](https://img.shields.io/badge/Django-6.x-092e20?logo=django&logoColor=white)](SENTINELFLOW/README.md)
[![Tests](https://img.shields.io/badge/Tests-41%20passing-2ea44f)](SENTINELFLOW/README.md#testing-and-verification)

</div>

---

## Repository layout

```text
SENTINELFLOW/                 ← complete Django application (open this folder)
├── README.md                 ← full overview, diagrams, quick start
├── LICENSE                   ← MIT License
├── CHANGELOG.md              ← version history
├── apps/                     ← accounts, core, monitoring, detection, alerts, investigation, analytics, reports
├── config/                   ← settings, URLs, WSGI/ASGI
├── data/                     ← synthetic CSV datasets
├── docs/                     ← architecture, ERD, workflow, structure, API, deployment
├── ml/                       ← feature contract, trainer, inference engine
├── scripts/                  ← smoke-check utility
├── static/                   ← custom CSS and JavaScript
└── templates/                ← reusable Django templates
```

## Start here

- **[Project README](SENTINELFLOW/README.md)** — features, architecture diagram, workflow diagrams, ER overview, structure tree, quick start and demo accounts.
- **[Architecture](SENTINELFLOW/docs/architecture.md)** — layered system design and request flow.
- **[Workflow](SENTINELFLOW/docs/workflow.md)** — ingestion → detection → alert → investigation → report.
- **[ER diagram](SENTINELFLOW/docs/er_diagram.md)** — database relationships.
- **[Structure](SENTINELFLOW/docs/structure.md)** — module responsibility matrix.
- **[API reference](SENTINELFLOW/docs/api.md)** — REST endpoints and examples.
- **[Deployment](SENTINELFLOW/docs/deployment.md)** — production setup.

## Verified snapshot

| Check | Result |
| --- | --- |
| `python manage.py check` | No issues |
| `python manage.py test` | 41 tests OK (1 skipped until models are trained) |
| `python scripts/smoke_check.py` | All routes 200 |
| Snapshot date | **23/11/2026** |

> Ethical use: this project contains synthetic data only and must never be used for covert employee monitoring.

MIT licensed — see [SENTINELFLOW/LICENSE](SENTINELFLOW/LICENSE).
