from pandas import DataFrame


def create_portfolio_dataframe(portfolio_data: list[dict]) -> DataFrame:
    try:
        # Create DataFrame
        df = DataFrame(portfolio_data)

        # Define expected columns and their types
        expected_columns = {
            "Ticker/ISIN": "string",
            "Name": "string",
            "Asset Type": "string",
            "Sector": "string",
            "Shares": "int32",
            "Latest Close": "float64",
        }

        # Convert types only for columns that exist
        for col, dtype in expected_columns.items():
            if col in df.columns:
                df[col] = df[col].astype(dtype)

        # Calculate Total Value if possible
        if "Latest Close" in df.columns and "Shares" in df.columns:
            df["Total_Value"] = df["Latest Close"] * df["Shares"]
            df = df.sort_values(by="Total_Value", ascending=False)

        df = df.reset_index(drop=True)

        return df

    except Exception as e:
        print(f"Error creating portfolio dataframe: {e}")
        return DataFrame(portfolio_data)  # Return the original data as a DataFrame
