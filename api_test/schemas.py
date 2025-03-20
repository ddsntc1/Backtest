from pydantic import BaseModel
from datetime import date

class ETFPrice(BaseModel):
    date : date
    ticker : str
    price : float
    
    
class BacktestRequest(BaseModel):
    start_year: int
    start_month: int
    initial_balance: int
    trade_day: int
    fee_rate: float
    weight_months: int
    
    
class Nav(BaseModel):
    data_id: int
    date: date
    nav_total: float
    
    
class RebalanceSchema(BaseModel):
    data_id: int
    date: date
    ticker: str
    weight: float
