from datetime import timedelta
from io import BytesIO

from minio import Minio
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

_client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_use_ssl,
)


async def ensure_bucket_exists() -> None:
    exists = await run_in_threadpool(_client.bucket_exists, settings.minio_bucket_name)
    if not exists:
        await run_in_threadpool(_client.make_bucket, settings.minio_bucket_name)


async def upload_bytes(object_name: str, data: bytes, content_type: str) -> None:
    await run_in_threadpool(
        _client.put_object,
        settings.minio_bucket_name,
        object_name,
        BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


async def delete_object(object_name: str) -> None:
    await run_in_threadpool(
        _client.remove_object, settings.minio_bucket_name, object_name
    )


async def get_presigned_url(
    object_name: str, expires: timedelta = timedelta(hours=1)
) -> str:
    return await run_in_threadpool(
        _client.presigned_get_object, settings.minio_bucket_name, object_name, expires
    )


async def download_bytes(object_name: str) -> bytes:
    response = await run_in_threadpool(
        _client.get_object, settings.minio_bucket_name, object_name
    )
    try:
        return await run_in_threadpool(response.read)
    finally:
        await run_in_threadpool(response.close)
        await run_in_threadpool(response.release_conn)
