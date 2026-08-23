"""Debt-to-GDP Ratio API Blueprint."""
from flask import Blueprint, request, jsonify
from services.data_loader import data
from utils.validators import error_response

debt_bp = Blueprint('debt', __name__, url_prefix='/api/debt')


@debt_bp.route('/')
def get_debt_data():
    """Get debt-to-GDP ratio data for all countries in a given year."""
    year = request.args.get('year', '2022')
    df = data.debt

    if year not in df.columns:
        return jsonify([])

    result = [
        {"country": row['Country Name'], "value": row[year]}
        for _, row in df.iterrows()
    ]
    return jsonify(result)
