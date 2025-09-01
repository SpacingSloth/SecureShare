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
    # Без download_url

class UploadResponse(BaseModel):
    id: UUID
    filename: str
    content_type: str | None
    size: int
    expires_at: datetime
    # Без download_url

class ShareResponse(BaseModel):
    share_url: str
    token: str
    expires_at: datetime
