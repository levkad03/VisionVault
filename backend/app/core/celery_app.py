from celery import Celery

from app.core.config import settings

# Register all ORM models on Base.metadata before any task runs. The worker
# process only imports app.processing.tasks (below), which pulls in
# app.images.models but never app.auth.models -- without this, resolving the
# Image.owner_id -> user.id foreign key fails because SQLAlchemy never saw
# the User table get defined in this process.
from app.auth import models as _auth_models  # noqa: E402,F401
from app.images import models as _images_models  # noqa: E402,F401

celery_app = Celery(
    "visionvault",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.processing.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
