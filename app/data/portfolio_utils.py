import json
from pathlib import Path
from typing import Dict, List, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import squarify

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

                # Calculate 52-week change
                if len(df) >= 252:  # Approximately 252 trading days in a year
                    year_ago_price = (
                        df["close"].astype(float).iloc[min(251, len(df) - 1)]
                    )
                    week_52_change = (latest_close - year_ago_price) / year_ago_price
                else:
                    # If we don't have a full year of data, calculate change from the oldest available data point
                    oldest_price = df["close"].astype(float).iloc[-1]
                    week_52_change = (latest_close - oldest_price) / oldest_price

                week_52_change = (
                    f"{week_52_change:.4f}"  # Convert to string with 4 decimal places
                )

                portfolio_data.append(
                    {
                        "Symbol": normalized_symbol,
                        "Name": overview.get("Name", "N/A"),
                        "Asset Type": overview.get("AssetType", "N/A"),
                        "Sector": overview.get("Sector", "N/A"),
                        "Industry": overview.get("Industry", "N/A"),
                        "Shares": share_count,
                        "Latest Close": latest_close,
                        "Total Value": total_value,
                        "Market Cap": overview.get("MarketCapitalization", "N/A"),
                        "PE Ratio": overview.get("PERatio", "N/A"),
                        "PEG Ratio": overview.get("PEGRatio", "N/A"),
                        "Book Value": overview.get("BookValue", "N/A"),
                        "Dividend Yield": overview.get("DividendYield", "N/A"),
                        "EPS": overview.get("EPS", "N/A"),
                        "Beta": overview.get("Beta", "N/A"),
                        "52 Week High": overview.get("52WeekHigh", "N/A"),
                        "52 Week Low": overview.get("52WeekLow", "N/A"),
                        "50 Day MA": overview.get("50DayMovingAverage", "N/A"),
                        "200 Day MA": overview.get("200DayMovingAverage", "N/A"),
                        "52WeekChange": week_52_change,
                    }
                )
            except ValueError as e:
                portfolio_data.append({"Symbol": normalized_symbol, "Error": str(e)})

    return pd.DataFrame(portfolio_data)


def create_asset_allocation_chart(df: pd.DataFrame) -> plt.Figure:
    if "Error" in df.columns:
        return plt.Figure()

    # Sort the dataframe by Total Value in descending order
    df_sorted = df.sort_values("Total Value", ascending=False)

    # Create lists for treemap input
    sizes = df_sorted["Total Value"].tolist()
    labels = [
        f"{row['Symbol']}\n${row['Total Value']:,.0f}"
        for _, row in df_sorted.iterrows()
    ]
    colors = plt.cm.viridis(np.linspace(0, 1, len(sizes)))

    # Create the treemap
    fig, ax = plt.subplots(figsize=(12, 8))
    squarify.plot(
        sizes=sizes, label=labels, color=colors, alpha=0.8, text_kwargs={"fontsize": 8}
    )

    plt.title("Portfolio Composition", fontsize=16)
    plt.axis("off")

    # Add a color bar to represent value
    sm = plt.cm.ScalarMappable(
        cmap=plt.cm.viridis, norm=plt.Normalize(vmin=min(sizes), vmax=max(sizes))
    )
    sm.set_array([])
    cbar = plt.colorbar(sm)
    cbar.set_label("Total Value ($)", rotation=270, labelpad=25)

    plt.tight_layout(pad=3.0, rect=[0, 0.05, 1, 0.95])
    return fig


def create_sector_breakdown_chart(df: pd.DataFrame) -> plt.Figure:
    if "Error" in df.columns:
        return plt.Figure()

    sector_allocation = (
        df.groupby("Sector")["Total Value"].sum().sort_values(ascending=True)
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(sector_allocation.index, sector_allocation.values)

    # Add value labels to the end of each bar
    for bar in bars:
        width = bar.get_width()
        ax.text(
            width,
            bar.get_y() + bar.get_height() / 2,
            f"${width:,.0f}",
            ha="left",
            va="center",
            fontweight="bold",
        )

    # Add percentage labels inside each bar
    total = sector_allocation.sum()
    for bar in bars:
        width = bar.get_width()
        percentage = (width / total) * 100
        ax.text(
            width / 2,
            bar.get_y() + bar.get_height() / 2,
            f"{percentage:.1f}%",
            ha="center",
            va="center",
            fontweight="bold",
            color="white",
        )

    ax.set_title("Sector Breakdown", fontsize=16)
    ax.set_xlabel("Total Value ($)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout(pad=3.0, rect=[0, 0.05, 1, 0.95])
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
        "Most Shares Held": (
            df.loc[df["Shares"].idxmax(), "Symbol"] if not df.empty else "N/A"
        ),
        "Least Shares Held": (
            df.loc[df["Shares"].idxmin(), "Symbol"] if not df.empty else "N/A"
        ),
        "Highest Price Asset": (
            df.loc[df["Latest Close"].idxmax(), "Symbol"] if not df.empty else "N/A"
        ),
        "Lowest Price Asset": (
            df.loc[df["Latest Close"].idxmin(), "Symbol"] if not df.empty else "N/A"
        ),
        "Number of Sectors": (
            df["Sector"].nunique() if "Sector" in df.columns else "N/A"
        ),
        "Most Represented Sector": (
            df.groupby("Sector")["Total Value"].sum().idxmax()
            if "Sector" in df.columns
            else "N/A"
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
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize="small")
    ax.grid(True)
    plt.tight_layout(pad=3.0, rect=[0, 0.05, 1, 0.95])

    return fig


def create_risk_return_chart(df: pd.DataFrame) -> plt.Figure:
    if "Error" in df.columns:
        return plt.Figure()

    fig, ax = plt.subplots(figsize=(10, 6))

    print("Debug: DataFrame columns:", df.columns)
    print("Debug: Beta values:", df["Beta"])
    print("Debug: 52WeekChange values:", df["52WeekChange"])

    x = df["Beta"].apply(lambda x: float(x) if x not in ["N/A", None] else np.nan)
    y = (
        df["52WeekChange"].apply(
            lambda x: float(x) if x not in ["N/A", None] else np.nan
        )
        * 100
    )

    print("Debug: Converted x values:", x)
    print("Debug: Converted y values:", y)

    # Remove rows with NaN values
    valid_data = df[~(np.isnan(x) | np.isnan(y))]
    x = x[~np.isnan(x) & ~np.isnan(y)]
    y = y[~np.isnan(x) & ~np.isnan(y)]

    print("Debug: Valid data points:", len(valid_data))

    if len(valid_data) == 0:
        ax.text(
            0.5,
            0.5,
            "No valid data points for Risk-Return chart",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        return fig

    size = valid_data["Total Value"] / valid_data["Total Value"].max() * 500

    scatter = ax.scatter(
        x, y, s=size, c=valid_data["Sector"].astype("category").cat.codes, alpha=0.6
    )

    for i, txt in enumerate(valid_data["Symbol"]):
        ax.annotate(txt, (x.iloc[i], y.iloc[i]))

    ax.set_xlabel("Beta (Risk)")
    ax.set_ylabel("52 Week Change (%)")
    ax.set_title("Risk-Return Analysis of Portfolio")
    plt.colorbar(scatter, label="Sector")

    plt.tight_layout(pad=3.0, rect=[0, 0.05, 1, 0.95])
    return fig
