from sqlalchemy import Column,Integer,String,Date,Numeric,UniqueConstraint, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from database import Base

class ETFPrice(Base):
    __tablename__ = "prices"
    
    id = Column(Integer,primary_key=True,index=True)
    date = Column(Date,nullable=False)
    ticker = Column(String(10),nullable=False) # SPY QQQ GLD TIP BIL
    price = Column(Numeric(13,4),nullable=False)
    
    __table_args__ = (UniqueConstraint("date","ticker",name = 'uq_prices_date_ticker'),)
    
    
class BacktestRequest(Base):
    __tablename__ = 'backtest_requests'
    
    data_id = Column(Integer, primary_key=True,autoincrement=True, index=True)
    start_year = Column(Integer, nullable=False)
    start_month = Column(Integer,nullable=False)
    initial_balance = Column(Integer,nullable=False)
    trade_day = Column(Integer,nullable=False)
    fee_rate = Column(Numeric(5,4),nullable=False)
    weight_months = Column(Integer,nullable=False)
    
    nav = relationship("Nav",back_populates="backtest_request",cascade="all, delete-orphan")
    rebalance = relationship("Rebalance",back_populates="backtest_request",cascade="all, delete-orphan")
    
class Nav(Base):
    __tablename__ = "nav"    
    id = Column(Integer,primary_key=True,autoincrement=True,index =True)
    data_id = Column(Integer,ForeignKey("backtest_requests.data_id"),nullable=False)
    date =Column(Date,nullable=False)
    nav_total = Column(Numeric(15,2),nullable=False)
    
    backtest_request = relationship("BacktestRequest",back_populates="nav")
    
    
class Rebalance(Base):
    __tablename__ = "rebalance"
    
    id = Column(Integer,primary_key=True,autoincrement=True,index = True)
    data_id = Column(Integer,ForeignKey("backtest_requests.data_id"),nullable=False)
    date = Column(Date,nullable=False)
    ticker = Column(String(10),nullable=False)
    weight = Column(Numeric(3,2),nullable=False)
    
    backtest_request = relationship("BacktestRequest",back_populates="rebalance")