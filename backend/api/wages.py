"""Wages API Blueprint."""
from flask import Blueprint, request, jsonify
import pandas as pd
from services.data_loader import data
from utils.validators import error_response

wages_bp = Blueprint('wages', __name__, url_prefix='/api/wages')


@wages_bp.route('/countries')
def get_wage_countries():
    """Get list of all countries with wage data."""
    countries = data.wages['Country name'].dropna().unique().tolist()
    return jsonify(countries)


@wages_bp.route('/<country>')
def get_wages(country):
    """Get average wage data for a specific country across all years."""
    df = data.wages
    row = df[df['Country name'] == country]

    if row.empty:
        return jsonify(error_response(f"Country '{country}' not found")), 404

    wage_year_columns = [col for col in df.columns if col.isdigit()]
    wages = row[wage_year_columns].iloc[0].to_dict()
    clean_wages = {
        year: float(wages[year])
        for year in wages
        if pd.notna(wages[year])
    }
    return jsonify(clean_wages)
