from __future__ import annotations

import html
import math
import urllib.parse
from collections.abc import AsyncIterator
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.database import get_db
from app.core.minio_client import minio_client
from app.models.file import File
from app.models.share_link import ShareLink
from app.utils.urls import build_external_url

router = APIRouter(tags=["Download"])


def _rfc5987_filename(value: str) -> str:
    quoted = urllib.parse.quote(value, safe="")
    latin1_fallback = value.encode("latin-1", "ignore").decode("latin-1")
    return f'filename="{latin1_fallback}"; filename*=UTF-8\'\'{quoted}'


def _human_size(n: int | None) -> str:
    if n is None:
        return "unknown"
    units = ["B", "KB", "MB", "GB", "TB"]
    if n == 0:
        return "0 B"
    p = min(int(math.log(n, 1024)), len(units) - 1)
    return f"{n / (1024 ** p):.2f} {units[p]}"


async def _aiter_minio(obj) -> AsyncIterator[bytes]:
    try:
        while True:
            chunk = await run_in_threadpool(obj.read, 1024 * 1024)  
            if not chunk:
                break
            yield chunk
    finally:
        await run_in_threadpool(obj.close)


def _render_error_page(title: str, message: str, status_code: int = 404) -> HTMLResponse:
    esc = lambda s: html.escape(s or "", quote=True)
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{esc(title)}</title>
  <style>
    :root{{ --bg:#0b1016; --card:#111827; --fg:#e5eef7; --muted:#8ea3b7; }}
    html,body{{ height:100%; }}
    body{{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.45 system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif; }}
    .wrap{{ min-height:100%; display:grid; place-items:center; padding:24px; }}
    .card{{ background:var(--card); padding:28px; max-width:640px; border-radius:16px; box-shadow:0 10px 30px rgba(0,0,0,.35); }}
    .title{{ margin:0 0 8px 0; font-size:22px; }}
    .muted{{ color:var(--muted); margin:0; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1 class="title">{esc(title)}</h1>
      <p class="muted">{esc(message)}</p>
    </div>
  </div>
</body>
</html>"""
    return HTMLResponse(content=page, status_code=status_code, headers={"Cache-Control": "no-store"})



@router.get("/s/{token}", response_class=HTMLResponse)
async def share_landing(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Public landing page for a share token that auto-triggers the browser download.
    Shows basic metadata and provides a big 'Download' button as fallback.
    """
    now = datetime.utcnow()

    res = await db.execute(select(ShareLink).where(ShareLink.token == token))
    link: ShareLink | None = res.scalars().first()

    if not link or not link.is_active or (link.expires_at and link.expires_at <= now):
        return _render_error_page("Share link not found", "The link is invalid or has expired.", 404)

    res = await db.execute(select(File).where(File.id == link.file_id))
    file: File | None = res.scalars().first()

    if not file:
        link.is_active = False
        await db.commit()
        return _render_error_page("File not found", "The file has been removed or is no longer available.", 404)

    direct_url = build_external_url(request, f"/download/{token}")
    filename = file.filename or "download.bin"
    safe_filename = html.escape(filename, quote=True)

    html_page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Downloading {safe_filename}</title>
  <style>
    :root {{ --bg:#0b0d10; --card:#151a20; --fg:#e7edf3; --muted:#9fb0c3; }}
    html,body {{ height:100%; }}
    body {{ margin:0; background:var(--bg); color:var(--fg); font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji"; }}
    .wrap {{ max-width:720px; margin:0 auto; padding:40px 20px; }}
    .card {{ background:var(--card); border-radius:20px; padding:28px; box-shadow: 0 10px 30px rgba(0,0,0,.25); }}
    h1 {{ font-size:22px; margin:0 0 12px; }}
    p {{ margin: 6px 0; color:var(--muted); }}
    .row {{ display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-top:20px; }}
    .btn {{ text-decoration:none; display:inline-block; padding:12px 18px; border-radius:12px; background:#2a7cff; color:white; font-weight:600; border:0; cursor:pointer; }}
    .btn.secondary {{ background:#2b3340; color:#d7e1ea; }}
    .meta {{ margin-top:10px; font-size:14px; }}
    .hidden {{ display:none; }}
    code {{ background:#0f1318; padding:2px 6px; border-radius:6px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Preparing download…</h1>
      <p><strong>{safe_filename}</strong></p>
      <p class="meta">Size: {_human_size(file.size)}{(' · expires: ' + link.expires_at.isoformat()) if link.expires_at else ''}</p>

      <div class="row">
        <a id="dl" class="btn" href="{direct_url}" download="{safe_filename}">Download</a>
        <button class="btn secondary" id="copy">Copy link</button>
      </div>

      <p class="meta" id="status">The download should start automatically. If it doesn’t, click <strong>Download</strong>.</p>

      <input id="hidden" class="hidden" value="{direct_url}" readonly/>
    </div>
  </div>

  <script>
    // Auto-trigger the browser's download using the anchor
    const a = document.getElementById('dl');
    setTimeout(() => a.click(), 250);

    // Copy link
    document.getElementById('copy').addEventListener('click', async () => {{
      const url = document.getElementById('hidden').value;
      try {{
        await navigator.clipboard.writeText(url);
        document.getElementById('status').textContent = 'Link copied to clipboard.';
      }} catch (e) {{
        // Fallback: show the input so the user can copy manually
        document.getElementById('hidden').classList.remove('hidden');
        document.getElementById('hidden').select();
        document.getElementById('status').textContent = 'Press Ctrl+C to copy the link below.';
      }}
    }});
  </script>
</body>
</html>"""
    return HTMLResponse(html_page, headers={"Cache-Control": "no-store"})


@router.get("/download/{token}")
async def download_by_token(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()

    res = await db.execute(select(ShareLink).where(ShareLink.token == token))
    link: ShareLink | None = res.scalars().first()

    if not link or not link.is_active or (link.expires_at and link.expires_at <= now):
        raise HTTPException(status_code=404, detail="File not found")

    res = await db.execute(select(File).where(File.id == link.file_id))
    file: File | None = res.scalars().first()
    if not file:
        link.is_active = False
        await db.commit()
        raise HTTPException(status_code=404, detail="File not found")

    link.views = (link.views or 0) + 1
    if link.max_views and link.views >= link.max_views:
        link.is_active = False
    await db.commit()

    try:
        stat = await run_in_threadpool(minio_client.stat_object, file.bucket, file.object_name)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found in storage")

    try:
        obj = await run_in_threadpool(minio_client.get_object, file.bucket, file.object_name)
    except Exception:
        raise HTTPException(status_code=500, detail="Storage is temporarily unavailable")

    override = request.query_params.get("filename")
    effective_name = override or file.filename or "download.bin"
    content_disposition = f'attachment; {_rfc5987_filename(effective_name)}'

    headers = {
        "Content-Disposition": content_disposition,
        "Content-Length": str(getattr(stat, "size", "") or ""),
        "Cache-Control": "no-store",
    }

    media_type = file.content_type or getattr(stat, "content_type", None) or "application/octet-stream"

    return StreamingResponse(
        _aiter_minio(obj),
        media_type=media_type,
        headers=headers,
    )
