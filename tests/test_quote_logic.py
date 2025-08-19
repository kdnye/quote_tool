import pandas as pd
import pytest
from quote.logic_hotshot import calculate_hotshot_quote
from quote.logic_air import calculate_air_quote


def test_calculate_hotshot_quote(monkeypatch):
    # Prepare a simple rates table with a zone X entry
    rates_df = pd.DataFrame({
        'MILES': [100, 200],
        'ZONE': ['A', 'X'],
        'PER LB': [2.0, 0.0],
        'FUEL': [0.1, 0.2],
        'MIN': [50, 1.5],  # For zone X this represents rate per mile
        'WEIGHT BREAK': [100, 200],
    })

    # Stub the distance call to avoid external API usage
    monkeypatch.setattr('quote.logic_hotshot.get_distance_miles', lambda o, d: 150)

    result = calculate_hotshot_quote('12345', '67890', 120, 10, rates_df)

    assert result['zone'] == 'X'
    assert result['miles'] == 150
    # 150 miles * $1.5 per mile * (1 + 0.2 fuel) + $10 accessorials = $280
    assert result['quote_total'] == pytest.approx(280.0)


def test_calculate_air_quote():
    workbook = {
        'ZIP CODE ZONES': pd.DataFrame({
            'ZIPCODE': ['12345', '67890'],
            'DEST ZONE': [1, 2],
            'BEYOND': ['NO', 'B1'],
        }),
        'COST ZONE TABLE': pd.DataFrame({
            'CONCATENATE': ['12'],
            'COST ZONE': ['C1'],
        }),
        'Air Cost Zone': pd.DataFrame({
            'ZONE': ['C1'],
            'MIN': [100],
            'PER LB': ['$1.00'],
            'WEIGHT BREAK': [50],
        }),
        'Beyond Price': pd.DataFrame({
            'ZONE': ['B1'],
            'RATE': ['$20'],
        }),
    }

    result = calculate_air_quote('12345', '67890', 60, 10, workbook)

    assert result['zone'] == 12
    assert result['beyond_total'] == 20
    # Base 110 + beyond 20 + accessorial 10 = 140
    assert result['quote_total'] == pytest.approx(140.0)


def test_calculate_air_quote_missing_zip():
    workbook = {
        'ZIP CODE ZONES': pd.DataFrame({
            'ZIPCODE': ['67890'],
            'DEST ZONE': [2],
            'BEYOND': ['B1'],
        }),
        'COST ZONE TABLE': pd.DataFrame({
            'CONCATENATE': ['12'],
            'COST ZONE': ['C1'],
        }),
        'Air Cost Zone': pd.DataFrame({
            'ZONE': ['C1'],
            'MIN': [100],
            'PER LB': ['$1.00'],
            'WEIGHT BREAK': [50],
        }),
        'Beyond Price': pd.DataFrame({
            'ZONE': ['B1'],
            'RATE': ['$20'],
        }),
    }

    result = calculate_air_quote('12345', '67890', 60, 10, workbook)

    assert result['quote_total'] == 0
    assert 'error' in result and 'Origin ZIP code 12345 not found' in result['error']


def test_calculate_air_quote_missing_destination():
    workbook = {
        'ZIP CODE ZONES': pd.DataFrame({
            'ZIPCODE': ['12345'],
            'DEST ZONE': [1],
            'BEYOND': ['NO'],
        }),
        'COST ZONE TABLE': pd.DataFrame({
            'CONCATENATE': ['11'],
            'COST ZONE': ['C1'],
        }),
        'Air Cost Zone': pd.DataFrame({
            'ZONE': ['C1'],
            'MIN': [100],
            'PER LB': ['$1.00'],
            'WEIGHT BREAK': [50],
        }),
        'Beyond Price': pd.DataFrame({
            'ZONE': ['B1'],
            'RATE': ['$20'],
        }),
    }

    result = calculate_air_quote('12345', '67890', 60, 10, workbook)

    assert result['quote_total'] == 0
    assert 'error' in result and 'Destination ZIP code 67890 not found' in result['error']
