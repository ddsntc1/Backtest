from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas import BacktestRequest
from services.backtest_crud import get_prices


router = APIRouter(prefix="/api",)

@router.get("/prices")
def test_get_price(start_date:str, weight_months:int,db:Session=Depends(get_db)):
    from datetime import datetime
    start_date = datetime.strptime(start_date,"%Y-%m-%d").date()
    
    price_data = get_prices(db,start_date,weight_months)
    
    return [price_data.iloc[i,:] for i in range(len(price_data))]
    