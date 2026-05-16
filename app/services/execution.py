import re
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
        elif action == "trim_whitespace":
            df[column] = df[column].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
            logger.info(f"Trimmed whitespace in column '{column}'")
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
        elif action == "standardize_date_format":
            params = action_dict.get("params") or {}
            fmt_name = params.get("target_format", "YYYY-MM-DD")
            fmt_map = {"DD/MM/YYYY": "%d/%m/%Y", "YYYY-MM-DD": "%Y-%m-%d", "MM/DD/YYYY": "%m/%d/%Y"}
            target_fmt = fmt_map.get(fmt_name, "%Y-%m-%d")
            # Parse each value by trying known formats explicitly (ISO first, then DMY, then MDY)
            _date_fmts = [
                "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",  # ISO variants
                "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",  # DMY variants
                "%m/%d/%Y", "%m-%d-%Y",               # MDY variants
            ]
            def _parse_date(val):
                val = str(val).strip()
                for fmt in _date_fmts:
                    try:
                        return pd.to_datetime(val, format=fmt)
                    except (ValueError, TypeError):
                        pass
                return pd.NaT
            parsed = df[column].apply(_parse_date)
            df[column] = parsed.dt.strftime(target_fmt).where(parsed.notna(), df[column])
            logger.info(f"Standardized dates in '{column}' to {fmt_name}")
        elif action == "normalize_turkish_chars":
            params = action_dict.get("params") or {}
            target = params.get("target", "ascii")
            _tr_map = str.maketrans("şğüöçŞĞÜÖÇ", "sguocSGUOC")
            def _normalize(val: str) -> str:
                if not isinstance(val, str):
                    return val
                if target == "ascii":
                    val = val.replace("İ", "I").replace("ı", "i")
                    return val.translate(_tr_map).lower()
                return val.lower()
            df[column] = df[column].astype(str).apply(_normalize)
            logger.info(f"Normalized Turkish characters in '{column}' (target={target})")
        elif action == "standardize_number_format":
            params = action_dict.get("params") or {}
            target = params.get("target", "american")
            _eu = re.compile(r"^-?\d{1,3}(\.\d{3})+(,\d+)?$")
            _us = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")
            def _convert_num(val: str) -> str:
                val = str(val).strip()
                if target == "american" and _eu.match(val):
                    return val.replace(".", "").replace(",", ".")
                if target == "european" and _us.match(val):
                    return val.replace(",", "X").replace(".", ",").replace("X", ".")
                return val
            df[column] = df[column].astype(str).apply(_convert_num)
            logger.info(f"Standardized number format in '{column}' to {target}")
        elif action == "standardize_phone_format":
            params = action_dict.get("params") or {}
            target_prefix = params.get("target_prefix", "international")
            def _normalize_phone(val: str) -> str:
                digits = re.sub(r"[^\d]", "", str(val))
                if digits.startswith("90") and len(digits) >= 12:
                    digits = digits[2:]
                elif digits.startswith("0") and len(digits) >= 11:
                    digits = digits[1:]
                if len(digits) < 10:
                    return val
                if target_prefix == "international":
                    # Add dash after country code so pandas reads as string, not integer
                    return f"+90-{digits}"
                if target_prefix == "local":
                    return f"0{digits}"
                return digits
            df[column] = df[column].astype(str).apply(_normalize_phone)
            logger.info(f"Standardized phone format in '{column}' to {target_prefix}")

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
