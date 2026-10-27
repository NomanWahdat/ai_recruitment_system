# Deployment and operations

Use Python requirements with requirements.lock.txt constraints and frontend/package-lock.json. The Python constraints were resolved/tested on Windows/Python 3.12; Linux CI/container results must be verified separately. Setup runs committed migrations rather than generating them.

## Local Compose

~~~sh
docker compose up --build
docker compose exec api python manage.py seed_demo
~~~

Services: PostgreSQL, one-shot migration, API, separate worker and frontend. This is a local demo configuration with published demo credentials. Docker was unavailable in the implementation environment: container definitions were reviewed, not built there.

## Production

Set DJANGO_SETTINGS_MODULE=config.settings.production, a random SECRET_KEY of at least 50 characters, DATABASE_URL, and real ALLOWED_HOSTS. Configure explicit CORS/CSRF origins and a trusted TLS proxy that sanitizes forwarded headers. Keep secure cookies and HTTPS redirects enabled.

Build the frontend with NEXT_PUBLIC_API_BASE_URL. Frontend/API must be same-site for the default SameSite=Lax session policy.

Mount a private persistent media volume shared by web and worker. Run collectstatic and migrations before release. WhiteNoise uses STORAGES. Supervise python manage.py process_tasks separately. Configure shared-cache throttles, request/body limits, worker resource limits, logging, coordinated backups and restoration tests.

Never seed the published demo account in production; the command rejects production settings.

~~~sh
python manage.py check --deploy --settings=config.settings.production
python manage.py makemigrations --check --dry-run
~~~

/api/health/ checks the database. Dashboard worker status uses heartbeat timestamps.

## Recovery and retention

SIGTERM/SIGINT let active work finish. A hard kill leaves a ten-minute lease; three exhausted claims fail. Ordinary processing errors need explicit retry. Large job pools can exceed a lease; split workloads or add renewal before scaling. Exactly-once external calls are not claimed.

Schedule purge_expired --apply after reviewing its dry run and retention policy. reconcile_storage previews unreferenced CV files older than 24 hours; only --apply deletes them. Use a maintenance window, coordinate database/media backups, and verify restoration. File writes cannot be made atomic with database commits.

## CI

.github/workflows/ci.yml defines PostgreSQL tests/coverage, migrations/config checks, evaluation, frontend lint/typecheck/build, and browser verification. A definition is not proof of a remote GitHub Actions run; verify that after publishing the branch.
