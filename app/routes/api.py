"""
API v1 Blueprint — all REST endpoints for the economic dashboard.

Every route returns a consistent JSON shape:
  Success: {"status": "success", "data": ...}
  Error:   {"status": "error",   "message": "..."}
"""

from flask import Blueprint, request, current_app

from app.utils.helpers import (
    success_response,
    error_response,
    validate_year,
    validate_country,
)

api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def _svc():
    """Shortcut to retrieve the DataService from the current app."""
    return current_app.config["DATA_SERVICE"]


# ================================================================== #
#                            GDP ROUTES                                #
# ================================================================== #

@api_v1.route("/gdp/years")
def gdp_years():
    """Return all available GDP year columns."""
    return success_response(_svc().get_gdp_years())


@api_v1.route("/gdp/countries")
def gdp_countries():
    """Return sorted list of countries with GDP data."""
    return success_response(_svc().get_gdp_countries())


@api_v1.route("/gdp/top")
def gdp_top():
    """
    Top 10 countries by GDP per capita.
    Query params: year (required), min_population (optional, default 0).
    """
    year = request.args.get("year", "2023")
    try:
        min_pop = int(request.args.get("min_population", 0))
    except (ValueError, TypeError):
        return error_response("min_population must be an integer")

    data = _svc().get_gdp_top10(year, min_pop)
    return success_response(data)


@api_v1.route("/gdp/compare")
def gdp_compare():
    """
    Compare GDP per capita of two countries over time.
    Query params: country1, country2 (both required).
    """
    country1 = request.args.get("country1")
    country2 = request.args.get("country2")

    if not country1 or not country2:
        return error_response("Both 'country1' and 'country2' are required")

    data = _svc().get_gdp_compare(country1, country2)
    if data is None:
        return error_response("One or both countries not found", 404)

    return success_response(data)


# ================================================================== #
#                        INFLATION ROUTES                              #
# ================================================================== #

@api_v1.route("/inflation/countries")
def inflation_countries():
    """Return list of countries with inflation data."""
    return success_response(_svc().get_inflation_countries())


@api_v1.route("/inflation/<country>")
def inflation_data(country):
    """Get inflation rates for a specific country."""
    data = _svc().get_inflation(country)
    if data is None:
        return error_response(f"Country '{country}' not found", 404)
    return success_response(data)


# ================================================================== #
#                       FOOD PRICE ROUTES                              #
# ================================================================== #

@api_v1.route("/food/countries")
def food_countries():
    """Return list of countries with food price data."""
    return success_response(_svc().get_food_countries())


@api_v1.route("/food/compare")
def food_compare():
    """
    Compare healthy diet costs between two countries.
    Query params: country1, country2 (both required).
    """
    country1 = request.args.get("country1")
    country2 = request.args.get("country2")

    if not country1 or not country2:
        return error_response("Both 'country1' and 'country2' are required")

    data = _svc().get_food_compare(country1, country2)
    return success_response(data)


# ================================================================== #
#                      POPULATION ROUTES                               #
# ================================================================== #

@api_v1.route("/population/metadata")
def population_metadata():
    """Return available countries and years for population data."""
    return success_response(_svc().get_population_metadata())


@api_v1.route("/population/distribution")
def population_distribution():
    """
    Urban vs rural population for a specific country and year.
    Query params: country (required), year (required).
    """
    country = request.args.get("country")
    year = request.args.get("year")

    if not country or not year:
        return error_response("Both 'country' and 'year' are required")

    data = _svc().get_population_distribution(country, year)
    if data is None:
        return error_response(
            f"Data not found for country='{country}', year='{year}'", 404
        )
    return success_response(data)


@api_v1.route("/population/trend")
def population_trend():
    """
    Population trend over all years for a specific country.
    Query params: country (required).
    """
    country = request.args.get("country")
    if not country:
        return error_response("'country' parameter is required")

    data = _svc().get_population_trend(country)
    if data is None:
        return error_response(f"Country '{country}' not found", 404)
    return success_response(data)


# ================================================================== #
#                         WAGES ROUTES                                 #
# ================================================================== #

@api_v1.route("/wages/countries")
def wage_countries():
    """Return list of countries with wage data."""
    return success_response(_svc().get_wage_countries())


@api_v1.route("/wages/<country>")
def wage_data(country):
    """Get average wage data for a specific country."""
    data = _svc().get_wages(country)
    if data is None:
        return error_response(f"Country '{country}' not found", 404)
    return success_response(data)


# ================================================================== #
#                          DEBT ROUTES                                 #
# ================================================================== #

@api_v1.route("/debt")
def debt_data():
    """
    Get debt-to-GDP ratio for all countries for a given year.
    Query params: year (optional, default "2022").
    """
    year = request.args.get("year", "2022")
    data = _svc().get_debt_data(year)
    return success_response(data)


# ================================================================== #
#                       REAL GROWTH ROUTES                             #
# ================================================================== #

@api_v1.route("/growth/countries")
def growth_countries():
    """Return list of countries with real growth data."""
    return success_response(_svc().get_growth_countries())


@api_v1.route("/growth/<country>")
def growth_data(country):
    """Get real economic growth rates for a specific country."""
    data = _svc().get_growth(country)
    if data is None:
        return error_response(f"Country '{country}' not found", 404)
    return success_response(data)
