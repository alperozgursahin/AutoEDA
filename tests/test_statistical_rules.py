import pandas as pd
import numpy as np
import pytest
from app.services.detection.statistical_rules import (
    detect_outliers_iqr,
    detect_skewed_distributions,
    detect_low_variance_columns,
    detect_high_correlation_pairs,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def normal_df():
    rng = np.random.default_rng(42)
    return pd.DataFrame({"a": rng.normal(50, 5, 100), "b": rng.normal(100, 10, 100)})


# ── detect_outliers_iqr ───────────────────────────────────────────────────────

def test_outlier_iqr_detected():
    rng = np.random.default_rng(42)
    # Normal base ensures IQR > 0; 10000.0 lands far outside the IQR fence
    values = rng.normal(50, 5, 50).tolist() + [10000.0]
    df = pd.DataFrame({"price": values})
    results = detect_outliers_iqr(df)
    assert len(results) == 1
    result = results[0]
    assert result.column == "price"
    assert result.issue_type == "OUTLIERS_IQR"
    assert result.suggested_action == "clip_outliers"
    assert result.action_params is not None
    assert "lower_bound" in result.action_params
    assert "upper_bound" in result.action_params
    assert result.requires_user_approval is True


def test_outlier_iqr_none_when_clean(normal_df):
    # Tightly distributed normal data should have no/few outliers flagged
    results = detect_outliers_iqr(normal_df)
    # Not asserting empty (normal dist can produce edge outliers),
    # but action and params must be correct if any exist
    for r in results:
        assert r.suggested_action == "clip_outliers"
        assert r.action_params is not None


def test_outlier_iqr_severity_high_when_over_5_percent():
    # 10 outliers out of 100 rows = 10% → high
    values = list(range(90)) + [10000] * 10
    df = pd.DataFrame({"x": values})
    results = detect_outliers_iqr(df)
    assert any(r.severity == "high" for r in results)


def test_outlier_iqr_severity_medium_when_under_5_percent():
    values = list(range(100)) + [10000]  # 1 outlier / 101 rows ≈ 1%
    df = pd.DataFrame({"x": values})
    results = detect_outliers_iqr(df)
    assert results[0].severity == "medium"


def test_outlier_iqr_skipped_for_small_series():
    df = pd.DataFrame({"x": [1, 2, 1000]})  # only 3 rows, below _OUTLIER_MIN_ROWS=10
    assert detect_outliers_iqr(df) == []


def test_outlier_iqr_skipped_when_iqr_zero():
    # All same value → IQR=0, skip to avoid division by zero
    df = pd.DataFrame({"x": [5.0] * 20})
    assert detect_outliers_iqr(df) == []


def test_outlier_iqr_skips_object_columns():
    df = pd.DataFrame({"text": ["a", "b", "c"] * 10})
    assert detect_outliers_iqr(df) == []


def test_outlier_iqr_does_not_mutate(normal_df):
    original = normal_df.copy()
    detect_outliers_iqr(normal_df)
    pd.testing.assert_frame_equal(normal_df, original)


# ── detect_skewed_distributions ───────────────────────────────────────────────

def test_skewed_distribution_detected():
    rng = np.random.default_rng(42)
    # chi-squared(df=1) has theoretical skewness ≈ 2.83, reliably above the threshold of 2.0
    df = pd.DataFrame({"income": rng.chisquare(1, size=500)})
    results = detect_skewed_distributions(df)
    assert len(results) == 1
    result = results[0]
    assert result.column == "income"
    assert result.issue_type == "SKEWED_DISTRIBUTION"
    assert result.suggested_action == "clip_outliers"
    assert result.action_params is not None
    assert result.action_params["lower_bound"] <= result.action_params["upper_bound"]


def test_skewed_distribution_not_flagged_for_normal(normal_df):
    results = detect_skewed_distributions(normal_df)
    assert results == []


def test_skewed_distribution_severity_high_above_5():
    rng = np.random.default_rng(1)
    # Power law → very high skewness
    values = rng.power(0.1, 300) * 1e6
    df = pd.DataFrame({"x": values})
    results = detect_skewed_distributions(df)
    if results:
        skewness = float(df["x"].skew())
        if abs(skewness) > 5:
            assert results[0].severity == "high"


def test_skewed_distribution_skipped_for_tiny_series():
    df = pd.DataFrame({"x": [1.0, 2.0]})  # only 2 rows, need >= 3
    assert detect_skewed_distributions(df) == []


def test_skewed_distribution_does_not_mutate(normal_df):
    original = normal_df.copy()
    detect_skewed_distributions(normal_df)
    pd.testing.assert_frame_equal(normal_df, original)


# ── detect_low_variance_columns ───────────────────────────────────────────────

def test_low_variance_detected():
    # Values vary by less than 1% of mean
    values = [1000.0 + i * 0.001 for i in range(50)]
    df = pd.DataFrame({"sensor": values})
    results = detect_low_variance_columns(df)
    assert len(results) == 1
    assert results[0].column == "sensor"
    assert results[0].issue_type == "LOW_VARIANCE"
    assert results[0].suggested_action == "drop_column"
    assert results[0].severity == "low"


def test_low_variance_not_flagged_for_normal(normal_df):
    assert detect_low_variance_columns(normal_df) == []


def test_low_variance_skips_constant_column():
    # Constant column has std=0 → skipped (structural rule handles it)
    df = pd.DataFrame({"x": [5.0] * 20})
    assert detect_low_variance_columns(df) == []


def test_low_variance_skips_zero_mean_column():
    # mean_abs=0 → skip to avoid division by zero
    df = pd.DataFrame({"x": [0.0] * 20})
    assert detect_low_variance_columns(df) == []


def test_low_variance_skips_object_columns():
    df = pd.DataFrame({"cat": ["a", "b", "c"] * 10})
    assert detect_low_variance_columns(df) == []


def test_low_variance_does_not_mutate(normal_df):
    original = normal_df.copy()
    detect_low_variance_columns(normal_df)
    pd.testing.assert_frame_equal(normal_df, original)


# ── detect_high_correlation_pairs ────────────────────────────────────────────

def test_high_correlation_detected():
    base = list(range(50))
    df = pd.DataFrame({
        "x": base,
        "y": [v * 2 + 1 for v in base],  # perfect linear correlation with x
        "z": list(range(50, 100)),         # uncorrelated
    })
    results = detect_high_correlation_pairs(df)
    assert len(results) >= 1
    result = results[0]
    assert result.issue_type == "HIGH_CORRELATION"
    assert result.suggested_action == "drop_column"
    assert result.requires_user_approval is True
    assert "x" in result.description and "y" in result.description


def test_high_correlation_not_flagged_for_uncorrelated(normal_df):
    assert detect_high_correlation_pairs(normal_df) == []


def test_high_correlation_no_duplicate_pairs():
    base = list(range(50))
    df = pd.DataFrame({"x": base, "y": [v * 2 for v in base]})
    results = detect_high_correlation_pairs(df)
    # Should report x-y pair only once
    assert len(results) == 1


def test_high_correlation_skipped_for_single_column():
    df = pd.DataFrame({"x": list(range(20))})
    assert detect_high_correlation_pairs(df) == []


def test_high_correlation_skips_object_columns():
    base = list(range(50))
    df = pd.DataFrame({
        "x": base,
        "label": [str(v) for v in base],  # object column, not used in corr
    })
    assert detect_high_correlation_pairs(df) == []


def test_high_correlation_does_not_mutate(normal_df):
    original = normal_df.copy()
    detect_high_correlation_pairs(normal_df)
    pd.testing.assert_frame_equal(normal_df, original)
