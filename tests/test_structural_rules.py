import pandas as pd
import pytest
from app.services.detection.structural_rules import (
    detect_duplicate_rows,
    detect_constant_columns,
    detect_all_null_columns,
    detect_high_cardinality_columns,
    detect_mixed_type_columns,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def clean_df():
    return pd.DataFrame({
        "age": [25, 30, 35, 40],
        "city": ["Istanbul", "Ankara", "Izmir", "Bursa"],
        "score": [80.0, 90.0, 85.0, 95.0],
    })


# ── detect_duplicate_rows ─────────────────────────────────────────────────────

def test_duplicate_rows_detected():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    results = detect_duplicate_rows(df)
    assert len(results) == 1
    result = results[0]
    assert result.issue_type == "DUPLICATE_ROWS"
    assert result.suggested_action == "drop_duplicates"
    assert result.column is None
    assert result.requires_user_approval is True
    assert "1 duplicate" in result.description


def test_duplicate_rows_none(clean_df):
    assert detect_duplicate_rows(clean_df) == []


def test_duplicate_rows_severity_high_when_over_10_percent():
    # 9 duplicates out of 10 rows = 90%
    df = pd.DataFrame({"a": [1] * 10})
    results = detect_duplicate_rows(df)
    assert results[0].severity == "high"


def test_duplicate_rows_severity_medium_when_under_10_percent():
    base = pd.DataFrame({"a": list(range(100))})
    dup_row = pd.DataFrame({"a": [0]})  # 1 duplicate out of 101 rows ≈ 1%
    df = pd.concat([base, dup_row], ignore_index=True)
    results = detect_duplicate_rows(df)
    assert results[0].severity == "medium"


def test_duplicate_rows_does_not_mutate(clean_df):
    original_shape = clean_df.shape
    detect_duplicate_rows(clean_df)
    assert clean_df.shape == original_shape


# ── detect_constant_columns ───────────────────────────────────────────────────

def test_constant_column_detected():
    df = pd.DataFrame({"a": [1, 2, 3], "version": ["v1", "v1", "v1"]})
    results = detect_constant_columns(df)
    assert len(results) == 1
    assert results[0].column == "version"
    assert results[0].issue_type == "CONSTANT_COLUMN"
    assert results[0].suggested_action == "drop_column"


def test_constant_column_not_flagged_when_varied(clean_df):
    assert detect_constant_columns(clean_df) == []


def test_constant_column_with_nulls_still_detected():
    df = pd.DataFrame({"a": [1, None, None], "b": ["x", "x", None]})
    results = detect_constant_columns(df)
    cols = [r.column for r in results]
    assert "b" in cols


def test_constant_column_skips_all_null():
    # All-null column: dropna() yields empty, nunique()==0, not 1 → should NOT be flagged here
    df = pd.DataFrame({"a": [None, None, None]})
    assert detect_constant_columns(df) == []


def test_constant_column_does_not_mutate(clean_df):
    original = clean_df.copy()
    detect_constant_columns(clean_df)
    pd.testing.assert_frame_equal(clean_df, original)


# ── detect_all_null_columns ───────────────────────────────────────────────────

def test_all_null_column_detected():
    df = pd.DataFrame({"a": [1, 2], "b": [None, None]})
    results = detect_all_null_columns(df)
    assert len(results) == 1
    assert results[0].column == "b"
    assert results[0].issue_type == "ALL_NULL_COLUMN"
    assert results[0].severity == "high"


def test_all_null_not_flagged_when_partial_null():
    df = pd.DataFrame({"a": [1, None, 3]})
    assert detect_all_null_columns(df) == []


def test_all_null_none_when_clean(clean_df):
    assert detect_all_null_columns(clean_df) == []


def test_all_null_does_not_mutate(clean_df):
    original = clean_df.copy()
    detect_all_null_columns(clean_df)
    pd.testing.assert_frame_equal(clean_df, original)


# ── detect_high_cardinality_columns ──────────────────────────────────────────

def test_high_cardinality_detected():
    # 55 unique string values out of 55 rows = 100% → high cardinality
    df = pd.DataFrame({"id": [f"user_{i}" for i in range(55)], "val": [1] * 55})
    results = detect_high_cardinality_columns(df)
    assert len(results) == 1
    assert results[0].column == "id"
    assert results[0].issue_type == "HIGH_CARDINALITY"
    assert results[0].severity == "low"


def test_high_cardinality_skipped_for_small_df():
    # Only 10 rows → below MIN_ROWS_FOR_CARDINALITY (50)
    df = pd.DataFrame({"id": [f"user_{i}" for i in range(10)]})
    assert detect_high_cardinality_columns(df) == []


def test_high_cardinality_not_flagged_for_low_cardinality():
    df = pd.DataFrame({"cat": ["a", "b", "c"] * 20})  # 3 unique / 60 rows = 5%
    assert detect_high_cardinality_columns(df) == []


def test_high_cardinality_only_checks_object_columns():
    # Numeric column with high unique count should NOT be flagged
    df = pd.DataFrame({"num": list(range(55))})
    assert detect_high_cardinality_columns(df) == []


def test_high_cardinality_does_not_mutate():
    df = pd.DataFrame({"id": [f"user_{i}" for i in range(55)]})
    original = df.copy()
    detect_high_cardinality_columns(df)
    pd.testing.assert_frame_equal(df, original)


# ── detect_mixed_type_columns ─────────────────────────────────────────────────

def test_mixed_types_detected():
    df = pd.DataFrame({"col": ["1", "2", "three", "4", "five"]})
    results = detect_mixed_type_columns(df)
    assert len(results) == 1
    assert results[0].column == "col"
    assert results[0].issue_type == "MIXED_TYPES"
    assert results[0].suggested_action == "drop_column"


def test_mixed_types_not_flagged_for_pure_numeric_strings():
    df = pd.DataFrame({"col": ["1", "2", "3", "4"]})
    assert detect_mixed_type_columns(df) == []


def test_mixed_types_not_flagged_for_pure_strings():
    df = pd.DataFrame({"col": ["apple", "banana", "cherry"]})
    assert detect_mixed_type_columns(df) == []


def test_mixed_types_skips_non_object_columns():
    df = pd.DataFrame({"num": [1, 2, 3]})
    assert detect_mixed_type_columns(df) == []


def test_mixed_types_skips_all_null_column():
    df = pd.DataFrame({"col": [None, None, None]})
    assert detect_mixed_type_columns(df) == []


def test_mixed_types_does_not_mutate(clean_df):
    original = clean_df.copy()
    detect_mixed_type_columns(clean_df)
    pd.testing.assert_frame_equal(clean_df, original)
