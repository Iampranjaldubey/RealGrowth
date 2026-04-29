"""
Utility functions for input validation and consistent JSON responses.
"""

from flask import jsonify


def success_response(data):
    """Wrap data in a standard success response."""
    return jsonify({
        "status": "success",
        "data": data
    })


def error_response(message, status_code=400):
    """Return a standard error response with the given status code."""
    return jsonify({
        "status": "error",
        "message": message
    }), status_code


def validate_year(year_str, available_years):
    """
    Validate that a year string is present in the list of available year columns.
    Returns (year, None) on success or (None, error_message) on failure.
    """
    if not year_str:
        return None, "Year parameter is required"

    year = str(year_str).strip()
    if year not in available_years:
        return None, f"Year '{year}' is not available. Valid years: {available_years[:5]}..."

    return year, None


def validate_country(country_str, available_countries):
    """
    Validate that a country name exists in the available list.
    Returns (country, None) on success or (None, error_message) on failure.
    """
    if not country_str:
        return None, "Country parameter is required"

    country = str(country_str).strip()
    if country not in available_countries:
        return None, f"Country '{country}' not found"

    return country, None


def safe_float(value):
    """Safely convert a value to float, returning None on failure."""
    try:
        if isinstance(value, str):
            value = value.replace(",", "")
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_round(value, decimals=2):
    """Safely round a numeric value, returning None for non-numeric input."""
    try:
        return round(float(value), decimals)
    except (ValueError, TypeError):
        return None
