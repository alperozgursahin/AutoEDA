from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any

class ProfilingResultBase(BaseModel):
    pre_cleaning_score: Optional[float] = None
    post_cleaning_score: Optional[float] = None
    dataset_statistics: Optional[Dict[str, Any]] = None
    column_statistics: Optional[Dict[str, Any]] = None
    detected_issues: Optional[Dict[str, Any]] = None

class ProfilingResultCreate(ProfilingResultBase):
    dataset_id: UUID

class ProfilingResultUpdate(BaseModel):
    post_cleaning_score: Optional[float] = None
    dataset_statistics: Optional[Dict[str, Any]] = None
    column_statistics: Optional[Dict[str, Any]] = None
    detected_issues: Optional[Dict[str, Any]] = None

class ProfilingResultOut(ProfilingResultBase):
    id: UUID
    dataset_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
