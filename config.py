import os
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env file

# Database
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Check your .env file.")

# AI model
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")  # default to qwen

# Ticker list for daily automated scan
TICKER_LIST = ["SPY", "QQQ", "GLD", "AAPL"]

# Other settings (you can expand as needed)
