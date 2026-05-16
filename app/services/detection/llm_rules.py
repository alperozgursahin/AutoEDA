"""
LLM-powered detection rules using Groq API.
Detects semantic entity groups, unit inconsistencies, and meaningless column names.
All LLM functions handle failures gracefully — they never raise exceptions.
"""

import re
import json
import logging
import pandas as pd
from typing import List
from app.services.detection.contracts import DetectionSuggestion

logger = logging.getLogger(__name__)

_MEANINGLESS_PATTERN = re.compile(
    r"^(col|column|field|var|variable|feature|data|value|unnamed|x|y|z|f|a|b|c)\d*$",
    re.IGNORECASE,
)
_SINGLE_CHAR_SAFE = {"id", "no"}
_UNIT_VALUE_RE = re.compile(r"\d+\.?\d*\s*[a-zA-Z]+")
_SEMANTIC_MIN_UNIQUE = 3
_SEMANTIC_MAX_UNIQUE = 40
_SEMANTIC_MAX_UNIQUE_RATIO = 0.7
_SEMANTIC_MIN_ROWS = 10
_UNIT_MIN_RATIO = 0.30
_UNIT_MIN_MATCHING = 5


def detect_meaningless_column_names(df: pd.DataFrame) -> List[DetectionSuggestion]:
    """Flag columns whose names are generic placeholders with no semantic meaning."""
    suggestions = []
    for col in df.columns:
        col_str = str(col).strip()
        is_meaningless = bool(_MEANINGLESS_PATTERN.match(col_str))
        is_single_char = len(col_str) == 1 and col_str.lower() not in _SINGLE_CHAR_SAFE
        if is_meaningless or is_single_char:
            suggestions.append(DetectionSuggestion(
                column=col_str,
                issue_type="MEANINGLESS_COLUMN_NAME",
                description=(
                    f"Column '{col_str}' has a generic, non-descriptive name that provides "
                    "no information about the data it contains. "
                    "This makes the dataset harder to interpret and increases misuse risk."
                ),
                suggested_action="review_column",
                action_params=None,
                requires_user_approval=True,
                severity="low",
            ))
    return suggestions


def detect_semantic_entity_groups(
    df: pd.DataFrame, groq_client
) -> List[DetectionSuggestion]:
    """
    Use LLM to identify string columns where different values refer to the same entity.
    Example: 'IEU', 'İzmir Ekonomi Üniversitesi', 'Izmir University of Economics'.
    """
    suggestions = []
    string_cols = df.select_dtypes(include=["object", "string"]).columns

    for col in string_cols:
        non_null = df[col].dropna()
        if len(non_null) < _SEMANTIC_MIN_ROWS:
            continue
        unique_vals = non_null.unique().tolist()
        n_unique = len(unique_vals)
        unique_ratio = n_unique / len(non_null)

        if not (_SEMANTIC_MIN_UNIQUE <= n_unique <= _SEMANTIC_MAX_UNIQUE):
            continue
        if unique_ratio > _SEMANTIC_MAX_UNIQUE_RATIO:
            continue

        # Convert to strings for JSON serialization
        unique_str = [str(v) for v in unique_vals]

        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a data normalization expert. Analyze values from a dataset column "
                            "and identify groups of values that refer to the same real-world entity, "
                            "despite different spellings, abbreviations, languages, or formats. "
                            "Respond with valid JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Column name: '{col}'\n"
                            f"Unique values: {json.dumps(unique_str)}\n\n"
                            "Identify groups of values that refer to the same entity. "
                            "Only include groups with 2 or more members. "
                            "If no groups exist, return an empty list.\n\n"
                            'Respond with this exact JSON: {"groups": [["val1", "val2"], ["val3", "val4"]]}\n'
                            'If no semantic duplicates: {"groups": []}'
                        ),
                    },
                ],
                temperature=0.1,
                max_tokens=512,
            )
            raw = response.choices[0].message.content.strip()
            parsed = json.loads(raw)
            groups = parsed.get("groups", [])
        except Exception as e:
            logger.warning(f"Semantic entity detection failed for column '{col}': {e}")
            continue

        # Filter to valid groups (≥2 members)
        valid_groups = [g for g in groups if isinstance(g, list) and len(g) >= 2]
        if not valid_groups:
            continue

        n_groups = len(valid_groups)
        example_parts = [f"({' / '.join(str(v) for v in g[:3])})" for g in valid_groups[:2]]
        example_str = ", ".join(example_parts)

        suggestions.append(DetectionSuggestion(
            column=col,
            issue_type="SEMANTIC_ENTITY_GROUPS",
            description=(
                f"Column '{col}' contains {n_groups} group(s) of values that likely refer "
                f"to the same real-world entity: {example_str}. "
                "These semantic duplicates inflate unique counts and break grouping operations."
            ),
            suggested_action="review_column",
            action_params={"groups": valid_groups},
            requires_user_approval=True,
            severity="high" if n_groups >= 3 else "medium",
        ))

    return suggestions


def detect_unit_inconsistency(
    df: pd.DataFrame, groq_client
) -> List[DetectionSuggestion]:
    """
    Use LLM to find columns where values measure the same quantity in different units.
    Example: '5 km', '5000 m', '3.1 miles' in the same column.
    """
    suggestions = []
    string_cols = df.select_dtypes(include=["object", "string"]).columns

    for col in string_cols:
        non_null = df[col].dropna().astype(str)
        if len(non_null) < _UNIT_MIN_MATCHING:
            continue

        matching = non_null[non_null.apply(lambda v: bool(_UNIT_VALUE_RE.search(v)))]
        if len(matching) < _UNIT_MIN_MATCHING:
            continue
        if len(matching) / len(non_null) < _UNIT_MIN_RATIO:
            continue

        # Sample up to 20 unique matching values for LLM
        sample = matching.unique().tolist()[:20]
        sample_str = [str(v) for v in sample]

        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a data quality expert. Detect unit inconsistencies in dataset values. "
                            "Respond with valid JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Column: '{col}'\n"
                            f"Sample values: {json.dumps(sample_str)}\n\n"
                            "Do these values measure the same quantity in different units "
                            "(e.g., km vs m vs miles, kg vs g vs lb, USD vs EUR)?\n\n"
                            'Respond: {"has_unit_inconsistency": true/false, '
                            '"unit_groups": [["5 km", "5000 m"], ...], '
                            '"quantity_type": "distance" or null}'
                        ),
                    },
                ],
                temperature=0.1,
                max_tokens=256,
            )
            raw = response.choices[0].message.content.strip()
            parsed = json.loads(raw)
        except Exception as e:
            logger.warning(f"Unit inconsistency detection failed for column '{col}': {e}")
            continue

        if not parsed.get("has_unit_inconsistency"):
            continue

        unit_groups = parsed.get("unit_groups", [])
        quantity_type = parsed.get("quantity_type")
        quantity_str = f" ({quantity_type})" if quantity_type else ""

        suggestions.append(DetectionSuggestion(
            column=col,
            issue_type="UNIT_INCONSISTENCY",
            description=(
                f"Column '{col}' contains values measuring the same quantity{quantity_str} "
                "in different units. Mixed units make numeric comparisons and aggregations meaningless."
            ),
            suggested_action="review_column",
            action_params={"unit_groups": unit_groups, "quantity_type": quantity_type},
            requires_user_approval=True,
            severity="medium",
        ))

    return suggestions


def run_llm_detection_rules(
    df: pd.DataFrame, groq_api_key: str
) -> List[DetectionSuggestion]:
    """
    Orchestrates all LLM-powered detection rules.
    Always runs rule-based meaningless column name detection.
    LLM rules only run when groq_api_key is non-empty.
    Never raises — all exceptions are logged and swallowed.
    """
    results: List[DetectionSuggestion] = []

    # Rule-based (no LLM required)
    try:
        results.extend(detect_meaningless_column_names(df))
    except Exception as e:
        logger.warning(f"detect_meaningless_column_names failed: {e}")

    if not groq_api_key:
        return results

    # LLM-powered rules
    try:
        from groq import Groq
        groq_client = Groq(api_key=groq_api_key)
    except Exception as e:
        logger.warning(f"Could not initialize Groq client: {e}")
        return results

    try:
        results.extend(detect_semantic_entity_groups(df, groq_client))
    except Exception as e:
        logger.warning(f"detect_semantic_entity_groups failed: {e}")

    try:
        results.extend(detect_unit_inconsistency(df, groq_client))
    except Exception as e:
        logger.warning(f"detect_unit_inconsistency failed: {e}")

    return results
