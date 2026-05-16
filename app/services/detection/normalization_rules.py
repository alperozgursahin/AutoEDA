"""
Rule-based detection for data normalization issues.
Detects date format inconsistencies, Turkish character mismatches,
whitespace issues, number format inconsistencies, and contact format problems.
"""

import re
import pandas as pd
from typing import List
from app.services.detection.contracts import DetectionSuggestion

# ── Compiled regex patterns ────────────────────────────────────────────────────

_DATE_PATTERNS = {
    "DMY_slash": re.compile(r"\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4}\b"),
    "ISO": re.compile(r"\b\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}\b"),
    "text_month": re.compile(
        r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
        re.IGNORECASE,
    ),
    "YMD_compact": re.compile(r"\b\d{8}\b"),
}
_DATE_MIN_RATIO = 0.6
_MIN_ROWS = 5

_TURKISH_MAP = str.maketrans("şğüıöçŞĞÜİÖÇ", "sguiocSGUIoc")  # Note: İ→I needs special handling

_EU_NUMBER = re.compile(r"^-?\d{1,3}(\.\d{3})+(,\d+)?$")
_US_NUMBER = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")
_COMMA_DECIMAL = re.compile(r"^-?\d+,\d+$")
_DOT_DECIMAL = re.compile(r"^-?\d+\.\d+$")
_MIN_NUMERIC_LOOKING = 5

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_PHONE_RE = re.compile(r"^[\+\d][\d\s\-\(\)\.]{6,20}$")
_EMAIL_MIN_RATIO = 0.5
_PHONE_MIN_RATIO = 0.5


def detect_date_format_inconsistency(df: pd.DataFrame) -> List[DetectionSuggestion]:
    """Detect columns that contain dates in multiple inconsistent formats."""
    suggestions = []
    for col in df.select_dtypes(include=["object", "string"]).columns:
        non_null = df[col].dropna().astype(str)
        if len(non_null) < _MIN_ROWS:
            continue

        # Check if column is date-like: any pattern matches ≥60% of values
        format_counts = {}
        for fmt_name, pattern in _DATE_PATTERNS.items():
            count = int(non_null.apply(lambda v: bool(pattern.search(v))).sum())
            if count > 0:
                format_counts[fmt_name] = count

        # Column must have at least one format with ≥60% coverage to be considered date-like
        date_like = any(c / len(non_null) >= _DATE_MIN_RATIO for c in format_counts.values())
        if not date_like or len(format_counts) < 2:
            continue

        # Check for ambiguity: values where day ≤ 12 (could be MM/DD or DD/MM)
        ambiguous_count = int(non_null.apply(
            lambda v: bool(re.search(r"\b(0?[1-9]|1[0-2])[/\-\.](0?[1-9]|1[0-2])[/\-\.]\d{2,4}\b", v))
        ).sum())

        severity = "high" if ambiguous_count > 0 else "medium"
        detected = list(format_counts.keys())

        suggestions.append(DetectionSuggestion(
            column=col,
            issue_type="DATE_FORMAT_INCONSISTENCY",
            description=(
                f"Column '{col}' contains dates in {len(detected)} different formats "
                f"({', '.join(detected)}). "
                + (f"{ambiguous_count} values are ambiguous (day and month both ≤ 12). " if ambiguous_count else "")
                + "Inconsistent formats cause silent parsing errors and wrong date comparisons."
            ),
            suggested_action="review_column",
            action_params={"detected_formats": detected, "ambiguous_count": ambiguous_count},
            requires_user_approval=True,
            severity=severity,
        ))
    return suggestions


def detect_turkish_character_issues(df: pd.DataFrame) -> List[DetectionSuggestion]:
    """Detect columns where Turkish diacritics cause the same entity to appear as different values."""
    suggestions = []

    def _normalize_turkish(val: str) -> str:
        # Handle İ→I separately (str.maketrans doesn't handle multi-byte well)
        val = val.replace("İ", "I").replace("ı", "i")
        return val.translate(_TURKISH_MAP).lower()

    for col in df.select_dtypes(include=["object", "string"]).columns:
        non_null = df[col].dropna().astype(str)
        if len(non_null) < _MIN_ROWS:
            continue

        # Build map: normalized → set of original values
        norm_to_originals: dict[str, set] = {}
        for val in non_null.unique():
            norm = _normalize_turkish(val)
            norm_to_originals.setdefault(norm, set()).add(val)

        # Find groups with 2+ distinct originals
        mismatch_groups = [
            sorted(originals)
            for originals in norm_to_originals.values()
            if len(originals) >= 2
        ]

        if not mismatch_groups:
            continue

        n = len(mismatch_groups)
        example_strs = [f"({' ↔ '.join(g[:3])})" for g in mismatch_groups[:2]]

        suggestions.append(DetectionSuggestion(
            column=col,
            issue_type="TURKISH_CHARACTER_MISMATCH",
            description=(
                f"Column '{col}' has {n} group(s) of values that differ only in Turkish characters "
                f"(e.g., {', '.join(example_strs)}). "
                "These are treated as distinct values but likely represent the same entity."
            ),
            suggested_action="review_column",
            action_params={"mismatch_groups": mismatch_groups[:5]},
            requires_user_approval=True,
            severity="high" if n > 5 else "medium",
        ))
    return suggestions


def detect_whitespace_issues(df: pd.DataFrame) -> List[DetectionSuggestion]:
    """Detect columns with leading/trailing or multiple internal spaces."""
    suggestions = []
    for col in df.select_dtypes(include=["object", "string"]).columns:
        non_null = df[col].dropna().astype(str)
        if len(non_null) == 0:
            continue

        stripped = non_null.str.strip()
        has_outer = non_null != stripped

        internal_multi = non_null[~has_outer].apply(
            lambda v: bool(re.search(r"  +", v))  # two or more consecutive spaces
        )

        affected_mask = has_outer | pd.Series(
            internal_multi.reindex(non_null.index, fill_value=False), index=non_null.index
        )
        affected_count = int(affected_mask.sum())

        if affected_count == 0:
            continue

        affected_ratio = affected_count / len(non_null)
        suggestions.append(DetectionSuggestion(
            column=col,
            issue_type="WHITESPACE_ISSUES",
            description=(
                f"Column '{col}' has {affected_count} value(s) ({affected_ratio:.1%}) "
                "with leading, trailing, or multiple internal spaces. "
                "These invisible characters cause failed string matches and phantom duplicates."
            ),
            suggested_action="trim_whitespace",
            action_params={"affected_count": affected_count, "affected_ratio": round(affected_ratio, 4)},
            requires_user_approval=True,
            severity="medium" if affected_ratio >= 0.1 else "low",
        ))
    return suggestions


def detect_number_format_inconsistency(df: pd.DataFrame) -> List[DetectionSuggestion]:
    """Detect columns mixing European (1.234,56) and American (1,234.56) number formats."""
    suggestions = []
    for col in df.select_dtypes(include=["object", "string"]).columns:
        non_null = df[col].dropna().astype(str).str.strip()
        if len(non_null) < _MIN_NUMERIC_LOOKING:
            continue

        eu_count = int(non_null.apply(lambda v: bool(_EU_NUMBER.match(v))).sum())
        us_count = int(non_null.apply(lambda v: bool(_US_NUMBER.match(v))).sum())
        comma_dec = int(non_null.apply(lambda v: bool(_COMMA_DECIMAL.match(v))).sum())
        dot_dec   = int(non_null.apply(lambda v: bool(_DOT_DECIMAL.match(v))).sum())

        # Flag if both structured EU and US thousand-separator formats coexist
        mixed_thousands = eu_count > 0 and us_count > 0
        # Flag if both comma-decimal and dot-decimal simple formats coexist
        mixed_decimal = comma_dec > 0 and dot_dec > 0

        if not mixed_thousands and not mixed_decimal:
            continue

        suggestions.append(DetectionSuggestion(
            column=col,
            issue_type="NUMBER_FORMAT_INCONSISTENCY",
            description=(
                f"Column '{col}' mixes number formats: "
                + (f"{eu_count} European-style (e.g., 1.234,56) and {us_count} American-style (e.g., 1,234.56). " if mixed_thousands else "")
                + (f"{comma_dec} comma-decimal and {dot_dec} dot-decimal values." if mixed_decimal and not mixed_thousands else "")
                + " Mixed separators cause silent numeric parsing errors."
            ),
            suggested_action="review_column",
            action_params={
                "european_count": eu_count,
                "american_count": us_count,
                "comma_decimal_count": comma_dec,
                "dot_decimal_count": dot_dec,
            },
            requires_user_approval=True,
            severity="medium",
        ))
    return suggestions


def detect_contact_format_issues(df: pd.DataFrame) -> List[DetectionSuggestion]:
    """Detect email columns with invalid addresses and phone columns with inconsistent formats."""
    suggestions = []
    for col in df.select_dtypes(include=["object", "string"]).columns:
        non_null = df[col].dropna().astype(str).str.strip()
        if len(non_null) < _MIN_ROWS:
            continue

        # ── Email detection ──
        email_matches = non_null.apply(lambda v: bool(_EMAIL_RE.match(v)))
        email_ratio = email_matches.sum() / len(non_null)
        if email_ratio >= _EMAIL_MIN_RATIO:
            invalid_count = int((~email_matches).sum())
            if invalid_count > 0:
                suggestions.append(DetectionSuggestion(
                    column=col,
                    issue_type="CONTACT_FORMAT_ISSUES",
                    description=(
                        f"Column '{col}' appears to be an email column ({email_ratio:.0%} valid emails) "
                        f"but contains {invalid_count} invalid or malformed email address(es)."
                    ),
                    suggested_action="review_column",
                    action_params={
                        "contact_type": "email",
                        "invalid_count": invalid_count,
                        "valid_count": int(email_matches.sum()),
                    },
                    requires_user_approval=True,
                    severity="medium",
                ))
            continue  # Don't also check as phone

        # ── Phone detection ──
        phone_matches = non_null.apply(lambda v: bool(_PHONE_RE.match(v)))
        phone_ratio = phone_matches.sum() / len(non_null)
        if phone_ratio >= _PHONE_MIN_RATIO:
            # Check for format inconsistency: different prefixes
            matched_phones = non_null[phone_matches]
            has_plus = int(matched_phones.str.startswith("+").sum())
            has_zero_prefix = int(matched_phones.str.match(r"^0[^0]").sum())
            has_plain = int(matched_phones.apply(
                lambda v: not v.startswith("+") and not v.startswith("0")
            ).sum())
            formats_used = sum([has_plus > 0, has_zero_prefix > 0, has_plain > 0])
            if formats_used >= 2:
                suggestions.append(DetectionSuggestion(
                    column=col,
                    issue_type="CONTACT_FORMAT_ISSUES",
                    description=(
                        f"Column '{col}' appears to be a phone column ({phone_ratio:.0%} phone-like values) "
                        f"but uses {formats_used} different format styles "
                        f"(+country: {has_plus}, 0-prefix: {has_zero_prefix}, plain: {has_plain})."
                    ),
                    suggested_action="review_column",
                    action_params={
                        "contact_type": "phone",
                        "invalid_count": int((~phone_matches).sum()),
                        "format_count": formats_used,
                    },
                    requires_user_approval=True,
                    severity="low",
                ))
    return suggestions
