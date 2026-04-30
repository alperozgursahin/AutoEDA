import os
from fastapi import APIRouter, status, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List, Optional

from app.worker.tasks import execute_cleaning_task
from app.services.visualization import build_visualization_data

router = APIRouter(prefix="/datasets", tags=["Datasets"])
DATASET_INPUT_PATHS: Dict[int, str] = {}

class ActionItem(BaseModel):
    action: str
    column: str
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None

class ExecuteRequest(BaseModel):
    input_file_path: str
    approved_actions: List[ActionItem]

@router.post("/{dataset_id}/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_cleaning(dataset_id: int, payload: ExecuteRequest):
    """
    Triggers the asynchronous data cleaning process based on approved actions.
    """
    # Trigger the Celery task safely
    DATASET_INPUT_PATHS[dataset_id] = payload.input_file_path
    task = execute_cleaning_task.delay(
        dataset_id,
        payload.input_file_path,
        [action.model_dump() for action in payload.approved_actions]
    )
    
    return {
        "message": "Cleaning task accepted and started asynchronously.",
        "task_id": task.id
    }


@router.get("/reports/{report_name}")
async def download_report(report_name: str):
    """
    Serves the generated HTML report file to the client.
    """
    if not os.path.exists(report_name):
        raise HTTPException(status_code=404, detail="Report not found")
        
    return FileResponse(
        path=report_name,
        media_type="text/html",
        filename=report_name
    )


@router.get("/{dataset_id}/visualizations")
async def get_visualizations(dataset_id: int, input_file_path: Optional[str] = Query(default=None)):
    """
    Returns raw dataset visualization metadata for dashboard charts.
    """
    resolved_path = input_file_path or DATASET_INPUT_PATHS.get(dataset_id)
    if not resolved_path:
        raise HTTPException(
            status_code=400,
            detail="input_file_path is required for first visualization request of this dataset.",
        )
    if not os.path.exists(resolved_path):
        raise HTTPException(status_code=404, detail=f"Dataset file not found: {resolved_path}")

    DATASET_INPUT_PATHS[dataset_id] = resolved_path
    return build_visualization_data(resolved_path)
