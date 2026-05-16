import os
import uuid
import pandas as pd
from fastapi import APIRouter, status, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from app.worker.tasks import execute_cleaning_task
from app.services.visualization import build_visualization_data
from app.services.detection.rule_registry import run_all_rules
from app.services.detection.llm_rules import run_llm_detection_rules
from app.services.suggestion_service import build_suggestions_from_issues

router = APIRouter(prefix="/datasets", tags=["Datasets"])
DATASET_INPUT_PATHS: Dict[int, str] = {}

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ActionItem(BaseModel):
    action: str
    column: str
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    params: Optional[Dict[str, Any]] = None

class ExecuteRequest(BaseModel):
    input_file_path: str
    approved_actions: List[ActionItem]

class DetectRequest(BaseModel):
    input_file_path: str
    expected_types: Optional[Dict[str, str]] = None

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_dataset(file: UploadFile = File(...)):
    """
    Accepts a CSV file, saves it to the uploads directory, and returns a
    dataset_id and the server-side file path for use in subsequent /detect calls.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only CSV files are accepted.")

    dataset_id = int(uuid.uuid4().int % 10**9)
    safe_name = f"{dataset_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    with open(file_path, "wb") as f:
        f.write(contents)

    DATASET_INPUT_PATHS[dataset_id] = file_path

    return {
        "dataset_id": dataset_id,
        "file_path": file_path,
        "filename": file.filename,
    }


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


@router.post("/{dataset_id}/detect", status_code=status.HTTP_200_OK)
async def detect_issues(dataset_id: int, payload: DetectRequest):
    """
    Runs all detection rules on the dataset and returns frontend-ready suggestions.
    Synchronous for MVP; move to Celery when dataset sizes require it.
    """
    if not os.path.exists(payload.input_file_path):
        raise HTTPException(
            status_code=404,
            detail=f"Dataset file not found: {payload.input_file_path}",
        )

    DATASET_INPUT_PATHS[dataset_id] = payload.input_file_path

    try:
        df = pd.read_csv(payload.input_file_path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to read CSV: {e}")

    from app.core.config import settings

    issues = run_all_rules(df, payload.expected_types)

    llm_issues = run_llm_detection_rules(df, settings.GROQ_API_KEY)
    if llm_issues:
        offset = len(issues)
        from app.services.detection.rule_registry import _suggestion_to_issue_dict
        for i, s in enumerate(llm_issues, start=1):
            issues.append(_suggestion_to_issue_dict(s, offset + i))

    suggestions, llm_meta = build_suggestions_from_issues(issues)

    return {
        "dataset_id": dataset_id,
        "total_issues": len(issues),
        "total_suggestions": len(suggestions),
        "llm_used": llm_meta.get("llm_used", False),
        "llm_model": llm_meta.get("llm_model"),
        "suggestions": suggestions,
    }


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
