from __future__ import annotations

import logging
import os
import secrets
import tempfile
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.minio_client import minio_client
from app.core.security import get_current_user
from app.dependencies.auth import get_current_user
from app.models.file import File
from app.models.share_link import ShareLink
from app.schemas.file import FileInfo, FileListResponse, UploadResponse
from app.services.index_html import index_html_if_applicable
from app.utils.urls import build_external_url

logger = logging.getLogger("secure-share")

router = APIRouter(tags=["Files"])

def _mojibake(s: str) -> str | None:
    try:
        b = s.encode("utf-8", errors="ignore")
        m = b.decode("latin1", errors="ignore")
        return m if m and m != s else None
    except Exception:
        return None

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    request: Request,
    file: UploadFile,
    expire_days: int = Query(7, ge=1, le=365),
    create_share: bool = Query(False, description="Return share_url/token in UploadResponse"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    suffix = "_" + file.filename if file.filename else ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            tmp.write(chunk)
        temp_path = tmp.name

    file_size = os.path.getsize(temp_path)
    content_type = file.content_type or "application/octet-stream"

    bucket = settings.MINIO_BUCKET
    object_name = f"{uuid.uuid4()}_{file.filename or 'file.bin'}"

    try:
        minio_client.fput_object(bucket, object_name, temp_path, content_type=content_type)
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass

    f = File(
        id=str(uuid.uuid4()),
        filename=file.filename or object_name,
        content_type=content_type,
        size=file_size,
        owner_id=str(current_user.id) if hasattr(current_user, "id") else current_user["id"],
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=expire_days),
        bucket=bucket,
        object_name=object_name,
    )
    db.add(f)
    await db.commit()
    await db.refresh(f)

    try:
        page = await index_html_if_applicable(db, f)
        if page:
            await db.commit()
    except Exception as e:
        logger.exception("HTML indexing failed for file %s: %s", f.id, e)
    
    resp = UploadResponse(
        id=f.id, filename=f.filename, content_type=f.content_type, size=f.size, created_at=f.created_at, expires_at=f.expires_at
    )

    if create_share:
        s = ShareLink(
            id=str(uuid.uuid4()),
            file_id=f.id,
            token=secrets.token_urlsafe(24),
            created_at=datetime.utcnow(),
            expires_at=f.expires_at,
            max_views=None,
            views=0,
            is_active=True,
        )
        db.add(s)
        await db.commit()
        share_url = build_external_url(request, f"/download/{s.token}")
        resp.share_url = share_url
        resp.token = s.token

    return resp


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await db.execute(select(File).where(File.id == file_id))
    file_obj = res.scalars().first()
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")
    owner_id = getattr(current_user, "id", None)
    is_admin = bool(getattr(current_user, "is_admin", False))
    if str(file_obj.owner_id) != str(owner_id) and not is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        if file_obj.bucket and file_obj.object_name:
            minio_client.remove_object(file_obj.bucket, file_obj.object_name)
    except Exception:
        logging.exception("MinIO remove_object failed for %s/%s", file_obj.bucket, file_obj.object_name)

    await db.delete(file_obj)
    await db.commit()
    return {"status": "ok", "id": file_id}


@router.get("/files", response_model=FileListResponse)
async def list_files(
    request: Request,
    search: str | None = Query(None, description="Search by filename"),
    file_type: str | None = Query(None, description="Filter by extension (e.g., 'pdf')"),
    start_date: str | None = Query(None, description="Filter by created_at >= YYYY-MM-DD"),
    end_date: str | None = Query(None, description="Filter by created_at <= YYYY-MM-DD"),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conditions = [File.owner_id == (str(current_user.id) if hasattr(current_user, "id") else current_user["id"])]
    if search and search.strip():
        needle = search.strip()
        mb = _mojibake(needle)
        like_exprs = [File.filename.ilike(f"%{needle}%")]
        if mb:
            like_exprs.append(File.filename.ilike(f"%{mb}%"))
        conditions.append(or_(*like_exprs))

    if file_type:
        ext = file_type.lower().lstrip(".")
        conditions.append(File.filename.ilike(f"%.{ext}"))

    def _parse_date(s: str, end=False) -> datetime | None:
        try:
            s2 = (s or "").strip()
            if not s2:
                return None
            dt = datetime.fromisoformat(s2)
            if end and len(s2) == 10:
                return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            return dt
        except Exception:
            return None

    if start_date:
        sd = _parse_date(start_date)
        if sd:
            conditions.append(File.created_at >= sd)
    if end_date:
        ed = _parse_date(end_date, end=True)
        if ed:
            conditions.append(File.created_at <= ed)

    where_clause = and_(*conditions) if conditions else None

    count_stmt = select(func.count()).select_from(File)
    if where_clause is not None:
        count_stmt = count_stmt.where(where_clause)
    total = (await db.execute(count_stmt)).scalar_one()

    query = select(File)
    if where_clause is not None:
        query = query.where(where_clause)

    allowed = {
        "created_at": File.created_at,
        "filename": File.filename,
        "size": File.size,
    }
    col = allowed.get(sort_by, File.created_at)
    query = query.order_by(col.asc() if order.lower() == "asc" else col.desc())

    query = query.offset(skip).limit(limit)

    rows = (await db.execute(query)).scalars().all()
    files = [FileInfo.from_orm(r) for r in rows]
    return FileListResponse(files=files, total=total, skip=skip, limit=limit)