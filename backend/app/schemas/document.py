from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class DocumentBase(BaseModel):
    title: str
    category: str
    filename: Optional[str] = None
    meta_info: Optional[Dict[str, Any]] = {}


class DocumentCreate(DocumentBase):
    pass


class DocumentWorkflowRequest(BaseModel):
    approval_status: str
    notes: Optional[str] = None


class DocumentResponse(DocumentBase):
    id: int
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    chunk_count: int
    uploader_id: Optional[int] = None
    tenant_id: Optional[int] = 1
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
