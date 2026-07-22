from fastapi import FastAPI
from data import get_stock_data
from ai import analyze_asset

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "running"}

# The {ticker} in the URL becomes the variable passed into the function
@app.get("/analyze/{ticker}")
def analyze_ticker(ticker: str):
    # 1. Fetch real market data
    stock_data = get_stock_data(ticker)
    
    # Handle invalid tickers gracefully
    if "error" in stock_data:
        return stock_data
        
    # 2. Send the data to your local Llama 3.2 model
    ai_response = analyze_asset(stock_data)
    
    # 3. Return the structured AI analysis directly to the browser
    return ai_response