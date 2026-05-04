from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel


class DetectionSuggestion(BaseModel):
    column: Optional[str] = None
    issue_type: str
    description: str
    suggested_action: str
    action_params: Optional[Dict[str, Any]] = None
    requires_user_approval: bool = True
    severity: Literal["low", "medium", "high"]
