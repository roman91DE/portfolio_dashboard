import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests


class APILimitReachedException(Exception):
    pass


def fetch_stock_data(symbol: str, api_key: str) -> tuple[pd.DataFrame, dict]:
    # Create a database connection
    db_path = Path("database") / "stock_data.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables if they don't exist
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS time_series
                      (symbol TEXT, date TEXT, data TEXT, PRIMARY KEY (symbol, date))"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS overview
                      (symbol TEXT PRIMARY KEY, data TEXT, last_updated TEXT)"""
    )
    conn.commit()

    # Check if we have recent data in the database
    today = datetime.now().date()
    cursor.execute(
        "SELECT date, data FROM time_series WHERE symbol = ? ORDER BY date DESC LIMIT 1",
        (symbol,),
    )
    result = cursor.fetchone()

    if result and (today - datetime.strptime(result[0], "%Y-%m-%d").date()).days < 1:
        # Use cached time series data
        ts_data = json.loads(result[1])
    else:
        # Fetch new time series data from API
        ts_data = fetch_time_series_from_api(symbol, api_key)
        # Store in database
        cursor.execute(
            "INSERT OR REPLACE INTO time_series (symbol, date, data) VALUES (?, ?, ?)",
            (symbol, today.isoformat(), json.dumps(ts_data)),
        )
        conn.commit()

    # Check if we have recent overview data
    cursor.execute(
        "SELECT data, last_updated FROM overview WHERE symbol = ?", (symbol,)
    )
    result = cursor.fetchone()

    if (
        result and (today - datetime.strptime(result[1], "%Y-%m-%d").date()).days < 7
    ):  # Update weekly
        # Use cached overview data
        overview_data = json.loads(result[0])
    else:
        # Fetch new overview data from API
        overview_data = fetch_overview_from_api(symbol, api_key)
        # Store in database
        cursor.execute(
            "INSERT OR REPLACE INTO overview (symbol, data, last_updated) VALUES (?, ?, ?)",
            (symbol, json.dumps(overview_data), today.isoformat()),
        )
        conn.commit()

    conn.close()

    # Process data and return as before
    if "Time Series (Daily)" in ts_data:
        df = pd.DataFrame(ts_data["Time Series (Daily)"]).T
        df.columns = ["open", "high", "low", "close", "volume"]
        df.index = pd.to_datetime(df.index)

        # Extract relevant information from overview data
        overview_info = {
            "AssetType": overview_data.get("AssetType", "Unknown"),
            "Sector": overview_data.get("Sector", "Unknown"),
            "Industry": overview_data.get("Industry", "Unknown"),
            "Name": overview_data.get("Name", symbol),
        }

        return df, overview_info
    elif "Error Message" in ts_data:
        raise ValueError(f"Alpha Vantage API error: {ts_data['Error Message']}")
    else:
        raise ValueError("Unexpected response format from Alpha Vantage API")


def fetch_time_series_from_api(symbol: str, api_key: str) -> dict:
    ts_url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}"
    ts_response = requests.get(ts_url)
    ts_data = ts_response.json()

    # Log time series data
    log_path = Path("logs") / f"ts_data_{symbol}.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(ts_data, indent=2))

    if "Information" in ts_data and "standard API rate limit" in ts_data["Information"]:
        raise APILimitReachedException(
            "Alpha Vantage API daily limit reached. Please try again tomorrow or upgrade to a premium plan."
        )

    return ts_data


def fetch_overview_from_api(symbol: str, api_key: str) -> dict:
    overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={api_key}"
    overview_response = requests.get(overview_url)
    overview_data = overview_response.json()

    # Log overview data
    log_path = Path("logs") / f"overview_data_{symbol}.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(overview_data, indent=2))

    # Check for API limit reached
    if "Information" in overview_data and "standard API rate limit" in overview_data["Information"]:
        raise APILimitReachedException(
            "Alpha Vantage API daily limit reached. Please try again tomorrow or upgrade to a premium plan."
        )

    return overview_data
