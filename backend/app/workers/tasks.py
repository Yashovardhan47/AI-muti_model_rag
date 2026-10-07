from celery import Celery
from app.core.config import get_settings
from app.services.processing import process_file
from app.services.reconcile import reconcile

cfg = get_settings()
celery_app = Celery("document_intelligence", broker=cfg.redis_url or "redis://localhost:6379/0")
celery_app.conf.update(task_acks_late=True, worker_prefetch_multiplier=1)
celery_app.conf.beat_schedule = {"reconcile-source-index": {"task": "app.workers.tasks.reconcile_index", "schedule": 3600.0}}


@celery_app.task(bind=True, autoretry_for=(ConnectionError, TimeoutError), retry_backoff=True, retry_kwargs={"max_retries": 3})
def index_file(self, file_id: str, chunk_method: str = "document"):
    process_file(file_id, chunk_method)


@celery_app.task
def reconcile_index():
    result = reconcile()
    for file_id in result["queued_files"]:
        index_file.delay(file_id)
    return result
