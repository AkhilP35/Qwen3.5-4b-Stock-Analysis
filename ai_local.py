import ollama
from pydantic import BaseModel, Field, ValidationError
from typing import Literal
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import OLLAMA_MODEL

logger = logging.getLogger(__name__)

# System prompt (unchanged)
SYSTEM_PROMPT = """You are an expert financial analyst specializing in technical analysis and risk assessment.
... (the rest stays exactly the same) ..."""

# Pydantic schema (unchanged)
class StockAnalysis(BaseModel):
    ticker: str
    signal: Literal["BUY", "HOLD", "SELL"]
    risk_score: int = Field(ge=1, le=10, description="1-3: stable, 4-6: moderate, 7-10: high volatility")
    confidence_level: str = Field(description="State confidence based on data availability")
    reasoning: str = Field(description="2-3 sentences covering the primary trend, evidence, and risk factor")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception)),
    reraise=True
)
def analyze_stock(ticker: str, financial_data: str) -> StockAnalysis:
    """Sends financial data to the local LLM and returns a validated Pydantic object."""
    logger.info(f"Analyzing {ticker} with model {OLLAMA_MODEL}...")

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': f'Analyze this stock data for {ticker}:\n{financial_data}'}
            ],
            format=StockAnalysis.model_json_schema(),
            options={'temperature': 0.0}
        )
        raw_json_string = response.message.content
        validated_data = StockAnalysis.model_validate_json(raw_json_string)
        return validated_data

    except ValidationError as ve:
        logger.error(f"LLM output schema validation failed for {ticker}: {ve}")
        raise  # Will trigger retry because it's an Exception
    except Exception as e:
        logger.error(f"Ollama call failed for {ticker}: {e}")
        raise

# Execution example (if run directly)
if __name__ == "__main__":
    mock_data = """..."""  # same as before
    try:
        analysis = analyze_stock("NVDA", mock_data)
        # ... print
    except Exception as e:
        logger.exception("Analysis failed")
