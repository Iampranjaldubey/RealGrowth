"""Request validation utilities."""


def validate_year(year, valid_columns):
    """Validate that a year parameter exists in the dataset columns."""
    if year is None:
        return None, "Year parameter is required"
    if year not in valid_columns:
        return None, f"Year '{year}' not found. Available years: {valid_columns[:5]}..."
    return year, None


def validate_country(country, df, column_name='Country Name'):
    """Validate that a country exists in the dataset."""
    if not country:
        return None, "Country parameter is required"
    if country not in df[column_name].values:
        return None, f"Country '{country}' not found in dataset"
    return country, None


def validate_population(population_str):
    """Validate and convert population filter."""
    try:
        return int(population_str or 0), None
    except (ValueError, TypeError):
        return None, f"Invalid population value: '{population_str}'"


def error_response(message, status_code=400):
    """Create a standardized error response dict."""
    return {'error': message, 'status': status_code}
