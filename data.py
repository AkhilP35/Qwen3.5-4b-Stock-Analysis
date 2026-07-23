import yfinance as yf
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception)),
    reraise=True
)
def get_stock_data(ticker_symbol: str):
    """
    Fetch 1 month of historical data, calculate a simple moving average,
    and return a structured dictionary.
    """
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="1mo")

    if hist.empty:
        raise ValueError(f"No data found for ticker {ticker_symbol}")

    closing_prices = {
        date.strftime('%Y-%m-%d'): round(price, 2)
        for date, price in hist['Close'].items()
    }

    sma = sum(closing_prices.values()) / len(closing_prices)

    return {
        "ticker": ticker_symbol.upper(),
        "moving_average": round(sma, 2),
        "closing_prices": closing_prices
    }

# Quick test (run with: python data.py)
if __name__ == "__main__":
    import json
    print("Fetching data for SPY...")
    try:
        data = get_stock_data("SPY")
        print(json.dumps(data, indent=4))
    except Exception as e:
        logger.exception("Test failed")
