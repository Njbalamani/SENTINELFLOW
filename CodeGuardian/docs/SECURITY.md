# Security model

## Upload handling

- Allowed source extensions: `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.java`, and `.zip`.
- Single file limit defaults to 10 MB; ZIP limit to 25 MB; uncompressed ZIP content to 100 MB.
- ZIP members are normalised, constrained to the scan directory, and checked for symlink bits and encryption flags.
- Relative paths, absolute paths, Windows drive paths, and null bytes are rejected.
- Uploaded code is treated as inert text and is never executed.

## Access control

- Scans, findings, analysed files, and reports are scoped to the owner.
- Superusers can view all resources through the web and API.
- Object-level DRF permission `IsOwnerOrAdmin` and Django mixin `OwnerRequiredMixin` enforce ownership.
- Admin routes remain available to staff users only.

## Application hardening

- CSRF protection on all state-changing browser requests.
- Secure cookies, HSTS, content-type sniffing protection, and `X-Frame-Options: DENY`.
- Password validators and Django's adaptive password hashing.
- Audit log entries for registration, profile updates, scan creation, report generation, and denial events.

## AI boundary

When enabled, Gemini receives finding metadata only. It cannot create, delete, or alter finding counts, severities, file paths, or scores. If AI is unavailable or disabled, deterministic rule-based explanations are used.

## Deployment checklist

- Set `DJANGO_DEBUG=false`.
- Use a unique, high-entropy `DJANGO_SECRET_KEY`.
- Configure `DJANGO_ALLOWED_HOSTS` and trusted origins.
- Enable HTTPS and secure cookies.
- Use PostgreSQL with TLS and least-privilege credentials.
- Store media with restrictive permissions and a retention policy.
- Keep Semgrep and Bandit versions pinned in deployment images.
