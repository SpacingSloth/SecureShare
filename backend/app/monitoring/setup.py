import logging
import time

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

cleanup_runs = Counter("cleanup_runs_total", "Cleanup loop runs")
cleanup_files_deleted = Counter("cleanup_files_deleted_total", "Files deleted by cleanup")
cleanup_links_deactivated = Counter("cleanup_links_deactivated_total", "Share links deactivated by cleanup")
cleanup_failed_deletes = Counter("cleanup_failed_deletes_total", "Failed MinIO deletes in cleanup")
cleanup_duration = Histogram("cleanup_duration_seconds", "Duration of a cleanup run in seconds")

def report_cleanup(files_deleted: int, links_deactivated: int, failed: int, duration: float) -> None:
    """Record cleanup metrics to Prometheus."""
    cleanup_runs.inc()
    if files_deleted:
        cleanup_files_deleted.inc(files_deleted)
    if links_deactivated:
        cleanup_links_deactivated.inc(links_deactivated)
    if failed:
        cleanup_failed_deletes.inc(failed)
    cleanup_duration.observe(duration)

def setup_monitoring(app: ASGIApp):
    Instrumentator().instrument(app).expose(app, endpoint="/api/metrics", include_in_schema=False)

    @app.middleware("http")
    async def monitor_requests(request: Request, call_next):
        start_time = time.time()
        try:
            response = await call_next(request)
        except HTTPException as e:
            logger.exception("HTTP exception: %s %s -> %s", request.method, request.url.path, e.detail)
            response = JSONResponse(status_code=e.status_code, content={"detail": e.detail})
        except Exception as e:
            logger.exception("Unhandled error: %s %s -> %s", request.method, request.url.path, e)
            response = JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
        finally:
            process_time = time.time() - start_time
            logger.info("method=%s path=%s status=%s duration=%.4fs",
                        getattr(request, "method", "?"), getattr(request, "url", "?").path,
                        getattr(response, "status_code", "?"), process_time)
        return response