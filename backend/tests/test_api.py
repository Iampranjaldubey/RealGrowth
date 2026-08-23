import pytest
import sys
import os

# Add the backend directory to the path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

@pytest.fixture
def client():
    app = create_app('development')
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    """Test the root endpoint."""
    rv = client.get('/')
    assert rv.status_code == 200
    json_data = rv.get_json()
    assert json_data['status'] == 'running'
    assert 'RealGrowth API' in json_data['name']

def test_gdp_countries(client):
    """Test the GDP countries endpoint."""
    rv = client.get('/api/gdp/countries')
    assert rv.status_code == 200
    json_data = rv.get_json()
    assert isinstance(json_data, list)
    assert len(json_data) > 0

def test_correlation_indicators(client):
    """Test the new Correlation Explorer endpoint."""
    rv = client.get('/api/correlation/indicators')
    assert rv.status_code == 200
    json_data = rv.get_json()
    assert 'indicators' in json_data
    assert len(json_data['indicators']) >= 5
