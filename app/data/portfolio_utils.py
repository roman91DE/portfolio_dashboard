import json
from pathlib import Path
from typing import Dict, List, Union

import matplotlib.pyplot as plt
import pandas as pd

from app.data.fetch_data import fetch_stock_data


def create_portfolio_dataframe(
    portfolio_data: List[Dict[str, Union[str, int, float]]]
) -> pd.DataFrame:
    df = pd.DataFrame(portfolio_data)
    if not df.empty and "Total Value" not in df.columns:
        df["Total Value"] = df["Shares"] * df["Latest Close"]
    return df


def fetch_portfolio_data(
    symbols: List[str], shares: List[int], api_key: str
) -> pd.DataFrame:
    portfolio_data = []
    for symbol, share_count in zip(symbols, shares):
        if symbol and share_count:
            normalized_symbol = symbol.strip().upper()
            if not normalized_symbol.isalnum():
                portfolio_data.append(
                    {"Symbol": symbol.strip(), "Error": "Invalid symbol format"}
                )
                continue

            try:
                df, overview = fetch_stock_data(normalized_symbol, api_key)
                latest_data = df.iloc[0]
                latest_close = float(latest_data["close"])
                total_value = share_count * latest_close
                portfolio_data.append(
                    {
                        "Symbol": normalized_symbol,
                        "Name": overview.get("Name", "N/A"),
                        "Asset Type": overview.get("AssetType", "N/A"),
                        "Sector": overview.get("Sector", "N/A"),
                        "Shares": share_count,
                        "Latest Close": latest_close,
                        "Total Value": total_value,
                    }
                )
            except ValueError as e:
                portfolio_data.append({"Symbol": normalized_symbol, "Error": str(e)})

    return pd.DataFrame(portfolio_data)


def create_asset_allocation_chart(df: pd.DataFrame) -> plt.Figure:
    if "Error" in df.columns:
        return plt.Figure()

    asset_allocation = df.groupby("Asset Type")["Total Value"].sum().reset_index()

    fig, ax = plt.subplots()
    ax.pie(
        asset_allocation["Total Value"],
        labels=asset_allocation["Asset Type"],
        autopct="%1.1f%%",
        startangle=90,
    )
    ax.axis("equal")
    plt.title("Asset Allocation")
    return fig


def create_sector_breakdown_chart(df: pd.DataFrame) -> plt.Figure:
    if "Error" in df.columns:
        return plt.Figure()

    sector_allocation = df.groupby("Sector")["Total Value"].sum().reset_index()

    fig, ax = plt.subplots()
    ax.pie(
        sector_allocation["Total Value"],
        labels=sector_allocation["Sector"],
        autopct="%1.1f%%",
        startangle=90,
    )
    ax.axis("equal")
    plt.title("Sector Breakdown")
    return fig


def calculate_portfolio_metrics(df: pd.DataFrame) -> pd.DataFrame:
    total_value = df["Total Value"].sum()

    metrics = {
        "Total Portfolio Value": total_value,
        "Number of Assets": len(df),
        "Average Asset Value": total_value / len(df) if len(df) > 0 else 0,
        "Highest Value Asset": (
            df.loc[df["Total Value"].idxmax(), "Symbol"] if not df.empty else "N/A"
        ),
        "Lowest Value Asset": (
            df.loc[df["Total Value"].idxmin(), "Symbol"] if not df.empty else "N/A"
        ),
    }

    return pd.DataFrame(list(metrics.items()), columns=["Metric", "Value"])


def create_portfolio_performance_chart(portfolio_data):
    all_data = pd.DataFrame()
    total_value = pd.Series(dtype=float)

    for symbol, data in portfolio_data.items():
        with open(Path(f"logs/ts_data_{symbol}.json")) as f:
            stock_data = json.load(f)

        df = pd.DataFrame(stock_data["Time Series (Daily)"]).T
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        close_prices = df["4. close"].astype(float) * data["shares"]
        all_data[symbol] = close_prices

        if total_value.empty:
            total_value = close_prices
        else:
            total_value = total_value.add(close_prices, fill_value=0)

    all_data["Total Portfolio"] = total_value

    fig, ax = plt.subplots(figsize=(12, 6))
    for column in all_data.columns:
        if column == "Total Portfolio":
            ax.plot(
                all_data.index,
                all_data[column],
                label=column,
                linewidth=3,
                color="black",
            )
        else:
            ax.plot(all_data.index, all_data[column], label=column)

    ax.set_title("Portfolio Performance Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Value ($)")
    ax.legend(loc="upper left", bbox_to_anchor=(1, 1))
    ax.grid(True)
    plt.tight_layout()

    return fig
