"""Inflation API Blueprint."""
from flask import Blueprint, request, jsonify
from services.data_loader import data
from utils.validators import error_response

inflation_bp = Blueprint('inflation', __name__, url_prefix='/api/inflation')


@inflation_bp.route('/countries')
def get_inflation_countries():
    """Get list of all countries with inflation data."""
    return jsonify({'countries': data.inflation_countries})


@inflation_bp.route('/<country>')
def get_inflation(country):
    """Get inflation rate data for a specific country."""
    if country in data.inflation_data:
        return jsonify({'country': country, 'inflation': data.inflation_data[country]})
    return jsonify(error_response(f"Country '{country}' not found")), 404
