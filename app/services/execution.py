import pandas as pd
import logging

logger = logging.getLogger(__name__)

def apply_cleaning(input_path: str, output_path: str, approved_actions: list) -> dict:
    """
    Applies a list of cleaning actions onto a dataset using Pandas.
    Returns a stats dictionary.
    """
    logger.info(f"Loading dataset from {input_path}")
    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        logger.error(f"Error reading file {input_path}. Exception: {e}")
        raise e

    initial_rows, initial_cols = df.shape
    initial_missing = int(df.isna().sum().sum())

    for action_dict in approved_actions:
        action = action_dict.get("action")
        column = action_dict.get("column")
        
        if not action:
            continue
            
        if action == "drop_duplicates":
            df.drop_duplicates(inplace=True)
            logger.info("Dropped duplicate rows")
            continue
            
        if not column or column not in df.columns:
            logger.warning(f"Column '{column}' not found or not provided. Skipping action '{action}'.")
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
        elif action == "fill_mean":
            if pd.api.types.is_numeric_dtype(df[column]):
                mean_val = df[column].mean()
                df[column].fillna(mean_val, inplace=True)
                logger.info(f"Filled missing values in '{column}' with mean ({mean_val})")
            else:
                logger.warning(f"Cannot fill mean on non-numeric column '{column}'.")
        elif action == "drop_missing_rows":
            df.dropna(subset=[column], inplace=True)
            logger.info(f"Dropped rows with missing values in column '{column}'")

    # Save cleaned file
    logger.info(f"Saving cleaned dataset to {output_path}")
    df.to_csv(output_path, index=False)
    
    final_rows, final_cols = df.shape
    final_missing = int(df.isna().sum().sum())
    
    pre_cleaning_score = max(0.0, min(100.0, 100.0 - (initial_missing * 2)))
    post_cleaning_score = max(0.0, min(100.0, 100.0 - (final_missing * 2)))

    return {
        "pre_cleaning_score": round(pre_cleaning_score, 2),
        "post_cleaning_score": round(post_cleaning_score, 2),
        "initial_rows": initial_rows,
        "initial_cols": initial_cols,
        "final_rows": final_rows,
        "final_cols": final_cols,
        "initial_missing": initial_missing,
        "final_missing": final_missing,
        "missing_removed": initial_missing - final_missing
    }
