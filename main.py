from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime, date
import pandas as pd
import exchange_calendars as xcals
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from config import TICKER_LIST
from data import get_stock_data
from ai_local import analyze_stock, StockAnalysis
from models import SessionLocal, DailyAnalysis

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Scheduler setup
scheduler = BackgroundScheduler()

# Market calendar for US trading days
nyse = xcals.get_calendar("XNYS")

def is_trading_day():
    """Check if today is a regular trading day on the NYSE."""
    today = pd.Timestamp.now(tz='America/New_York').normalize()
    return nyse.is_session(today)

def run_daily_scan():
    """Job that runs every weekday at 5:00 PM Eastern Time."""
    if not is_trading_day():
        logger.info("Today is not a trading day. Skipping scan.")
        return

    logger.info(f"Starting daily scan for tickers: {TICKER_LIST}")
    db = SessionLocal()
    try:
        for ticker in TICKER_LIST:
            try:
                # 1. Fetch data
                data_dict = get_stock_data(ticker)
                # 2. Format the data as a string to pass to the LLM
                financial_data_str = (
                    f"Ticker: {data_dict['ticker']}\n"
                    f"Current Price: {list(data_dict['closing_prices'].values())[-1]}\n"  # latest close
                    f"30-Day Moving Average: {data_dict['moving_average']}\n"
                    f"Recent Price Range: {min(data_dict['closing_prices'].values())} - {max(data_dict['closing_prices'].values())}\n"
                    f"Volume: (not available in this data)\n"
                )
                # 3. Analyze with AI
                analysis: StockAnalysis = analyze_stock(ticker, financial_data_str)

                # 4. Upsert to database (idempotent)
                stmt = pg_insert(DailyAnalysis).values(
                    date=date.today(),
                    ticker=analysis.ticker,
                    risk_score=analysis.risk_score,
                    signal=analysis.signal,
                    rationale=analysis.reasoning
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=['date', 'ticker'],
                    set_=dict(
                        risk_score=stmt.excluded.risk_score,
                        signal=stmt.excluded.signal,
                        rationale=stmt.excluded.rationale
                    )
                )
                db.execute(stmt)
                db.commit()
                logger.info(f"Successfully processed {ticker}")

            except Exception as e:
                logger.exception(f"Failed to process {ticker}: {e}")
                db.rollback()  # rollback any partial changes for this ticker
                continue  # move to next ticker

    finally:
        db.close()
    logger.info("Daily scan completed.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the scheduler when the app starts
    scheduler.add_job(
        run_daily_scan,
        trigger='cron',
        day_of_week='mon-fri',
        hour=17,
        minute=0,
        timezone='America/New_York',
        id='daily_scan',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300
    )
    scheduler.start()
    logger.info("Scheduler started.")
    yield
    # Shut down the scheduler when the app stops
    scheduler.shutdown()
    logger.info("Scheduler shut down.")

app = FastAPI(lifespan=lifespan)

# Allow requests from Next.js frontend (adjust origin in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "running"}

@app.get("/analyze/{ticker}")
def analyze_ticker(ticker: str):
    """On-demand analysis for a single ticker. Returns AI signal and saves to DB."""
    db = SessionLocal()
    try:
        data_dict = get_stock_data(ticker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Data fetch failed for {ticker}")
        raise HTTPException(status_code=500, detail="Failed to fetch stock data.")

    financial_data_str = (
        f"Ticker: {data_dict['ticker']}\n"
        f"Current Price: {list(data_dict['closing_prices'].values())[-1]}\n"
        f"30-Day Moving Average: {data_dict['moving_average']}\n"
        f"Recent Price Range: {min(data_dict['closing_prices'].values())} - {max(data_dict['closing_prices'].values())}\n"
        f"Volume: (not available in this data)\n"
    )

    try:
        analysis: StockAnalysis = analyze_stock(ticker, financial_data_str)
    except Exception as e:
        logger.exception(f"AI analysis failed for {ticker}")
        raise HTTPException(status_code=500, detail="AI analysis failed after multiple attempts.")

    # Save to DB (upsert)
    try:
        stmt = pg_insert(DailyAnalysis).values(
            date=date.today(),
            ticker=analysis.ticker,
            risk_score=analysis.risk_score,
            signal=analysis.signal,
            rationale=analysis.reasoning
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=['date', 'ticker'],
            set_=dict(
                risk_score=stmt.excluded.risk_score,
                signal=stmt.excluded.signal,
                rationale=stmt.excluded.rationale
            )
        )
        db.execute(stmt)
        db.commit()
    except Exception as e:
        logger.exception("DB write failed")
        db.rollback()
        # We still return the analysis even if DB fails
    finally:
        db.close()

    return analysis.model_dump()

@app.get("/analyses")
def get_analyses(
    ticker: str = Query(None),
    date: str = Query(None),  # format YYYY-MM-DD
    skip: int = 0,
    limit: int = 100
):
    """Retrieve historical analyses, with optional filters and pagination."""
    db = SessionLocal()
    query = db.query(DailyAnalysis)
    if ticker:
        query = query.filter(DailyAnalysis.ticker == ticker.upper())
    if date:
        query = query.filter(DailyAnalysis.date == date)
    rows = query.order_by(DailyAnalysis.date.desc()).offset(skip).limit(limit).all()
    db.close()
    # Convert SQLAlchemy objects to dictionaries
    return [
        {
            "id": row.id,
            "date": row.date.isoformat(),
            "ticker": row.ticker,
            "risk_score": row.risk_score,
            "signal": row.signal,
            "rationale": row.rationale
        }
        for row in rows
    ]
