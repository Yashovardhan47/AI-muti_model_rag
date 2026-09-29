from celery import Celery
from app.core.config import get_settings
from app.services.processing import process_file

cfg = get_settings()
celery_app = Celery("document_intelligence", broker=cfg.redis_url or "redis://localhost:6379/0")
celery_app.conf.update(task_acks_late=True, worker_prefetch_multiplier=1)


@celery_app.task(bind=True, autoretry_for=(ConnectionError, TimeoutError), retry_backoff=True, retry_kwargs={"max_retries": 3})
def index_file(self, file_id: str, chunk_method: str = "document"):
    process_file(file_id, chunk_method)
