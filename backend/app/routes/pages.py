from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(tags=["Pages"])

BASE_STYLE = """
:root{color-scheme:light dark}
body{margin:0;font-family:system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, "Helvetica Neue", Arial, "Apple Color Emoji","Segoe UI Emoji";line-height:1.5}
header{position:sticky;top:0;background:Canvas;padding:.75rem 1rem;border-bottom:1px solid color-mix(in oklab, Canvas, CanvasText 12%)}
main{max-width:1100px;margin:0 auto;padding:1rem}
article{padding:1rem;border:1px solid color-mix(in oklab, Canvas, CanvasText 12%);border-radius:12px;margin:1rem 0;background:Canvas}
h1,h2,h3{line-height:1.2}
.page-meta{font:12px/1.4 ui-monospace;color:color-mix(in oklab, CanvasText, Canvas 35%)}
.search-hint{font-size:12px;color:color-mix(in oklab, CanvasText, Canvas 40%)}
a{color:LinkText;text-decoration:underline;text-underline-offset:2px}
"""
CSP = "default-src 'none'; img-src 'self' data: blob:; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"

@router.get("/pages/{page_id}", response_class=HTMLResponse)
async def view_page(page_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.execute(text("""
        SELECT wp.id, wp.title, f.filename, wpf.safe_html
        FROM web_pages wp
        JOIN files f ON f.id = wp.file_id
        JOIN web_page_fts wpf ON wpf.page_id = wp.id
        WHERE wp.id = :pid
    """), {"pid": page_id})
    r = row.first()
    if not r:
        raise HTTPException(status_code=404, detail="Page not found")
    title = r.title or r.filename or "Page"
    safe_html = r.safe_html or "<p>(Empty)</p>"
    html = f"""<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8"/>
<title>{title}</title>
<meta http-equiv="Content-Security-Policy" content="{CSP}"/>
<style>{BASE_STYLE}</style>
</head>
<body>
<header>
  <strong>{title}</strong>
  <div class="search-hint">Нажмите Ctrl/⌘+F для поиска по этой странице</div>
</header>
<main>
  <article>{safe_html}</article>
</main>
</body>
</html>"""
    return HTMLResponse(html, headers={"Content-Security-Policy": CSP})

@router.get("/pages/search", response_class=HTMLResponse)
async def search_pages(q: str = Query("", description="Запрос, можно пустой для всех страниц"),
                       limit: int = 20, db: AsyncSession = Depends(get_db)):
    if q:
        sql = text("""
            SELECT wp.id, wp.title, f.filename
            FROM web_page_fts w
            JOIN web_pages wp ON wp.id = w.page_id
            JOIN files f ON f.id = wp.file_id
            WHERE w.body MATCH :q OR w.title MATCH :q
            LIMIT :limit
        """)
        rows = (await db.execute(sql, {"q": q, "limit": limit})).all()
    else:
        sql = text("""
            SELECT wp.id, wp.title, f.filename
            FROM web_pages wp
            JOIN files f ON f.id = wp.file_id
            ORDER BY wp.created_at DESC
            LIMIT :limit
        """)
        rows = (await db.execute(sql, {"limit": limit})).all()

    ids = [r.id for r in rows] if rows else []
    safe_html_map = {}
    if ids:
        placeholders = ",".join([f":p{i}" for i in range(len(ids))])
        params = {f"p{i}": ids[i] for i in range(len(ids))}
        wsql = text(f"SELECT page_id, safe_html FROM web_page_fts WHERE page_id IN ({placeholders})")
        for rec in (await db.execute(wsql, params)).all():
            safe_html_map[rec.page_id] = rec.safe_html

    items = []
    for r in rows:
        title = r.title or r.filename or r.id
        anchor = f"p-{r.id}"
        body = safe_html_map.get(r.id, "<p>(Empty)</p>")
        items.append(f'<h2 id="{anchor}">{title}</h2><article>{body}</article>')

    hint = "Нажмите Ctrl/⌘+F для полнотекстового поиска прямо на этой странице."
    listing = "\n".join(items) if items else "<p>Ничего не найдено.</p>"

    html = f"""<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8"/>
<title>Поиск по страницам</title>
<meta http-equiv="Content-Security-Policy" content="{CSP}"/>
<style>{BASE_STYLE}</style>
</head>
<body>
<header>
  <strong>Поиск по страницам</strong>
  <div class="page-meta">Запрос: {q!s}</div>
  <div class="search-hint">{hint}</div>
</header>
<main>
  {listing}
</main>
</body>
</html>"""
    return HTMLResponse(html, headers={"Content-Security-Policy": CSP})
