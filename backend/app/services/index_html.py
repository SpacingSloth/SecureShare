from __future__ import annotations

import logging

import bleach
from bs4 import BeautifulSoup
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.minio_client import minio_client
from app.models.file import File
from app.models.web_page import WebPage

logger = logging.getLogger("secure-share")

ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union({
    "p","div","span","br","hr","pre","code",
    "h1","h2","h3","h4","h5","h6",
    "ul","ol","li","strong","em","blockquote","cite",
    "table","thead","tbody","tr","th","td",
    "img","a"
})
ALLOWED_ATTRS = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "a": ["href","title","name","id","target","rel"],
    "img": ["src","alt","title","width","height"]
}

def _extract_text_and_title(html_bytes: bytes, fallback_title: str) -> tuple[str, str, str]:
    try:
        raw = html_bytes.decode("utf-8", errors="ignore")
    except Exception:
        raw = html_bytes.decode("latin-1", errors="ignore")
    soup = BeautifulSoup(raw, "html.parser")
    title = (soup.title.string.strip() if soup.title and soup.title.string else fallback_title) or fallback_title
    for s in soup(["script","style","noscript"]):
        s.decompose()
    text_body = soup.get_text(" ", strip=True)
    safe_html = bleach.clean(str(soup.body or soup), tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
    return title, text_body, safe_html

async def index_html_if_applicable(db: AsyncSession, file_obj: File) -> WebPage | None:
    name = (file_obj.filename or "").lower()
    ctype = (file_obj.content_type or "").lower()
    if not (name.endswith(".html") or name.endswith(".htm") or "text/html" in ctype):
        return None

    obj = minio_client.get_object(file_obj.bucket, file_obj.object_name)
    try:
        data = obj.read()
    finally:
        obj.close(); obj.release_conn()

    title, body_text, safe_html = _extract_text_and_title(data, file_obj.filename)

    existing = await db.execute(select(WebPage).where(WebPage.file_id == str(file_obj.id)))
    row = existing.scalars().first()
    if row is None:
        row = WebPage(file_id=str(file_obj.id), title=title)
        db.add(row)
        await db.flush()
    else:
        row.title = title

    await db.execute(text("DELETE FROM web_page_fts WHERE page_id = :pid"), {"pid": row.id})
    await db.execute(
        text("INSERT INTO web_page_fts(page_id, title, body, safe_html) VALUES (:pid, :title, :body, :safe_html)"),
        {"pid": row.id, "title": title, "body": body_text, "safe_html": safe_html}
    )
    logger.info("Indexed HTML page %s (%s)", row.id, file_obj.filename)
    return row
