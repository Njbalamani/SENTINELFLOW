# Deployment guide

## 1. Environment

Create `.env` from `.env.example` and set at minimum:

```dotenv
DJANGO_SECRET_KEY=<long-random-64-character-value>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.example,www.your-domain.example
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.example,https://www.your-domain.example
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_COOKIES=True
DJANGO_TRUST_X_FORWARDED_PROTO=True
DJANGO_HSTS_SECONDS=31536000
DJANGO_HSTS_INCLUDE_SUBDOMAINS=True
DJANGO_HSTS_PRELOAD=True
DB_ENGINE=django.db.backends.postgresql
DB_NAME=sentinelflow
DB_USER=sentinelflow
DB_PASSWORD=<strong-password>
DB_HOST=127.0.0.1
DB_PORT=5432
DB_SSLMODE=require
```

Create the PostgreSQL role and database:

```sql
CREATE USER sentinelflow WITH PASSWORD 'strong-password';
CREATE DATABASE sentinelflow OWNER sentinelflow;
GRANT ALL PRIVILEGES ON DATABASE sentinelflow TO sentinelflow;
```

Settings load `.env` automatically using `python-dotenv`; real environment variables take precedence. The application falls back to SQLite when `DB_ENGINE` is empty. This is intended only for local development and tests.

## 2. Install and initialise

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py check --deploy
python manage.py migrate
python -m ml.generate_dataset
python -m ml.train
python manage.py seed_synthetic_data --activities 600 --password "<unique-password>"
python manage.py collectstatic --noinput
```

Create the first real administrator with `python manage.py createsuperuser` and disable or rotate every seeded demo account. The seeder writes only synthetic records; never point it at production data.

## 3. Serve

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
```

WhiteNoise serves collected static files. Put TLS termination (nginx, a cloud load balancer, or equivalent) in front of Gunicorn and redirect all HTTP traffic to HTTPS.

Recommended nginx settings:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
client_max_body_size 10m;
```

## 4. Production security checklist

- `DJANGO_DEBUG=False`, unique `DJANGO_SECRET_KEY`, restrictive `DJANGO_ALLOWED_HOSTS`.
- Add your public domain to `DJANGO_CSRF_TRUSTED_ORIGINS` (include the `https://` scheme).
- Keep `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_COOKIES` and the HSTS flags enabled; `SECURE_CONTENT_TYPE_NOSNIFF` and `X_FRAME_OPTIONS=DENY` are always on.
- Only set `DJANGO_TRUST_X_FORWARDED_PROTO=True` when all traffic reaches Django through a trusted TLS proxy.
- Run the application under a dedicated OS user with read/write access only to `media/`, `logs/` and `ml/artifacts/`.
- Restrict access to `/admin/`, `/audit/`, and `/api/v1/` at the network or identity-aware proxy layer where possible.
- Rotate the seeded demo password immediately; enforce your organisation's password policy.
- Back up PostgreSQL plus `media/reports/` and `ml/artifacts/`.
- Review `logs/sentinelflow.log` and `AuditLog` records regularly.
- Ensure monitoring is authorised, transparent, and limited to synthetic or consented datasets.

## 5. Health and verification

```bash
curl https://your-domain.example/health/     # {"status":"ok","database":"ok"}
python manage.py test
python manage.py check --deploy
```

## 6. Updating the model

```bash
python manage.py train_models --regenerate
python manage.py sync_model_metadata
```

The prediction module caches loaded artifacts per process; restart Gunicorn workers after replacing model files so the new ensemble is used.
