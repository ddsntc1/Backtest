from sqlalchemy import Column,Integer,String,Date,Numeric,UniqueConstraint, ForeignKey, TIMESTAMP, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from database import Base
from sqlalchemy.dialects.postgresql import JSONB

class ETFPrice(Base):
    __tablename__ = "prices"
    
    date = Column(Date,nullable=False)
    ticker = Column(String(10),nullable=False) # SPY QQQ GLD TIP BIL
    price = Column(Numeric(13,4),nullable=False)
    
    __table_args__ = (
        PrimaryKeyConstraint("date", "ticker", name="pk_prices_date_ticker"),
        )
    
    
class BacktestRequest(Base):
    __tablename__ = 'backtest_requests'
    
    data_id = Column(Integer, primary_key=True,autoincrement=True, index=True)
    start_year = Column(Integer, nullable=False)
    start_month = Column(Integer,nullable=False)
    initial_balance = Column(Integer,nullable=False)
    trade_day = Column(Integer,nullable=False)
    fee_rate = Column(Numeric(5,4),nullable=False)
    weight_months = Column(Integer,nullable=False)
    nav_result = Column(JSONB) 
    rebalance_result = Column(JSONB)
    