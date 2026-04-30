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
        lower_bound = action_dict.get("lower_bound")
        upper_bound = action_dict.get("upper_bound")
        
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
            numeric_series = pd.to_numeric(df[column], errors="coerce")
            if numeric_series.notna().sum() > 0:
                median_val = numeric_series.median()
                df[column] = numeric_series.fillna(median_val)
                logger.info(f"Filled missing values in '{column}' with median ({median_val})")
            else:
                logger.warning(f"Cannot fill median on non-numeric column '{column}'.")
        elif action == "fill_mean":
            numeric_series = pd.to_numeric(df[column], errors="coerce")
            if numeric_series.notna().sum() > 0:
                mean_val = numeric_series.mean()
                df[column] = numeric_series.fillna(mean_val)
                logger.info(f"Filled missing values in '{column}' with mean ({mean_val})")
            else:
                logger.warning(f"Cannot fill mean on non-numeric column '{column}'.")
        elif action == "fill_mode":
            mode_series = df[column].mode(dropna=True)
            if not mode_series.empty:
                mode_val = mode_series.iloc[0]
                df[column] = df[column].fillna(mode_val)
                logger.info(f"Filled missing values in '{column}' with mode ({mode_val})")
            else:
                logger.warning(f"Cannot fill mode on column '{column}' because mode is empty.")
        elif action == "drop_missing_rows":
            df.dropna(subset=[column], inplace=True)
            logger.info(f"Dropped rows with missing values in column '{column}'")
        elif action == "clip_outliers":
            numeric_series = pd.to_numeric(df[column], errors="coerce")
            if numeric_series.notna().sum() == 0:
                logger.warning(f"Cannot clip outliers on non-numeric column '{column}'.")
                continue
            if lower_bound is None or upper_bound is None:
                logger.warning(f"clip_outliers for '{column}' skipped due to missing bounds.")
                continue
            df[column] = numeric_series.clip(lower=float(lower_bound), upper=float(upper_bound))
            logger.info(f"Clipped outliers in '{column}' to range [{lower_bound}, {upper_bound}]")
        elif action == "drop_outliers":
            numeric_series = pd.to_numeric(df[column], errors="coerce")
            if numeric_series.notna().sum() == 0:
                logger.warning(f"Cannot drop outliers on non-numeric column '{column}'.")
                continue
            if lower_bound is None or upper_bound is None:
                logger.warning(f"drop_outliers for '{column}' skipped due to missing bounds.")
                continue
            df[column] = numeric_series
            valid_mask = numeric_series.between(float(lower_bound), float(upper_bound), inclusive="both") | numeric_series.isna()
            df = df[valid_mask].copy()
            logger.info(f"Dropped outlier rows in '{column}' outside [{lower_bound}, {upper_bound}]")

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
