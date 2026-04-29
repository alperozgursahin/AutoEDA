import os
import logging
from app.core.celery_app import celery_app
from app.services.execution import apply_cleaning
from app.services.reporting import generate_report

logger = logging.getLogger(__name__)

@celery_app.task(name="execute_cleaning_task")
def execute_cleaning_task(dataset_id: int, input_file_path: str, approved_actions: list):
    """
    Celery background task to apply data cleaning actions and generate a report.
    """
    logger.info(f"Starting cleaning task for dataset_id: {dataset_id}")
    
    # Construct an output path based on the input path
    base, ext = os.path.splitext(input_file_path)
    output_file_path = f"{base}_cleaned{ext}"
    
    try:
        # Step 1: Execute Cleaning
        post_score = apply_cleaning(
            input_path=input_file_path, 
            output_path=output_file_path, 
            approved_actions=approved_actions
        )
        
        # We mock a pre-score here. Typically evaluated earlier in the pipeline.
        pre_score = 65.0
        
        # Step 2: Generate Report
        html_report = generate_report(
            dataset_name=f"Dataset #{dataset_id}",
            pre_score=pre_score,
            post_score=post_score,
            applied_actions=approved_actions
        )
        
        logger.info(f"Successfully completed cleaning for dataset_id {dataset_id}. Post cleaning score: {post_score}.")
        
        # Returning task summary data for celery result backend
        return {
            "status": "success",
            "dataset_id": dataset_id,
            "post_score": post_score,
            "report_length": len(html_report),
            "output_file": output_file_path
        }
        
    except Exception as e:
        logger.error(f"Task failed for dataset_id {dataset_id}: {str(e)}")
        raise e
