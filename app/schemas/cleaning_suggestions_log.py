from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class CleaningSuggestionsLogBase(BaseModel):
    action_type: str
    target_column: Optional[str] = None
    explanation: Optional[str] = None
    suggestion_status: Optional[str] = "SUGGESTED"

class CleaningSuggestionsLogCreate(CleaningSuggestionsLogBase):
    dataset_id: UUID

class CleaningSuggestionsLogUpdate(BaseModel):
    suggestion_status: str

class CleaningSuggestionsLogOut(CleaningSuggestionsLogBase):
    id: UUID
    dataset_id: UUID
    applied_at: datetime

    model_config = ConfigDict(from_attributes=True)
