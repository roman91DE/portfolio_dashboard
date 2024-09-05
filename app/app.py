import os
from logging import getLogger
from pathlib import Path

import chardet
import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv
from shiny import App, Inputs, Outputs, Session, reactive, render, ui
from shiny.types import FileInfo

from app.data.portfolio_utils import (calculate_portfolio_metrics,
                                      create_portfolio_performance_chart,
                                      create_sector_breakdown_chart,
                                      create_risk_return_chart,
                                      fetch_portfolio_data)

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
        ui.navset_tab(
            ui.nav_panel(
                "Manual Input",
                ui.div(
                    ui.row(
                        ui.column(
                            6,
                            ui.input_text(
                                "symbol_0", "Stock Symbol", placeholder="e.g., AAPL"
                            ),
                        ),
                        ui.column(
                            6,
                            ui.input_numeric(
                                "shares_0", "Number of Shares", value=1, min=1
                            ),
                        ),
                    ),
                    id="input-container",
                ),
                ui.row(
                    ui.column(
                        3,
                        ui.input_action_button(
                            "add_row", "Add Row", class_="btn-primary mt-2"
                        ),
                    ),
                    ui.column(
                        3,
                        ui.input_action_button(
                            "remove_row", "Remove Last Row", class_="btn-warning mt-2"
                        ),
                    ),
                    ui.column(
                        3,
                        ui.input_action_button(
                            "fetch", "Fetch Data", class_="btn-success mt-2"
                        ),
                    ),
                ),
            ),
            ui.nav_panel(
                "CSV Upload",
                ui.input_file("csv_upload", "Upload CSV file", accept=[".csv"]),
                ui.input_action_button(
                    "fetch_csv", "Fetch Data from CSV", class_="btn-success mt-2"
                ),
            ),
        ),
        ui.hr(),
        ui.row(
            ui.column(12, ui.div(ui.output_table("portfolio_table"), class_="mb-5")),
        ),
        ui.row(
            ui.column(12, ui.div(ui.output_plot("portfolio_performance"), class_="mb-5")),
        ),
        ui.row(
            ui.column(12, ui.div(ui.output_plot("risk_return_chart"), class_="mb-5")),
        ),
        ui.row(
            ui.column(6, ui.div(ui.output_plot("sector_breakdown_chart"), class_="mb-5 pe-3")),
            ui.column(6, ui.div(ui.output_table("portfolio_metrics"), class_="mb-5 ps-3")),
        ),
    )
)


def server(input: Inputs, output: Outputs, session: Session):
    row_count = reactive.Value(1)
    portfolio_metrics_value = reactive.Value(None)  # Renamed from portfolio_metrics
    data_fetched = reactive.Value(None)
    portfolio_performance_chart = reactive.Value(None)
    csv_data = reactive.Value(None)

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
    def fetch_data_from_manual():
        symbols, shares = get_portfolio_data()
        data = fetch_portfolio_data(symbols, shares, API_KEY)
        data_fetched.set(data)
        metrics = calculate_portfolio_metrics(data)
        portfolio_metrics_value.set(metrics)

        # Create portfolio data dictionary for the performance chart
        portfolio_data = {
            symbol: {"shares": shares[i]} for i, symbol in enumerate(symbols)
        }

        # Create the portfolio performance chart
        performance_chart = create_portfolio_performance_chart(portfolio_data)
        portfolio_performance_chart.set(performance_chart)

    @reactive.Effect
    @reactive.event(input.fetch_csv)
    def fetch_data_from_csv():
        file_infos = input.csv_upload()
        if file_infos and len(file_infos) > 0:
            file_info: FileInfo = file_infos[0]
            file_path = file_info["datapath"]

            # Check file encoding
            with open(file_path, "rb") as file:
                raw_data = file.read()
                result = chardet.detect(raw_data)
                file_encoding = result["encoding"]

            if file_encoding.lower() not in ["utf-8", "ascii"]:
                ui.notification_show(
                    f"Error: The file is not UTF-8 or ASCII encoded. Detected encoding: {file_encoding}",
                    duration=None,
                    type="error",
                )
                return

            try:
                # Try to read the CSV file with comma separator
                df = pd.read_csv(file_path, encoding="utf-8", sep=",")

                # Check if required columns exist
                if "symbol" not in df.columns or "shares" not in df.columns:
                    ui.notification_show(
                        "Error: The CSV file must contain the headers 'symbol' and 'shares' and use a comma as the delimiter.",
                        duration=None,
                        type="error",
                    )
                    return

                symbols = df["symbol"].tolist()
                shares = df["shares"].tolist()

                # Additional check for data types
                if not all(isinstance(share, (int, float)) for share in shares):
                    ui.notification_show(
                        "Error: 'shares' column must contain numeric values.",
                        duration=None,
                        type="error",
                    )
                    return

                data = fetch_portfolio_data(symbols, shares, API_KEY)
                data_fetched.set(data)
                metrics = calculate_portfolio_metrics(data)
                portfolio_metrics_value.set(metrics)

                # Create portfolio data dictionary for the performance chart
                portfolio_data = {
                    symbol: {"shares": shares[i]} for i, symbol in enumerate(symbols)
                }

                # Create the portfolio performance chart
                performance_chart = create_portfolio_performance_chart(portfolio_data)
                portfolio_performance_chart.set(performance_chart)

                ui.notification_show(
                    "CSV data processed successfully!", duration=3, type="message"
                )

            except pd.errors.EmptyDataError:
                ui.notification_show(
                    "Error: The CSV file is empty.", duration=None, type="error"
                )
            except pd.errors.ParserError:
                ui.notification_show(
                    "Error: The file is not a valid CSV. Please ensure it's comma-separated.",
                    duration=None,
                    type="error",
                )
            except Exception as e:
                ui.notification_show(
                    f"An error occurred while processing the file: {str(e)}",
                    duration=None,
                    type="error",
                )

    @output
    @render.table
    def portfolio_table():
        data = data_fetched.get()
        if data is None or data.empty:
            return pd.DataFrame({"Message": ["No data available. Please fetch data."]})
        return data



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
            return pd.DataFrame(
                {"Message": ["No metrics available. Please fetch data."]}
            )
        return metrics  # This should now be the DataFrame returned by calculate_portfolio_metrics

    @output
    @render.plot
    def portfolio_performance():
        return portfolio_performance_chart.get()

    @output
    @render.plot(alt="Risk-Return Analysis")
    def risk_return_chart():
        data = data_fetched.get()
        if data is None or data.empty:
            return None
        return create_risk_return_chart(data)



# Create the Shiny app
app = App(app_ui, server)
