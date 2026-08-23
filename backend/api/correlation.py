"""Correlation Explorer API Blueprint — NEW feature for resume-level project."""
from flask import Blueprint, request, jsonify
import pandas as pd
import numpy as np
from services.data_loader import data
from utils.validators import error_response

correlation_bp = Blueprint('correlation', __name__, url_prefix='/api/correlation')


def _get_indicator_series(indicator, country):
    """
    Extract a time series for a given indicator and country.
    Returns a dict of {year: value} or None if not found.
    """
    if indicator == 'gdp':
        df = data.gdp
        row = df[df['Country Name'] == country]
        if row.empty:
            return None
        years = data.gdp_year_columns
        series = {}
        for y in years:
            val = row[y].iloc[0]
            if pd.notna(val):
                series[y] = float(val)
        return series

    elif indicator == 'inflation':
        df = data.inflation
        row = df[df['Country'] == country]
        if row.empty:
            return None
        year_cols = [c for c in df.columns if c != 'Country']
        series = {}
        for y in year_cols:
            val = row[y].iloc[0]
            if pd.notna(val):
                series[y] = float(val)
        return series

    elif indicator == 'wages':
        df = data.wages
        row = df[df['Country name'] == country]
        if row.empty:
            return None
        year_cols = [c for c in df.columns if c.isdigit()]
        series = {}
        for y in year_cols:
            val = row[y].iloc[0]
            if pd.notna(val):
                series[y] = float(val)
        return series

    elif indicator == 'growth':
        df = data.growth
        row = df[df['Country name'] == country]
        if row.empty:
            return None
        row_data = row.iloc[0, 1:]
        series = {}
        for y, val in row_data.items():
            if pd.notna(val):
                series[str(y).strip()] = float(val)
        return series

    elif indicator == 'debt':
        df = data.debt
        row = df[df['Country Name'] == country]
        if row.empty:
            return None
        year_cols = [c for c in df.columns if c != 'Country Name']
        series = {}
        for y in year_cols:
            val = row[y].iloc[0]
            if pd.notna(val):
                series[y] = float(val)
        return series

    return None


@correlation_bp.route('/')
def get_correlation():
    """
    Compute correlation between two economic indicators for a given country.

    Query params:
        - country: Country name
        - indicator1: First indicator (gdp, inflation, wages, growth, debt)
        - indicator2: Second indicator
    """
    country = request.args.get('country')
    ind1 = request.args.get('indicator1')
    ind2 = request.args.get('indicator2')

    valid_indicators = ['gdp', 'inflation', 'wages', 'growth', 'debt']

    if not country:
        return jsonify(error_response("'country' parameter is required")), 400
    if ind1 not in valid_indicators:
        return jsonify(error_response(f"Invalid indicator1. Choose from: {valid_indicators}")), 400
    if ind2 not in valid_indicators:
        return jsonify(error_response(f"Invalid indicator2. Choose from: {valid_indicators}")), 400
    if ind1 == ind2:
        return jsonify(error_response("Indicators must be different")), 400

    series1 = _get_indicator_series(ind1, country)
    series2 = _get_indicator_series(ind2, country)

    if series1 is None:
        return jsonify(error_response(f"No {ind1} data found for '{country}'")), 404
    if series2 is None:
        return jsonify(error_response(f"No {ind2} data found for '{country}'")), 404

    # Find common years
    common_years = sorted(set(series1.keys()) & set(series2.keys()))

    if len(common_years) < 3:
        return jsonify(error_response(
            f"Not enough overlapping data points ({len(common_years)}). Need at least 3."
        )), 400

    values1 = [series1[y] for y in common_years]
    values2 = [series2[y] for y in common_years]

    # Compute Pearson correlation
    arr1 = np.array(values1)
    arr2 = np.array(values2)

    correlation = float(np.corrcoef(arr1, arr2)[0, 1])

    # Compute linear regression for trend line
    slope, intercept = np.polyfit(arr1, arr2, 1)

    return jsonify({
        'country': country,
        'indicator1': ind1,
        'indicator2': ind2,
        'years': common_years,
        'values1': values1,
        'values2': values2,
        'correlation': round(correlation, 4),
        'regression': {
            'slope': round(float(slope), 6),
            'intercept': round(float(intercept), 4)
        }
    })


@correlation_bp.route('/indicators')
def get_available_indicators():
    """Get list of available indicators for correlation analysis."""
    return jsonify({
        'indicators': [
            {'id': 'gdp', 'name': 'GDP Per Capita', 'unit': 'USD'},
            {'id': 'inflation', 'name': 'Inflation Rate', 'unit': '%'},
            {'id': 'wages', 'name': 'Average Wages', 'unit': 'USD'},
            {'id': 'growth', 'name': 'Real Growth Rate', 'unit': '%'},
            {'id': 'debt', 'name': 'Debt-to-GDP Ratio', 'unit': '%'}
        ]
    })


@correlation_bp.route('/countries')
def get_correlation_countries():
    """Get countries that have data in at least two indicators."""
    gdp_countries = set(data.gdp['Country Name'].dropna().unique())
    growth_countries = set(data.growth['Country name'].dropna().unique())
    wage_countries = set(data.wages['Country name'].dropna().unique())

    # Return countries that appear in at least GDP + one other dataset
    all_sets = [gdp_countries, growth_countries, wage_countries]
    combined = set()
    for s in all_sets:
        combined |= s

    return jsonify(sorted(list(combined)))
