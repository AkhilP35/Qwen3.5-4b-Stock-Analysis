import ollama
from pydantic import BaseModel, Field
from typing import Literal

# 1. The System Prompt 
SYSTEM_PROMPT = """You are an expert financial analyst specializing in technical analysis and risk assessment.

## Your Role
Analyze stock data using price action, moving averages, and trend analysis to provide actionable insights for short-term traders.

## Core Rules
- Never invent price data or market events not provided in the input.
- When data is insufficient, state your confidence level in the reasoning.
- Always return ONLY valid JSON matching the exact schema provided.
- Be decisive — don't hedge with "might" or "could" unless data is truly ambiguous.
- Your signal must be strictly one of: "BUY", "HOLD", or "SELL".
- Always use English language for the reasoning and response.

## Analysis Methodology
- Compare recent closing prices to the 30-day moving average to determine trend direction.
- Assess whether the trend is accelerating, decelerating, or reversing.
- Consider volatility implied by the price range versus the moving average.
- Risk score (1-10): 1-3 = stable trend with low volatility, 4-6 = moderate uncertainty, 7-10 = high volatility or trend reversal risk.

"""

# 2. Define the Pydantic Schema
# This enforces the rules from your system prompt structurally.
class StockAnalysis(BaseModel):
    ticker: str
    signal: Literal["BUY", "HOLD", "SELL"]
    risk_score: int = Field(ge=1, le=10, description="1-3: stable, 4-6: moderate, 7-10: high volatility")
    confidence_level: str = Field(description="State confidence based on data availability")
    reasoning: str = Field(description="2-3 sentences covering the primary trend, evidence, and risk factor")

def analyze_stock(ticker: str, financial_data: str) -> StockAnalysis:
    """Sends financial data to Qwen via Ollama and returns a validated Pydantic object."""
    
    print(f"Analyzing {ticker} with qwen3.5:4b...")
    
    # 3. Call the Model
    response = ollama.chat(
        model='qwen3.5:4b',
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': f'Analyze this stock data for {ticker}:\n{financial_data}'}
        ],
        # Forces the local model to strictly adhere to the Pydantic JSON schema
        format=StockAnalysis.model_json_schema(),
        # A temperature of 0 is crucial for financial analysis to stop hallucinations
        options={'temperature': 0.0}
    )
    
    # 4. Parse and Validate
    raw_json_string = response.message.content
    validated_data = StockAnalysis.model_validate_json(raw_json_string)
    
    return validated_data

# --- Execution Example ---
if __name__ == "__main__":
    # Mock data to test the logic constraints
    mock_data = """
    Ticker: NVDA
    Current Price: $118.50
    30-Day Moving Average: $125.20
    Recent Price Range: $112.00 - $122.00
    Volume: Decelerating over the last 5 days
    News: Semiconductor sector facing mild headwinds due to supply chain delays.
    """
    
    try:
        # Run the analysis
        analysis = analyze_stock("NVDA", mock_data)
        
        # Print output to confirm successful structure
        print("\n--- Analysis Complete ---")
        print(f"Ticker: {analysis.ticker}")
        print(f"Signal: {analysis.signal}")
        print(f"Risk Score: {analysis.risk_score}/10")
        print(f"Confidence: {analysis.confidence_level}")
        print(f"Reasoning:\n{analysis.reasoning}")
        
    except Exception as e:
        print(f"An error occurred: {e}")