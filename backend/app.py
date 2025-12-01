from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import json
import os

app = Flask(__name__)
CORS(app)  

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

df_gdp = pd.read_csv( 'GDP_per_capita.csv', on_bad_lines='skip')
df_inflation = pd.read_csv( 'filled_Inflation_Rate.csv')
df_food = pd.read_csv('filled_healthy_diet_cost.csv')
df_rural_pop = pd.read_csv( 'rural_population.csv')
df_urban_pop = pd.read_csv('urban_population.csv')
df_rural_pct_change = pd.read_csv('rural_pop_percent_change.csv')
df_urban_pct_change = pd.read_csv('urban_pop_percent_change.csv')
df_wage = pd.read_csv('avg_wage.csv')
df_debt = pd.read_csv( 'filled_debt_to_gdp_ratio.csv')
df_real_growth = pd.read_csv('real_growth.csv')

# Clean and prepare data
df_gdp['Population'] = pd.to_numeric(df_gdp['Population'], errors='coerce')
gdp_year_columns = [col for col in df_gdp.columns if col.isdigit()]
for col in gdp_year_columns:
    df_gdp[col] = pd.to_numeric(df_gdp[col], errors='coerce')

for df in [df_rural_pop, df_urban_pop, df_rural_pct_change, df_urban_pct_change]:
    df['Country Name'] = df['Country Name'].str.strip()
    df.columns = df.columns.str.strip()

df_real_growth.columns = df_real_growth.columns.str.strip()
df_debt.columns = df_debt.columns.str.strip()

# Prepare inflation data
countries_inflation = df_inflation['Country'].tolist()
inflation_data = {}
for country in countries_inflation:
    inflation_data[country] = df_inflation.loc[df_inflation['Country'] == country].drop('Country', axis=1).values.flatten().tolist()[0:15]

# API routes only - No HTML serving

# GDP API routes
@app.route('/api/gdp/data', methods=['GET', 'POST'])
def gdp_data():
    selected_year = request.args.get('year', '2023')
    selected_pop = int(request.args.get('population', 0))
    
    filtered = df_gdp[df_gdp['Population'] >= selected_pop].copy()
    if selected_year in df_gdp.columns:
        filtered['gdp_per_capita'] = filtered[selected_year]
        top10 = filtered.sort_values(by='gdp_per_capita', ascending=False).head(10)
        chart_labels = list(top10['Country Name'])
        chart_data = list(round(top10['gdp_per_capita'], 2))
    else:
        chart_labels = []
        chart_data = []
    
    return jsonify({
        'years': gdp_year_columns,
        'selected_year': selected_year,
        'selected_pop': selected_pop,
        'chart_labels': chart_labels,
        'chart_data': chart_data
    })

@app.route('/api/gdp/countries')
def gdp_countries():
    countries = sorted(df_gdp['Country Name'].dropna().unique().tolist())
    return jsonify(countries)

@app.route('/api/gdp')
def api_gdp():
    year = request.args.get('year')
    min_population = int(request.args.get('min_population', 0))
    if year not in df_gdp.columns: return jsonify([])
    filtered = df_gdp[df_gdp['Population'] >= min_population].copy()
    filtered['gdp_per_capita'] = filtered[year]
    top10 = filtered.sort_values(by='gdp_per_capita', ascending=False).head(10)
    result = [{"country": row['Country Name'], "gdp_per_capita": round(row['gdp_per_capita'], 2)} for _, row in top10.iterrows()]
    return jsonify(result)

@app.route('/api/gdp/compare')
def api_compare():
    country1 = request.args.get('country1')
    country2 = request.args.get('country2')
    
    if not country1 or not country2:
        return jsonify({"error": "Both countries must be provided"})
    
    # Filter data for the two countries
    country1_data = df_gdp[df_gdp['Country Name'] == country1]
    country2_data = df_gdp[df_gdp['Country Name'] == country2]
    
    if country1_data.empty or country2_data.empty:
        return jsonify({"error": "One or both countries not found"})
    
    # Get GDP data for all years
    result = {
        "years": gdp_year_columns,
        "country1": {
            "name": country1,
            "data": [round(country1_data[year].iloc[0], 2) if not country1_data[year].isna().iloc[0] else None for year in gdp_year_columns]
        },
        "country2": {
            "name": country2,
            "data": [round(country2_data[year].iloc[0], 2) if not country2_data[year].isna().iloc[0] else None for year in gdp_year_columns]
        }
    }
    
    return jsonify(result)

# Inflation API routes
@app.route('/api/inflation/<country>')
def get_inflation(country):
    if country in inflation_data:
        return jsonify({'country': country, 'inflation': inflation_data[country]})
    return jsonify({'error': 'Country not found'}), 404

@app.route('/api/inflation/countries')
def get_inflation_countries():
    return jsonify({'countries': countries_inflation})

# Food price API routes
@app.route('/api/food/countries')
def food_countries():
    return jsonify(df_food['Entity'].dropna().unique().tolist())

@app.route('/api/food/histogram')
def food_histogram_data():
    c1 = request.args.get('country1')
    c2 = request.args.get('country2')
    selected = df_food[df_food['Entity'].isin([c1, c2])]
    food_year_cols = [col for col in df_food.columns if col.isdigit()]
    recent_years = food_year_cols[-5:]
    result = []
    for year in recent_years:
        row = {'Year': year}
        for _, r in selected.iterrows():
            row[r['Entity']] = r[year]
        result.append(row)
    return jsonify(result)

@app.route('/api/food/line')
def food_line_data():
    c1 = request.args.get('country1')
    c2 = request.args.get('country2')
    selected = df_food[df_food['Entity'].isin([c1, c2])]
    food_year_cols = [col for col in df_food.columns if col.isdigit()]
    recent_years = food_year_cols[-5:]
    result = []
    for year in recent_years:
        row = {'Year': year}
        for _, r in selected.iterrows():
            row[r['Entity']] = r[year]
        result.append(row)
    return jsonify(result)

# Population API routes
@app.route('/api/population', methods=['GET'])
def population_data():
    year = request.args.get('year')
    country = request.args.get('country')

    if not year or not country:
        return jsonify({'error': 'Missing year or country'}), 400

    try:
        df_rural_pop[year] = df_rural_pop[year].replace({',': ''}, regex=True).astype(float)
        df_urban_pop[year] = df_urban_pop[year].replace({',': ''}, regex=True).astype(float)

        if country not in df_rural_pop['Country Name'].values:
            return jsonify({'error': f'Country "{country}" not found'}), 404

        if year not in df_rural_pop.columns:
            return jsonify({'error': f'Year "{year}" not found'}), 404

        rural_value = float(df_rural_pop.loc[df_rural_pop['Country Name'] == country, year].values[0])
        urban_value = float(df_urban_pop.loc[df_urban_pop['Country Name'] == country, year].values[0])

        return jsonify({
            'rural': rural_value,
            'urban': urban_value
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Unexpected error occurred'}), 500

@app.route('/api/population/line', methods=['GET'])
def get_line_chart_data():
    country = request.args.get('country')
    if not country:
        return jsonify({'error': 'Missing country'}), 400
    try:
        if country not in df_rural_pop['Country Name'].values:
            return jsonify({'error': f'Country "{country}" not found'}), 404

        rural_data = df_rural_pop.loc[df_rural_pop['Country Name'] == country].drop(columns=['Country Name']).iloc[0].to_dict()
        urban_data = df_urban_pop.loc[df_urban_pop['Country Name'] == country].drop(columns=['Country Name']).iloc[0].to_dict()

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
        print("Error:", e)
        return jsonify({'error': 'Unexpected error occurred'}), 500

@app.route('/api/population/metadata')
def get_population_metadata():
    countries = df_rural_pop['Country Name'].dropna().unique().tolist()
    years = [col for col in df_rural_pop.columns if col != 'Country Name']
    return jsonify({'countries': countries, 'years': years})

# Wage API routes
@app.route("/api/wages/countries")
def get_wage_countries():
    countries = df_wage["Country name"].dropna().unique().tolist()
    return jsonify(countries)

@app.route("/api/wages/<country>")
def get_wages(country):
    row = df_wage[df_wage["Country name"] == country]
    if row.empty:
        return jsonify({"error": "Country not found"}), 404
    wage_year_columns = [col for col in df_wage.columns if col.isdigit()]
    wages = row[wage_year_columns].iloc[0].to_dict()
    clean_wages = {year: float(wages[year]) for year in wages if pd.notna(wages[year])}
    return jsonify(clean_wages)

# Debt API routes
@app.route('/api/debt')
def get_debt_data():
    year = request.args.get('year', '2022')  
    if year not in df_debt.columns:
        return jsonify([])  
    data = [{"country": row['Country Name'], "value": row[year]} for _, row in df_debt.iterrows()]
    return jsonify(data)

# Real growth API routes
@app.route('/api/growth/countries')
def get_growth_countries():
    return jsonify(df_real_growth['Country name'].dropna().unique().tolist())

@app.route('/api/growth/<country>')
def get_real_growth(country):
    row = df_real_growth[df_real_growth['Country name'] == country]
    if row.empty:
        return jsonify({"error": "Country not found"}), 404

    data = row.iloc[0, 1:]  # exclude 'Country name'
    years = data.index.tolist()
    values = data.values.tolist()

    return jsonify({"years": years, "values": values})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
