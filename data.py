import yfinance as yf
import json

def get_stock_data(ticker_symbol: str):
    # 1. Connect to Yahoo Finance for the specific ticker
    ticker = yf.Ticker(ticker_symbol)
    
    # 2. Fetch the last month of data (~30 calendar days)
    hist = ticker.history(period="1mo")
    
    # Safety check: If the ticker is fake or has no data, return an error
    if hist.empty:
        return {"error": f"No data found for {ticker_symbol}"}
    
    # 3. Extract the 'Close' prices
    # We format the dates to standard strings (YYYY-MM-DD) so they play nicely with FastAPI later
    closing_prices = {date.strftime('%Y-%m-%d'): round(price, 2) for date, price in hist['Close'].items()}
    
    # 4. Calculate a Simple Moving Average (SMA)
    # The SMA is just the sum of all closing prices divided by the number of days
    sma = sum(closing_prices.values()) / len(closing_prices)
    
    # 5. Return everything neatly bundled in a Python dictionary
    return {
        "ticker": ticker_symbol.upper(),
        "moving_average": round(sma, 2),
        "closing_prices": closing_prices
    }

# --- TEST SCRIPT ---
# This block only runs if you run this file directly in the terminal
if __name__ == "__main__":
    print("Fetching data for SPY...")
    test_data = get_stock_data("SPY")
    
    # json.dumps makes the dictionary print in a pretty, easy-to-read format
    print(json.dumps(test_data, indent=4))