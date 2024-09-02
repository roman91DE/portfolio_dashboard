import argparse

from shiny import run_app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Portfolio Tracker App")
    parser.add_argument("-d", "--debug", action="store_true", help="Run in debug mode")
    parser.add_argument(
        "-p", "--port", type=int, default=8000, help="Port to run the app on"
    )
    args = parser.parse_args()

    run_app(
        "app.app:app",
        port=args.port,
        host="0.0.0.0",
        log_level="debug" if args.debug else "info",
        reload=True,  # Disable auto-reload
        dev_mode=args.debug,
    )
