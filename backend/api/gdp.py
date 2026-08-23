"""GDP API Blueprint."""
from flask import Blueprint, request, jsonify
from services.data_loader import data
from utils.validators import validate_year, validate_country, validate_population, error_response

gdp_bp = Blueprint('gdp', __name__, url_prefix='/api/gdp')


@gdp_bp.route('/data', methods=['GET'])
def gdp_data():
    """Get top 10 countries by GDP per capita for a given year and population filter."""
    selected_year = request.args.get('year', '2023')
    pop_str = request.args.get('population', '0')

    selected_pop, err = validate_population(pop_str)
    if err:
        return jsonify(error_response(err)), 400

    df = data.gdp
    year_columns = data.gdp_year_columns

    filtered = df[df['Population'] >= selected_pop].copy()
    if selected_year in df.columns:
        filtered['gdp_per_capita'] = filtered[selected_year]
        top10 = filtered.sort_values(by='gdp_per_capita', ascending=False).head(10)
        chart_labels = list(top10['Country Name'])
        chart_data = list(round(top10['gdp_per_capita'], 2))
    else:
        chart_labels = []
        chart_data = []

    return jsonify({
        'years': year_columns,
        'selected_year': selected_year,
        'selected_pop': selected_pop,
        'chart_labels': chart_labels,
        'chart_data': chart_data
    })


@gdp_bp.route('/countries')
def gdp_countries():
    """Get sorted list of all countries with GDP data."""
    countries = sorted(data.gdp['Country Name'].dropna().unique().tolist())
    return jsonify(countries)


@gdp_bp.route('/')
def api_gdp():
    """Get top 10 countries by GDP per capita for a specific year."""
    year = request.args.get('year')
    min_population, err = validate_population(request.args.get('min_population', '0'))
    if err:
        return jsonify(error_response(err)), 400

    df = data.gdp
    if year not in df.columns:
        return jsonify([])

    filtered = df[df['Population'] >= min_population].copy()
    filtered['gdp_per_capita'] = filtered[year]
    top10 = filtered.sort_values(by='gdp_per_capita', ascending=False).head(10)
    result = [
        {"country": row['Country Name'], "gdp_per_capita": round(row['gdp_per_capita'], 2)}
        for _, row in top10.iterrows()
    ]
    return jsonify(result)


@gdp_bp.route('/compare')
def api_compare():
    """Compare GDP per capita between two countries across all years."""
    country1 = request.args.get('country1')
    country2 = request.args.get('country2')

    if not country1 or not country2:
        return jsonify(error_response("Both countries must be provided")), 400

    df = data.gdp
    year_columns = data.gdp_year_columns

    country1_data = df[df['Country Name'] == country1]
    country2_data = df[df['Country Name'] == country2]

    if country1_data.empty or country2_data.empty:
        return jsonify(error_response("One or both countries not found")), 404

    result = {
        "years": year_columns,
        "country1": {
            "name": country1,
            "data": [
                round(country1_data[year].iloc[0], 2)
                if not country1_data[year].isna().iloc[0] else None
                for year in year_columns
            ]
        },
        "country2": {
            "name": country2,
            "data": [
                round(country2_data[year].iloc[0], 2)
                if not country2_data[year].isna().iloc[0] else None
                for year in year_columns
            ]
        }
    }

    return jsonify(result)
