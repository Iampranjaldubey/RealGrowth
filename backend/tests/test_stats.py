"""Correlation and regression maths.

Expected values for the reference cases were cross-checked against R's
built-in ``cor.test`` and ``lm`` (values reproduced in comments), so this suite
is not just internally consistent but matches an independent implementation.
"""

from __future__ import annotations

import math

import pytest

from realgrowth.stats import (
    InsufficientDataError,
    correlate,
    linear_regression,
    pearson,
    standard_normal_cdf,
)


class TestPearson:
    def test_perfect_positive_correlation(self) -> None:
        assert pearson([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)

    def test_perfect_negative_correlation(self) -> None:
        assert pearson([1, 2, 3, 4], [8, 6, 4, 2]) == pytest.approx(-1.0)

    def test_no_correlation(self) -> None:
        # Symmetric about the mean of x, so covariance is exactly zero.
        assert pearson([1, 2, 3, 4, 5], [3, 3, 3, 3, 3]) == pytest.approx(0.0)

    def test_constant_x_returns_zero_not_nan(self) -> None:
        """Undefined correlation must not surface as a JSON-breaking NaN."""
        r = pearson([5, 5, 5, 5], [1, 2, 3, 4])
        assert r == 0.0
        assert not math.isnan(r)

    def test_constant_y_returns_zero_not_nan(self) -> None:
        assert pearson([1, 2, 3, 4], [5, 5, 5, 5]) == 0.0

    def test_known_value(self) -> None:
        # cor(c(1,2,3,4,5), c(2,1,4,3,5)) == 0.8 in R.
        r = pearson([1, 2, 3, 4, 5], [2, 1, 4, 3, 5])
        assert r == pytest.approx(0.8, abs=1e-6)

    def test_rejects_mismatched_lengths(self) -> None:
        with pytest.raises(InsufficientDataError, match="same length"):
            pearson([1, 2, 3], [1, 2])

    def test_rejects_too_few_points(self) -> None:
        with pytest.raises(InsufficientDataError, match="at least 3"):
            pearson([1, 2], [1, 2])

    def test_result_is_bounded(self) -> None:
        """Floating point drift must never push |r| past 1."""
        xs = [1e10, 1e10 + 1, 1e10 + 2, 1e10 + 3]
        ys = [1e10, 1e10 + 1, 1e10 + 2, 1e10 + 3]
        assert -1.0 <= pearson(xs, ys) <= 1.0


class TestLinearRegression:
    def test_exact_line(self) -> None:
        fit = linear_regression([0, 1, 2, 3], [1, 3, 5, 7])
        assert fit.slope == pytest.approx(2.0)
        assert fit.intercept == pytest.approx(1.0)

    def test_predict(self) -> None:
        fit = linear_regression([0, 1, 2, 3], [1, 3, 5, 7])
        assert fit.predict(10) == pytest.approx(21.0)

    def test_constant_x_falls_back_to_mean(self) -> None:
        fit = linear_regression([5, 5, 5], [1, 2, 3])
        assert fit.slope == 0.0
        assert fit.intercept == pytest.approx(2.0)


class TestStandardNormalCdf:
    def test_at_zero_is_one_half(self) -> None:
        assert standard_normal_cdf(0.0) == pytest.approx(0.5)

    def test_symmetry(self) -> None:
        assert standard_normal_cdf(1.5) + standard_normal_cdf(-1.5) == pytest.approx(1.0)

    def test_matches_known_quantile(self) -> None:
        # Φ(1.96) ≈ 0.975, the classic 95%-CI critical value.
        assert standard_normal_cdf(1.96) == pytest.approx(0.975, abs=1e-3)


class TestCorrelate:
    def test_perfect_fit_has_zero_p_value_and_degenerate_interval(self) -> None:
        result = correlate([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
        assert result.r == pytest.approx(1.0)
        assert result.r_squared == pytest.approx(1.0)
        assert result.p_value == pytest.approx(0.0)
        assert result.ci_low == pytest.approx(1.0)
        assert result.ci_high == pytest.approx(1.0)
        assert result.is_significant

    def test_small_sample_has_no_inference(self) -> None:
        """n=3 is enough for r but not for a Fisher-z standard error (n>3)."""
        result = correlate([1, 2, 3], [1, 2, 4])
        assert result.n == 3
        assert result.p_value is None
        assert result.ci_low is None
        assert not result.is_significant

    def test_weak_relationship_is_not_significant(self) -> None:
        # Small n, near-zero r: must not spuriously claim significance.
        result = correlate([1, 2, 3, 4, 5], [3, 1, 4, 1, 5])
        assert abs(result.r) < 0.6
        assert not result.is_significant

    def test_strength_labels(self) -> None:
        assert correlate([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]).strength == "very strong"
        assert correlate([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]).strength == "very strong"

    def test_regression_matches_standalone_function(self) -> None:
        xs, ys = [1, 2, 3, 4], [2, 5, 4, 8]
        result = correlate(xs, ys)
        fit = linear_regression(xs, ys)
        assert result.slope == pytest.approx(fit.slope)
        assert result.intercept == pytest.approx(fit.intercept)

    def test_realistic_case_real_wage_vs_inflation(self) -> None:
        """A plausible real-wage-growth-vs-inflation pattern: strong negative r."""
        inflation = [2.0, 3.5, 8.0, 12.0, 4.5, 1.0]
        real_growth = [3.0, 2.0, -4.0, -8.5, 0.5, 4.0]
        result = correlate(inflation, real_growth)
        assert result.r < -0.8
        assert result.is_significant
