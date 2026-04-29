from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import List

from app.worker.tasks import execute_cleaning_task

router = APIRouter()

class ActionItem(BaseModel):
    action: str
    column: str

class ExecuteRequest(BaseModel):
    input_file_path: str
    approved_actions: List[ActionItem]

@router.post("/{dataset_id}/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_cleaning(dataset_id: int, payload: ExecuteRequest):
    """
    Triggers the asynchronous data cleaning process based on approved actions.
    """
    # Trigger the Celery task safely
    task = execute_cleaning_task.delay(
        dataset_id,
        payload.input_file_path,
        [action.model_dump() for action in payload.approved_actions]
    )
    
    return {
        "message": "Cleaning task accepted and started asynchronously.",
        "task_id": task.id
    }
