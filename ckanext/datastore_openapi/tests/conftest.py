import pytest


@pytest.fixture
def introspection_result():
    return {
        "fields": [
            {
                "id": "_id",
                "type": "int4",
                "sample": 1,
                "samples": [1, 2, 3, 4, 5],
            },
            {
                "id": "bidding_zone",
                "type": "text",
                "sample": "SE1",
                "samples": ["SE1", "SE2", "SE3", "SE4"],
                "isEnum": True,
                "enumValues": ["SE1", "SE2", "SE3", "SE4"],
                "distinctCount": 4,
            },
            {
                "id": "volume_mw",
                "type": "float8",
                "sample": 1234.56,
                "samples": [1234.56, 2345.67, 3456.78],
                "min": 0.0,
                "max": 9999.99,
            },
            {
                "id": "timestamp",
                "type": "timestamp",
                "sample": "2025-01-15T10:30:00",
                "samples": ["2025-01-15T10:30:00", "2025-01-15T11:00:00"],
                "min": "2020-01-01T00:00:00",
                "max": "2025-12-31T23:59:59",
            },
            {
                "id": "is_active",
                "type": "bool",
                "sample": True,
                "samples": [True, False, True],
            },
            {
                "id": "tags",
                "type": "_text",
                "sample": ["energy", "market"],
                "samples": [["energy", "market"], ["wind", "solar"]],
            },
            {
                "id": "description",
                "type": "text",
                "sample": "A sample description",
                "samples": ["A sample description", "Another description"],
                "distinctCount": 50,
                "isEnum": False,
            },
        ],
        "totalRecords": 15432,
        "sampleRecords": [
            {
                "_id": 1,
                "bidding_zone": "SE1",
                "volume_mw": 1234.56,
                "timestamp": "2025-01-15T10:30:00",
                "is_active": True,
                "tags": ["energy", "market"],
                "description": "A sample description",
            },
        ],
    }


@pytest.fixture
def sample_dataset():
    return {
        "id": "ds-001",
        "name": "energy-market",
        "title": "Energy Market Data",
        "resources": [
            {
                "id": "res-001",
                "name": "Hourly Prices",
                "datastore_active": True,
            },
            {
                "id": "res-002",
                "name": "Static PDF",
                "datastore_active": False,
            },
            {
                "id": "res-003",
                "name": "Daily Summary",
                "datastore_active": True,
            },
        ],
    }


@pytest.fixture
def pg_stats_result():
    return {
        "bidding_zone": {
            "n_distinct": 4,
            "most_common_vals": ["SE1", "SE2", "SE3", "SE4"],
            "histogram_bounds": [],
        },
        "volume_mw": {
            "n_distinct": -0.95,
            "most_common_vals": [],
            "histogram_bounds": ["0.0", "2500.0", "5000.0", "7500.0", "9999.99"],
        },
        "timestamp": {
            "n_distinct": -0.99,
            "most_common_vals": [],
            "histogram_bounds": ["2020-01-01", "2022-06-15", "2025-12-31"],
        },
        "description": {
            "n_distinct": 50,
            "most_common_vals": [],
            "histogram_bounds": [],
        },
    }
