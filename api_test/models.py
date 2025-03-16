from sqlalchemy import Column,Integer,String,Date,Numeric,UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from .database import Base

class ETFPrice(Base):
    __tablename__ = "prices"
    
    id = Column(Integer,primary_key=True,index=True)
    date = Column(Date,nullable=False)
    ticker = Column(String(10),nullable=False) # SPY QQQ GLD TIP BIL
    price = Column(Numeric(13,4),nullable=False)
    
    