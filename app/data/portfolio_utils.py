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
