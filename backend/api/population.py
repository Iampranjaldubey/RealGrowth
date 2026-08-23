"""Population API Blueprint."""
from flask import Blueprint, request, jsonify
from services.data_loader import data
from utils.validators import validate_country, error_response

population_bp = Blueprint('population', __name__, url_prefix='/api/population')


@population_bp.route('/', methods=['GET'])
def population_data():
    """Get rural and urban population for a country in a specific year."""
    year = request.args.get('year')
    country = request.args.get('country')

    if not year or not country:
        return jsonify(error_response("Missing 'year' or 'country' parameter")), 400

    try:
        df_rural = data.rural_pop
        df_urban = data.urban_pop

        df_rural[year] = df_rural[year].replace({',': ''}, regex=True).astype(float)
        df_urban[year] = df_urban[year].replace({',': ''}, regex=True).astype(float)

        if country not in df_rural['Country Name'].values:
            return jsonify(error_response(f'Country "{country}" not found')), 404

        if year not in df_rural.columns:
            return jsonify(error_response(f'Year "{year}" not found')), 404

        rural_value = float(df_rural.loc[df_rural['Country Name'] == country, year].values[0])
        urban_value = float(df_urban.loc[df_urban['Country Name'] == country, year].values[0])

        return jsonify({'rural': rural_value, 'urban': urban_value})

    except Exception as e:
        print(f"Population Error: {e}")
        return jsonify(error_response("Unexpected error occurred")), 500


@population_bp.route('/line', methods=['GET'])
def get_line_chart_data():
    """Get population trend data over all years for a country."""
    country = request.args.get('country')
    if not country:
        return jsonify(error_response("Missing 'country' parameter")), 400

    try:
        df_rural = data.rural_pop
        df_urban = data.urban_pop

        if country not in df_rural['Country Name'].values:
            return jsonify(error_response(f'Country "{country}" not found')), 404

        rural_data = df_rural.loc[df_rural['Country Name'] == country].drop(
            columns=['Country Name']
        ).iloc[0].to_dict()
        urban_data = df_urban.loc[df_urban['Country Name'] == country].drop(
            columns=['Country Name']
        ).iloc[0].to_dict()

        def clean_value(val):
            if isinstance(val, str):
                return float(val.replace(',', ''))
            return float(val)

        rural_data = {year: clean_value(value) for year, value in rural_data.items()}
        urban_data = {year: clean_value(value) for year, value in urban_data.items()}

        return jsonify({
            'rural_population': rural_data,
            'urban_population': urban_data
        })
    except Exception as e:
        print(f"Population Line Error: {e}")
        return jsonify(error_response("Unexpected error occurred")), 500


@population_bp.route('/metadata')
def get_population_metadata():
    """Get list of available countries and years."""
    df_rural = data.rural_pop
    countries = df_rural['Country Name'].dropna().unique().tolist()
    years = [col for col in df_rural.columns if col != 'Country Name']
    return jsonify({'countries': countries, 'years': years})
