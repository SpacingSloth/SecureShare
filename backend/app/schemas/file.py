from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class FileInfo(BaseModel):
    id: UUID
    filename: str
    content_type: str | None
    size: int
    created_at: datetime
    expires_at: datetime

class UploadResponse(BaseModel):
    id: UUID
    filename: str
    content_type: str | None
    size: int
    expires_at: datetime
    share_url: Optional[str] = None
    token: Optional[str] = None

class FileListResponse(BaseModel):
    files: List[FileInfo]
    total: int
    skip: int
    limit: int

class ShareResponse(BaseModel):
    share_url: str
    token: str
    expires_at: datetime
