from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import date

# Replace this with your actual Supabase connection string
DATABASE_URL = "postgresql://postgres:[PASSWORD]@db.dlhwvoejafhshxagytky.supabase.co:5432/postgres"

# Set up the connection
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define your table structure
class DailyAnalysis(Base):
    __tablename__ = "daily_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=date.today)
    ticker = Column(String, index=True)
    risk_score = Column(Integer)
    signal = Column(String)
    rationale = Column(String)

# This magic line automatically creates the table in Supabase if it doesn't exist yet!
Base.metadata.create_all(bind=engine)
