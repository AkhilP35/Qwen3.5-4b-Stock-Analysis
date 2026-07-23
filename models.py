from sqlalchemy import create_engine, Column, Integer, String, Date, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import date
from config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DailyAnalysis(Base):
    __tablename__ = "daily_analysis"
    __table_args__ = (
        UniqueConstraint('date', 'ticker', name='uq_date_ticker'),
    )

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=date.today)
    ticker = Column(String, index=True)
    risk_score = Column(Integer)
    signal = Column(String)
    rationale = Column(String)

# Note: Do NOT use Base.metadata.create_all() in production.
# Instead, use Alembic migrations. For quick prototyping, uncomment the next line:
# Base.metadata.create_all(bind=engine)
