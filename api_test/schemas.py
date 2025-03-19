from pydantic import BaseModel
from datetime import date

class ETFPrice(BaseModel):
    date : date
    ticker : str
    price : float
    
    class Config:
        orm_mode = True
    
    
class BacktestRequest(BaseModel):
    start_year: int
    start_month: int
    initial_balance: int
    trade_day: int
    fee_rate: float
    weight_months: int
    
    class Config:
        orm_mode = True
    
class Nav(BaseModel):
    data_id: int
    date: date
    nav_total: float
    
    class Config:
        orm_mode = True
    
class RebalanceSchema(BaseModel):
    data_id: int
    date: date
    ticker: str
    weight: float

    class Config:
        orm_mode = True



    # data_id = Column(Integer, primary_key=True,autoincrement=True, index=True)
    # start_year = Column(Integer, nullable=False)
    # start_month = Column(Integer,nullable=False)
    # initial_balance = Column(Integer,nullable=False)
    # trade_day = Column(Integer,nullable=False)
    # fee_rate = Column(Numeric(5,4),nullable=False)
    # weight_months = Column(Integer,nullable=False)
    # created_at = Column(TIMESTAMP,server_default=func.now())