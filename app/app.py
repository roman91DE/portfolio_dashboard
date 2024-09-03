import os
from logging import getLogger
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv
from shiny import App, Inputs, Outputs, Session, reactive, render, ui

from app.data.portfolio_utils import (create_asset_allocation_chart,
                                      create_sector_breakdown_chart,
                                      fetch_portfolio_data, calculate_portfolio_metrics,
                                      create_portfolio_performance_chart)

# Load environment variables from .env file
load_dotenv(Path(".env"))
logger = getLogger(__name__)

# Get the API key from environment variables
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
if not API_KEY:
    raise ValueError("ALPHA_VANTAGE_API_KEY is not set")

# Define UI
app_ui = ui.page_fluid(
    ui.div(
        ui.h2("Portfolio Tracker"),
        ui.div(
            ui.row(
                ui.column(6, ui.input_text("symbol_0", "Stock Symbol", placeholder="e.g., AAPL")),
                ui.column(6, ui.input_numeric("shares_0", "Number of Shares", value=1, min=1)),
            ),
            id="input-container",
        ),
        ui.row(
            ui.column(3, ui.input_action_button("add_row", "Add Row", class_="btn-primary mt-2")),
            ui.column(3, ui.input_action_button("remove_row", "Remove Last Row", class_="btn-warning mt-2")),
            ui.column(3, ui.input_action_button("fetch", "Fetch Data", class_="btn-success mt-2")),
        ),
        ui.hr(),
        ui.row(
            ui.column(12, ui.output_table("portfolio_table")),
        ),
        ui.row(
            ui.column(12, ui.output_plot("portfolio_performance")),
        ),
        ui.row(
            ui.column(
                8,
                ui.row(
                    ui.column(6, ui.output_plot("asset_allocation_chart")),
                    ui.column(6, ui.output_plot("sector_breakdown_chart")),
                ),
            ),
            ui.column(4, ui.output_table("portfolio_metrics")),
        ),
    )
)


def server(input: Inputs, output: Outputs, session: Session):
    row_count = reactive.Value(1)
    portfolio_metrics_value = reactive.Value(None)  # Renamed from portfolio_metrics
    data_fetched = reactive.Value(None)
    portfolio_performance_chart = reactive.Value(None)

    @reactive.Effect
    @reactive.event(input.add_row)
    def add_input_row():
        current_count = row_count.get()
        ui.insert_ui(
            selector="#input-container",
            where="beforeEnd",
            ui=ui.row(
                ui.column(
                    6,
                    ui.input_text(
                        f"symbol_{current_count}",
                        "Stock Symbol",
                        placeholder="e.g., AAPL",
                    ),
                ),
                ui.column(
                    6,
                    ui.input_numeric(
                        f"shares_{current_count}", "Number of Shares", value=1, min=1
                    ),
                ),
            ),
        )
        row_count.set(current_count + 1)

    @reactive.Effect
    @reactive.event(input.remove_row)
    def remove_last_row():
        current_count = row_count.get()
        if current_count > 1:
            ui.remove_ui(selector=f"#input-container .row:last-child")
            row_count.set(current_count - 1)

    @reactive.Calc
    def get_portfolio_data():
        symbols = [input[f"symbol_{i}"]() for i in range(row_count.get())]
        shares = [input[f"shares_{i}"]() for i in range(row_count.get())]
        return symbols, shares

    @reactive.Effect
    @reactive.event(input.fetch)
    def fetch_data():
        symbols, shares = get_portfolio_data()
        data = fetch_portfolio_data(symbols, shares, API_KEY)
        data_fetched.set(data)
        metrics = calculate_portfolio_metrics(data)
        portfolio_metrics_value.set(metrics)
        
        # Create portfolio data dictionary for the performance chart
        portfolio_data = {symbol: {'shares': shares[i]} for i, symbol in enumerate(symbols)}
        
        # Create the portfolio performance chart
        performance_chart = create_portfolio_performance_chart(portfolio_data)
        portfolio_performance_chart.set(performance_chart)

    @output
    @render.table
    def portfolio_table():
        data = data_fetched.get()
        if data is None or data.empty:
            return pd.DataFrame({"Message": ["No data available. Please fetch data."]})
        return data

    @output
    @render.plot
    def asset_allocation_chart():
        data = data_fetched.get()
        if data is None or data.empty:
            return None
        fig = create_asset_allocation_chart(data)
        return fig
    
    @output
    @render.plot
    def sector_breakdown_chart():
        data = data_fetched.get()
        if data is None or data.empty:
            return None
        return create_sector_breakdown_chart(data)
    
    @output
    @render.table
    def portfolio_metrics():
        metrics = portfolio_metrics_value.get()  # Use the new name
        if metrics is None:
            return pd.DataFrame({"Message": ["No metrics available. Please fetch data."]})
        return metrics  # This should now be the DataFrame returned by calculate_portfolio_metrics

    @output
    @render.plot
    def portfolio_performance():
        chart = portfolio_performance_chart.get()
        if chart is None:
            return None
        return chart

# Create the Shiny app
app = App(app_ui, server)
