"""Real Economic Growth API Blueprint."""
from flask import Blueprint, request, jsonify
from services.data_loader import data
from utils.validators import error_response

growth_bp = Blueprint('growth', __name__, url_prefix='/api/growth')


@growth_bp.route('/countries')
def get_growth_countries():
    """Get list of all countries with growth data."""
    return jsonify(data.growth['Country name'].dropna().unique().tolist())


@growth_bp.route('/<country>')
def get_real_growth(country):
    """Get real economic growth rate data for a specific country."""
    df = data.growth
    row = df[df['Country name'] == country]

    if row.empty:
        return jsonify(error_response(f"Country '{country}' not found")), 404

    row_data = row.iloc[0, 1:]  # exclude 'Country name'
    years = row_data.index.tolist()
    values = row_data.values.tolist()

    return jsonify({"years": years, "values": values})
