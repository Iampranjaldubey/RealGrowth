"""Correlation and regression, implemented with the standard library.

The previous implementation called ``numpy.corrcoef`` and ``numpy.polyfit`` and
reported a bare correlation coefficient. A coefficient without a sample size or a
significance estimate invites over-reading: r = 0.9 across four points is noise.

This module returns the supporting statistics alongside the coefficient, and does
so without numpy, which keeps the API image small and the maths inspectable.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

#: Pearson's r needs at least three pairs to be meaningful at all.
MIN_PAIRS = 3

#: Fisher's z transform needs n > 3 for a finite standard error.
MIN_PAIRS_FOR_INFERENCE = 4


class InsufficientDataError(ValueError):
    """Raised when there are too few paired observations to compute a statistic."""


@dataclass(frozen=True, slots=True)
class Regression:
    """Ordinary least squares fit of ``y = slope * x + intercept``."""

    slope: float
    intercept: float

    def predict(self, x: float) -> float:
        return self.slope * x + self.intercept


@dataclass(frozen=True, slots=True)
class CorrelationResult:
    """A correlation plus everything needed to judge whether to trust it."""

    n: int
    r: float
    r_squared: float
    slope: float
    intercept: float
    #: Two-sided p-value for H0: r = 0. ``None`` when n is too small.
    p_value: float | None
    #: 95% confidence interval for r. ``None`` when n is too small.
    ci_low: float | None
    ci_high: float | None

    @property
    def is_significant(self) -> bool:
        """Whether the correlation clears the conventional 5% threshold."""
        return self.p_value is not None and self.p_value < 0.05

    @property
    def strength(self) -> str:
        """A plain-language label, to discourage over-reading the coefficient."""
        magnitude = abs(self.r)
        if magnitude >= 0.8:
            return "very strong"
        if magnitude >= 0.6:
            return "strong"
        if magnitude >= 0.4:
            return "moderate"
        if magnitude >= 0.2:
            return "weak"
        return "negligible"


def _validate(xs: Sequence[float], ys: Sequence[float]) -> None:
    if len(xs) != len(ys):
        raise InsufficientDataError(f"x and y must be the same length, got {len(xs)} and {len(ys)}")
    if len(xs) < MIN_PAIRS:
        raise InsufficientDataError(f"need at least {MIN_PAIRS} paired observations, got {len(xs)}")


def standard_normal_cdf(x: float) -> float:
    """Φ(x), the standard normal cumulative distribution, via ``math.erf``."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Pearson product-moment correlation coefficient.

    Returns ``0.0`` when either variable is constant: the correlation is
    genuinely undefined there, and zero is the honest "no linear relationship"
    answer rather than a NaN that would propagate into JSON as ``null``.
    """
    _validate(xs, ys)
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    covariance = sum(a * b for a, b in zip(dx, dy, strict=True))
    variance_x = sum(a * a for a in dx)
    variance_y = sum(b * b for b in dy)
    if variance_x == 0.0 or variance_y == 0.0:
        return 0.0
    r = covariance / math.sqrt(variance_x * variance_y)
    # Guard against floating-point drift past the mathematical bounds.
    return max(-1.0, min(1.0, r))


def linear_regression(xs: Sequence[float], ys: Sequence[float]) -> Regression:
    """Least-squares line through the points."""
    _validate(xs, ys)
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    variance_x = sum((x - mean_x) ** 2 for x in xs)
    if variance_x == 0.0:
        # Vertical point cloud: no meaningful slope, fall back to the mean.
        return Regression(slope=0.0, intercept=mean_y)
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    slope = covariance / variance_x
    return Regression(slope=slope, intercept=mean_y - slope * mean_x)


def correlate(xs: Sequence[float], ys: Sequence[float]) -> CorrelationResult:
    """Full correlation summary: coefficient, fit, significance and interval.

    Significance uses Fisher's z transform, whose sampling distribution is
    approximately normal with standard error ``1/sqrt(n - 3)``. That avoids
    needing a Student-t implementation while remaining accurate for the sample
    sizes here (a country's series spans 5 to 64 years).
    """
    _validate(xs, ys)
    r = pearson(xs, ys)
    fit = linear_regression(xs, ys)
    n = len(xs)

    p_value: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None

    if n > MIN_PAIRS_FOR_INFERENCE - 1 and abs(r) < 1.0:
        standard_error = 1.0 / math.sqrt(n - 3)
        z = math.atanh(r)
        p_value = 2.0 * (1.0 - standard_normal_cdf(abs(z) / standard_error))
        p_value = max(0.0, min(1.0, p_value))
        ci_low = math.tanh(z - 1.96 * standard_error)
        ci_high = math.tanh(z + 1.96 * standard_error)
    elif abs(r) >= 1.0:
        # A perfect fit: the transform diverges, but the conclusion is obvious.
        p_value = 0.0
        ci_low = ci_high = r

    return CorrelationResult(
        n=n,
        r=r,
        r_squared=r * r,
        slope=fit.slope,
        intercept=fit.intercept,
        p_value=p_value,
        ci_low=ci_low,
        ci_high=ci_high,
    )
