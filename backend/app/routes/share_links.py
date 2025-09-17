
from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.file import File
from app.models.share_link import ShareLink
from app.schemas.file import ShareResponse
from app.utils.urls import build_external_url

router = APIRouter(prefix="/share-links", tags=["Share Links"])


@router.post("/create", response_model=ShareResponse)
async def create_share_link(
    request: Request,
    file_id: str = Query(..., description="ID of the file to share"),
    expire_days: int = Query(7, ge=1, le=365, description="Days until link expiration"),
    max_views: Optional[int] = Query(None, ge=1, description="Optional maximum number of downloads"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Validate file ownership
    res = await db.execute(select(File).where(File.id == file_id))
    file = res.scalars().first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    if file.owner_id != current_user.id and not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Access denied")

    # Create token and link
    token = secrets.token_urlsafe(24)
    link = ShareLink(
        file_id=str(file.id),
        token=token,
        expires_at=(datetime.utcnow() + timedelta(days=expire_days)),
        max_views=max_views or None,
        is_active=True,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)

    # Build URLs
    page_url = build_external_url(request, f"/s/{token}")
    # Direct stream url (sometimes handy)
    direct_url = build_external_url(request, f"/download/{token}")

    return ShareResponse(share_url=page_url, token=token, expires_at=link.expires_at)


@router.get("/{token}/meta")
async def get_share_meta(token: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ShareLink).where(ShareLink.token == token))
    link: Optional[ShareLink] = res.scalars().first()
    if not link or not link.is_active or (link.expires_at and link.expires_at <= datetime.utcnow()):
        raise HTTPException(status_code=404, detail="Share link not found")

    file = (await db.execute(select(File).where(File.id == link.file_id))).scalars().first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "filename": file.filename,
        "size": file.size,
        "content_type": file.content_type,
        "expires_at": link.expires_at,
        "views": link.views,
        "max_views": link.max_views,
    }


@router.post("/ensure", response_model=ShareResponse)
async def ensure_share_link(
    request: Request,
    file_id: str = Query(..., description="ID of the file"),
    expire_days: int = Query(7, ge=1, le=365),
    max_views: Optional[int] = Query(None, ge=1),
    reuse: bool = Query(True, description="If true, return an existing active link if found"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # ownership check
    res = await db.execute(select(File).where(File.id == file_id))
    file = res.scalars().first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    if file.owner_id != current_user.id and not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Access denied")

    now = datetime.utcnow()

    if reuse:
        # try to find active link
        res = await db.execute(
            select(ShareLink).where(
                ShareLink.file_id == file_id,
                ShareLink.is_active == True,  # noqa: E712
                (ShareLink.expires_at == None) | (ShareLink.expires_at > now),  # noqa: E711
            )
        )
        existing = res.scalars().first()
        if existing:
            page_url = build_external_url(request, f"/s/{existing.token}")
            return ShareResponse(share_url=page_url, token=existing.token, expires_at=existing.expires_at)

    # else create
    token = secrets.token_urlsafe(24)
    link = ShareLink(
        file_id=str(file.id),
        token=token,
        expires_at=(datetime.utcnow() + timedelta(days=expire_days)),
        max_views=max_views or None,
        is_active=True,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)

    page_url = build_external_url(request, f"/s/{token}")
    return ShareResponse(share_url=page_url, token=token, expires_at=link.expires_at)
