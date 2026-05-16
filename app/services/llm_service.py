"""
Purpose:
Generate plain-English explanations for rule-based data quality issues.
This file does not decide cleaning actions.
This file does not modify data.
The rule engine decides severity and suggested_action.
"""

import json
import logging

logger = logging.getLogger(__name__)


def generate_explanations(issues: list) -> tuple[list[dict], dict]:
    """
    Returns (explanations, metadata).
    metadata = {"llm_used": bool, "llm_model": str | None}
    Falls back to rule-based templates if GROQ_API_KEY is missing or call fails.
    """
    if not issues:
        return [], {"llm_used": False, "llm_model": None}

    from app.core.config import settings

    if settings.GROQ_API_KEY:
        try:
            explanations = _generate_with_groq(issues)
            return explanations, {"llm_used": True, "llm_model": "llama-3.3-70b-versatile"}
        except Exception as e:
            logger.warning(f"Groq LLM call failed, using fallback explanations: {e}")

    return [generate_fallback_explanation(issue) for issue in issues], {"llm_used": False, "llm_model": None}


def _generate_with_groq(issues: list) -> list[dict]:
    from groq import Groq
    from app.core.config import settings

    client = Groq(api_key=settings.GROQ_API_KEY)

    simplified = [
        {
            "column": i.get("column") or "dataset",
            "issue_type": i.get("issue_type"),
            "severity": i.get("severity"),
            "suggested_action": i.get("suggested_action"),
            "description": i.get("description", ""),
            "metrics": i.get("metrics", {}),
        }
        for i in issues
    ]

    system_prompt = (
        "You are a data quality expert helping non-technical users understand issues in their CSV dataset. "
        "Always respond with valid JSON only, no markdown, no explanation outside the JSON."
    )

    user_prompt = f"""For each data quality issue below, produce an explanation object with exactly these fields:
- "explanation": What the problem is in plain English. Mention the column name and key numbers. (1-2 sentences)
- "recommendation_reason": Why this matters and why the suggested action is appropriate. (1-2 sentences)
- "user_warning": One specific thing to verify before approving this action. (1 sentence)

Be concise, non-technical, and accurate. Use exact column names and metric values from the input. Do not invent numbers.

Respond with a JSON object: {{"explanations": [<array of {len(simplified)} objects in input order>]}}

Issues:
{json.dumps(simplified, indent=2)}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=4096,
    )

    raw = response.choices[0].message.content.strip()
    parsed = json.loads(raw)
    result = parsed.get("explanations", parsed) if isinstance(parsed, dict) else parsed

    if not isinstance(result, list) or len(result) != len(issues):
        raise ValueError(f"Expected list of {len(issues)} explanations, got: {type(result).__name__} len={len(result) if isinstance(result, list) else 'N/A'}")

    return result


def generate_fallback_explanation(issue: dict) -> dict:
    """
    Generates a safe fallback explanation when the LLM is not available.

    Args:
        issue: rule-based issue dictionary

    Returns:
        Explanation dictionary with user-facing messages
    """

    column = issue.get("column", "this column")
    issue_type = issue.get("issue_type", "data_quality_issue")
    severity = issue.get("severity", "medium")
    suggested_action = issue.get("suggested_action", "review_column")
    metrics = issue.get("metrics", {})

    # Missing Values Explanation
    if issue_type == "missing_values":

        missing_count = metrics.get("missing_count", 0)
        missing_ratio = metrics.get("missing_ratio", 0)
        missing_percentage = round(missing_ratio * 100, 2)

        return {
            "explanation": (
                f"The column '{column}' contains {missing_count} missing values, "
                f"which represents {missing_percentage}% of the dataset."
            ),

            "recommendation_reason": (
                f"The system classified this as a {severity} issue and suggested "
                f"'{suggested_action}' based on the missing value ratio."
            ),

            "user_warning": (
                "Please review this suggestion before approving it. "
                "The original dataset will not be modified unless you approve the action."
            )
        }

    # Type Mismatch Explanation
    if issue_type == "type_mismatch":

        invalid_count = metrics.get("invalid_count", 0)
        invalid_ratio = metrics.get("invalid_ratio", 0)
        expected_type = metrics.get("expected_type", "expected type")

        invalid_percentage = round(invalid_ratio * 100, 2)

        return {
            "explanation": (
                f"The column '{column}' contains {invalid_count} invalid values "
                f"({invalid_percentage}% of the dataset) that do not match the expected "
                f"{expected_type} type."
            ),

            "recommendation_reason": (
                f"The system classified this as a {severity} issue and suggested "
                f"'{suggested_action}' because inconsistent values may reduce data reliability."
            ),

            "user_warning": (
                "Please inspect the invalid values before approving any cleaning action."
            )
        }

    # ── Benhur's structural & statistical issue types ────────────────────────
    # For these types the rule engine already produces a user-friendly description.
    # We reuse it as the explanation and add issue-specific reasoning / warnings.

    if issue_type == "DUPLICATE_ROWS":
        return {
            "explanation": issue.get("description", f"Duplicate rows were detected in the dataset."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Duplicate rows inflate statistics, distort frequency counts, "
                "and can cause data leakage in model training."
            ),
            "user_warning": (
                "Dropping duplicates is irreversible. "
                "Verify the flagged rows are true duplicates and not legitimate repeated observations."
            ),
        }

    if issue_type == "CONSTANT_COLUMN":
        return {
            "explanation": issue.get("description", f"Column '{column}' has only one unique value."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Columns with zero variance carry no information and add unnecessary noise to analysis."
            ),
            "user_warning": (
                "Verify this column is not intentionally constant "
                "(e.g., a version flag or dataset-level metadata) before dropping it."
            ),
        }

    if issue_type == "ALL_NULL_COLUMN":
        return {
            "explanation": issue.get("description", f"Column '{column}' contains no values at all."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "A completely empty column cannot contribute to any analysis or model."
            ),
            "user_warning": (
                "Ensure this column is not expected to be populated by a future data pipeline "
                "before approving the drop."
            ),
        }

    if issue_type == "HIGH_CARDINALITY":
        return {
            "explanation": issue.get("description", f"Column '{column}' has very high cardinality."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "High-cardinality string columns (IDs, free text) cannot be used directly "
                "in most statistical analyses or machine learning models."
            ),
            "user_warning": (
                "Confirm this is not a meaningful low-cardinality column "
                "before dropping it — check whether the unique count is expected."
            ),
        }

    if issue_type == "MIXED_TYPES":
        return {
            "explanation": issue.get("description", f"Column '{column}' contains mixed data types."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Mixed-type columns cause silent coercion errors in numeric operations "
                "and unreliable aggregations."
            ),
            "user_warning": (
                "Inspect the non-numeric values before approving — "
                "they may represent valid categories or data entry errors that need manual correction."
            ),
        }

    if issue_type == "OUTLIERS_IQR":
        metrics_str = ""
        lower = metrics.get("lower_bound")
        upper = metrics.get("upper_bound")
        if lower is not None and upper is not None:
            metrics_str = f" Proposed clip range: [{lower:.4g}, {upper:.4g}]."
        return {
            "explanation": issue.get("description", f"Column '{column}' contains outliers detected by IQR."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Outliers distort means, inflate variance, and can destabilize model training."
                f"{metrics_str}"
            ),
            "user_warning": (
                "Review the proposed clip bounds — they are derived from quartiles "
                "and may need adjustment for your specific domain."
            ),
        }

    if issue_type == "SKEWED_DISTRIBUTION":
        return {
            "explanation": issue.get("description", f"Column '{column}' has a heavily skewed distribution."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Heavy skew biases mean-based statistics and can degrade gradient-based model performance."
            ),
            "user_warning": (
                "Clipping reduces the tail effect but does not eliminate skew. "
                "Consider a log or square-root transformation as an alternative."
            ),
        }

    if issue_type == "LOW_VARIANCE":
        return {
            "explanation": issue.get("description", f"Column '{column}' has very low variance."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Near-constant numeric columns provide minimal discriminating signal "
                "for statistical analysis or model training."
            ),
            "user_warning": (
                "Verify the column is not a deliberately scaled or normalized feature "
                "before approving the drop."
            ),
        }

    if issue_type == "HIGH_CORRELATION":
        return {
            "explanation": issue.get("description", f"Column '{column}' is highly correlated with another column."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Highly correlated columns introduce multicollinearity, "
                "inflating model variance and making coefficient interpretation unreliable."
            ),
            "user_warning": (
                "Dropping a column is permanent. Confirm which of the correlated pair "
                "is more meaningful to retain before approving."
            ),
        }

    if issue_type == "DATE_FORMAT_INCONSISTENCY":
        detected_formats = metrics.get("detected_formats", [])
        formats_str = ", ".join(detected_formats) if detected_formats else "multiple formats"
        return {
            "explanation": (
                f"Column '{column}' contains dates written in {len(detected_formats) if detected_formats else 'multiple'} "
                f"different formats ({formats_str}). This causes inconsistent parsing and comparison errors."
            ),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Mixed date formats silently produce wrong results when sorting, filtering, or computing date differences."
            ),
            "user_warning": (
                "Verify which format is correct for your data before standardizing — "
                "ambiguous dates like 01/02/2023 could be January 2nd or February 1st."
            ),
        }

    if issue_type == "TURKISH_CHARACTER_MISMATCH":
        return {
            "explanation": issue.get("description", f"Column '{column}' contains the same values written with and without Turkish characters (e.g., 'şırnak' vs 'sirnak')."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Turkish/ASCII character variants are treated as different values, causing incorrect grouping, counting, and joins."
            ),
            "user_warning": (
                "Decide on a canonical form (Turkish or ASCII) before normalizing — "
                "ensure consistency with how this column is used in downstream systems."
            ),
        }

    if issue_type == "WHITESPACE_ISSUES":
        affected_count = metrics.get("affected_count", 0)
        affected_ratio = metrics.get("affected_ratio", 0)
        affected_pct = round(affected_ratio * 100, 1)
        return {
            "explanation": (
                f"Column '{column}' has {affected_count} values ({affected_pct}%) with leading, trailing, "
                "or multiple internal spaces. These invisible characters cause failed string matches and duplicates."
            ),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Whitespace inconsistencies make identical values appear different, breaking grouping and joins."
            ),
            "user_warning": (
                "Trimming is generally safe, but verify that no values intentionally start/end with spaces."
            ),
        }

    if issue_type == "NUMBER_FORMAT_INCONSISTENCY":
        european = metrics.get("european_count", 0)
        american = metrics.get("american_count", 0)
        return {
            "explanation": (
                f"Column '{column}' mixes European number format (e.g., 1.234,56) and American format (e.g., 1,234.56). "
                f"Found {european} European-style and {american} American-style values."
            ),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Mixed number separators cause incorrect numeric parsing — 1.000 means one thousand in Europe but one in America."
            ),
            "user_warning": (
                "Identify the intended format before converting — check the data source's locale settings."
            ),
        }

    if issue_type == "CONTACT_FORMAT_ISSUES":
        contact_type = metrics.get("contact_type", "contact")
        invalid_count = metrics.get("invalid_count", 0)
        return {
            "explanation": issue.get("description", f"Column '{column}' appears to be a {contact_type} column but contains {invalid_count} invalid or inconsistently formatted values."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                f"Invalid {contact_type} formats cause delivery failures and cannot be used for communication or validation."
            ),
            "user_warning": (
                f"Review invalid {contact_type} values manually before removing — they may be data entry errors that can be corrected."
            ),
        }

    if issue_type == "SEMANTIC_ENTITY_GROUPS":
        groups = metrics.get("groups", [])
        n_groups = len(groups)
        example = f" (e.g., {groups[0]})" if groups else ""
        return {
            "explanation": (
                f"Column '{column}' contains {n_groups} group(s) of values that likely refer to the same entity{example}. "
                "These are detected as semantic duplicates — different spellings, languages, or abbreviations of the same concept."
            ),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Semantic duplicates inflate unique value counts, break grouping operations, and distort frequency analysis."
            ),
            "user_warning": (
                "Review each group carefully — choose one canonical form before normalizing. "
                "Not all similar-looking values are guaranteed to be the same entity."
            ),
        }

    if issue_type == "UNIT_INCONSISTENCY":
        quantity = metrics.get("quantity_type", "quantity")
        unit_groups = metrics.get("unit_groups", [])  # noqa: F841
        return {
            "explanation": issue.get("description", f"Column '{column}' contains values measuring the same {quantity or 'quantity'} in different units."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Mixed units make numeric comparisons and aggregations meaningless without conversion."
            ),
            "user_warning": (
                "Choose a target unit and convert all values before analysis. "
                "Verify conversion factors carefully — unit errors compound silently."
            ),
        }

    if issue_type == "MEANINGLESS_COLUMN_NAME":
        return {
            "explanation": issue.get("description", f"Column '{column}' has a generic name that provides no information about its content."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Meaningless column names make the dataset hard to interpret and increase the risk of misuse."
            ),
            "user_warning": (
                "Rename this column to reflect its actual content before sharing or publishing the dataset."
            ),
        }

    # Generic Fallback
    return {
        "explanation": (
            f"The column '{column}' has a detected data quality issue."
        ),

        "recommendation_reason": (
            f"The system classified this as a {severity} issue and suggested "
            f"'{suggested_action}' based on rule-based analysis."
        ),

        "user_warning": (
            "Please review this suggestion before approving it."
        )
    }

