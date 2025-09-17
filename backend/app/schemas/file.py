from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FileInfo(BaseModel):
    id: UUID
    filename: str
    content_type: str | None
    size: int
    created_at: datetime
    expires_at: datetime

    class Config:
        orm_mode = True

class UploadResponse(BaseModel):
    id: UUID
    filename: str
    content_type: str | None
    size: int
    created_at: datetime
    expires_at: datetime
    share_url: str | None = None
    token: str | None = None

class FileListResponse(BaseModel):
    files: list[FileInfo]
    total: int
    skip: int
    limit: int

class ShareResponse(BaseModel):
    share_url: str
    token: str
    expires_at: datetime