import pandas as pd
import logging

logger = logging.getLogger(__name__)

def apply_cleaning(input_path: str, output_path: str, approved_actions: list) -> float:
    """
    Applies a list of cleaning actions onto a dataset using Pandas.
    """
    logger.info(f"Loading dataset from {input_path}")
    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        logger.error(f"Error reading file {input_path}. Exception: {e}")
        raise e

    for action_dict in approved_actions:
        action = action_dict.get("action")
        column = action_dict.get("column")
        
        if not action or not column:
            continue
            
        if column not in df.columns:
            logger.warning(f"Column '{column}' not found. Skipping action '{action}'.")
            continue

        if action == "drop_column":
            df.drop(columns=[column], inplace=True)
            logger.info(f"Dropped column: {column}")
        elif action == "fill_median":
            if pd.api.types.is_numeric_dtype(df[column]):
                median_val = df[column].median()
                df[column].fillna(median_val, inplace=True)
                logger.info(f"Filled missing values in '{column}' with median ({median_val})")
            else:
                logger.warning(f"Cannot fill median on non-numeric column '{column}'.")

    # Save cleaned file
    logger.info(f"Saving cleaned dataset to {output_path}")
    df.to_csv(output_path, index=False)
    
    # Return mock post_cleaning_score
    post_cleaning_score = 92.5
    return post_cleaning_score
