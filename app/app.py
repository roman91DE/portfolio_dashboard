import os
from logging import getLogger
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from shiny import App, Inputs, Outputs, Session, render, ui

from app.data.fetch_data import fetch_stock_data
from app.data.portfolio_utils import create_portfolio_dataframe

# Load environment variables from .env file
load_dotenv(Path(".env"))
logger = getLogger(__name__)

# Get the API key from environment variables
API_KEY_ENV = os.getenv("ALPHA_VANTAGE_API_KEY")
if not API_KEY_ENV:
    raise ValueError("ALPHA_VANTAGE_API_KEY is not set")
API_KEY = API_KEY_ENV

# Define UI
app_ui = ui.page_fluid(
    ui.input_text_area(
        "tickers", "Enter Tickers/ISINs (comma-separated)", value="AAPL,GOOGL"
    ),
    ui.input_text_area(
        "shares", "Enter Number of Shares (comma-separated)", value="10,5"
    ),
    ui.input_action_button("fetch", "Fetch Data"),
    ui.output_table("portfolio_table"),
)


# Define server logic
def server(input: Inputs, output: Outputs, session: Session) -> None:
    @output
    @render.table
    def portfolio_table() -> pd.DataFrame:
        try:
            tickers = input.tickers().split(",")
            shares = list(map(int, input.shares().split(",")))

            if len(tickers) != len(shares):
                return pd.DataFrame(
                    {
                        "Error": [
                            "The number of tickers/ISINs must match the number of shares."
                        ]
                    }
                )

            portfolio_data = []
            for ticker, share in zip(tickers, shares):
                try:
                    df, overview = fetch_stock_data(ticker.strip(), API_KEY)
                    latest_data = df.iloc[0]
                    portfolio_data.append(
                        {
                            "Ticker/ISIN": ticker.strip(),
                            "Name": overview["Name"],
                            "Asset Type": overview["AssetType"],
                            "Sector": overview["Sector"],
                            "Shares": share,
                            "Latest Close": latest_data["close"],
                        }
                    )
                except ValueError as e:
                    logger.error(
                        f"Error processing Alpha Vantage data for {ticker}: {e}"
                    )
                    portfolio_data.append(
                        {"Ticker/ISIN": ticker.strip(), "Error": str(e)}
                    )

            return create_portfolio_dataframe(portfolio_data)
        except Exception as e:
            logger.error(f"Error in portfolio_table: {e}")
            return pd.DataFrame({"Error": [str(e)]})


# Create the Shiny app
app = App(app_ui, server)
