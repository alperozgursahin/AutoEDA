from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class DatasetBase(BaseModel):
    original_filename: str
    file_path: Optional[str] = None
    cleaned_file_path: Optional[str] = None
    report_file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    status: Optional[str] = "UPLOADED"
    is_deleted: Optional[bool] = False

class DatasetCreate(DatasetBase):
    pass

class DatasetUpdate(BaseModel):
    status: Optional[str] = None
    is_deleted: Optional[bool] = None
    cleaned_file_path: Optional[str] = None
    report_file_path: Optional[str] = None

class DatasetOut(DatasetBase):
    id: UUID
    user_id: UUID
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)
