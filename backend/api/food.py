"""Food Price API Blueprint."""
from flask import Blueprint, request, jsonify
from services.data_loader import data
from utils.validators import error_response

food_bp = Blueprint('food', __name__, url_prefix='/api/food')


@food_bp.route('/countries')
def food_countries():
    """Get list of all countries with food price data."""
    return jsonify(data.food['Entity'].dropna().unique().tolist())


@food_bp.route('/histogram')
def food_histogram_data():
    """Get histogram comparison data for two countries."""
    c1 = request.args.get('country1')
    c2 = request.args.get('country2')

    if not c1 or not c2:
        return jsonify(error_response("Both countries must be provided")), 400

    df = data.food
    selected = df[df['Entity'].isin([c1, c2])]
    food_year_cols = [col for col in df.columns if col.isdigit()]
    recent_years = food_year_cols[-5:]

    result = []
    for year in recent_years:
        row = {'Year': year}
        for _, r in selected.iterrows():
            row[r['Entity']] = r[year]
        result.append(row)

    return jsonify(result)


@food_bp.route('/line')
def food_line_data():
    """Get line chart data for food price trends between two countries."""
    c1 = request.args.get('country1')
    c2 = request.args.get('country2')

    if not c1 or not c2:
        return jsonify(error_response("Both countries must be provided")), 400

    df = data.food
    selected = df[df['Entity'].isin([c1, c2])]
    food_year_cols = [col for col in df.columns if col.isdigit()]
    recent_years = food_year_cols[-5:]

    result = []
    for year in recent_years:
        row = {'Year': year}
        for _, r in selected.iterrows():
            row[r['Entity']] = r[year]
        result.append(row)

    return jsonify(result)
