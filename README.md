# SecureShare
SecureShare is a platform for secure file sharing with temporary access.

[Core Features]:

- Temporary File Sharing: Users can upload files and generate unique download links that expire after a specified time (e.g., 24 hours).

- Simple Full-Text Search: Users can search previously uploaded files in their personal account using keywords or file names.

- User Registration and Authentication: Simple sign-up with username/password authentication, plus optional two-factor authentication (2FA) for enhanced security.

- Custom Link Expiration: Users can set link expiration periods (e.g., 1, 3, 7 days, up to two weeks). After expiration, file access is disabled.

- Personal Dashboard: View uploaded files, track active links, and delete files as needed.

- Download Reports: Notifications showing when a file was downloaded, the originating IP address, and basic download statistics (e.g., total downloads).

[Killer Feature]:

- Automatic Cleanup of Inactive Links: After a link expires (based on time or a download limit set by the link creator), the system automatically deletes the file and notifies the user. Users are also proactively notified before the link expires, allowing them to extend its validity period if desired.

## Database migrations (Alembic)

Migrations are configured under `backend/alembic`. To create the SQLite DB and apply the initial schema:

```bash
cd backend
alembic upgrade head
```

To generate a new migration from model changes:
```bash
cd backend
alembic revision --autogenerate -m "your message"
alembic upgrade head
```

## Cleanup task tuning

Use env vars to control the cleanup loop:

- `CLEANUP_INTERVAL_SECONDS` (default: 300)
- `CLEANUP_MAX_RECORDS_PER_LOOP` (default: 200)
- `CLEANUP_RETRY_ATTEMPTS` (default: 3)
- `CLEANUP_RETRY_BACKOFF_SECS` (default: 0.5)

Metrics are logged as a one-line summary: `cleanup_summary files_deleted=... links_deactivated=... failed_minio=... duration=...`.


## Notes on Docker build TLS timeouts
If you hit `TLS handshake timeout` when pulling base images from Docker Hub, you can:
1) Use Google mirror (already applied in Dockerfiles):
   - `mirror.gcr.io/library/node:18-alpine`
   - `mirror.gcr.io/library/python:3.10-slim`
2) Or pre-pull images / configure registry mirrors in `/etc/docker/daemon.json`:
```json
{
  "registry-mirrors": ["https://mirror.gcr.io"],
  "dns": ["8.8.8.8","1.1.1.1"]
}
```
Then restart Docker.

## Hardening MinIO
Set non-default credentials in `docker-compose.yml`:
```yaml
minio:
  environment:
    - MINIO_ROOT_USER=secureshare
    - MINIO_ROOT_PASSWORD=<strong-password>
```
And in `.env` / backend settings:
```
MINIO_ACCESS_KEY=secureshare
MINIO_SECRET_KEY=<strong-password>
```
