from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class FileBase(BaseModel):
    filename: str
    content_type: str
    size: int

class FileCreate(FileBase):
    pass

class FileInfo(FileBase):
    id: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    download_url: str

    class Config:
        orm_mode = True

class UploadResponse(FileBase):
    id: str
    download_url: str
    expires_at: Optional[datetime] = None

class ShareResponse(BaseModel):
    share_url: str