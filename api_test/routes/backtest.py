from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db
from services.backtest_crud import calculate_backtest,save_result,get_backtest_list,get_summary,delete_input
import models
from datetime import date
from dateutil.relativedelta import relativedelta
from schemas import BacktestRequestSchema

router = APIRouter(prefix="/backtest",)

    
@router.post("/run")
def run_backtest(rq: BacktestRequestSchema,db: Session = Depends(get_db)):

        
    min_date_db =  db.query(func.min(models.ETFPrice.date)).scalar()
    min_date = date(rq.start_year,rq.start_month,rq.trade_day) - relativedelta(months=rq.weight_months)
    
    if min_date < min_date_db:
        raise HTTPException(
            status_code= 400,
            detail=f"데이터가 {min_date_db.strftime('%Y-%m-%d')} 이후부터 존재합니다. 시작일로부터 {rq.weight_months}개월 전 데이터가 존재하지 않습니다."
        )
        
    
    result = calculate_backtest(
        db=db,
        start_year=rq.start_year,
        start_month=rq.start_month,
        trade_day=rq.trade_day,
        weight_months=rq.weight_months,
        fee_rate=rq.fee_rate
    )
    
    
    data_id = save_result(
        db=db,
        df_cal=result["result"]["df_cal"],
        nav_list=result["result"]["nav_list"],
        balances=result["result"]["balances"],
        start_year=rq.start_year,
        start_month=rq.start_month,
        initial_balance=rq.initial_balance,
        trade_day=rq.trade_day,
        fee_rate=rq.fee_rate,
        weight_months=rq.weight_months
    )
    return {
        "data_id": data_id,
        "output": result["metrics"],
        "last_rebalance_weight": result["last_rebalance_weight"],
    }
    
    
@router.get("/")
def list_results(db: Session = Depends(get_db)):
    return get_backtest_list(db)


@router.get("/{data_id}")
def get_result(data_id: int, db: Session = Depends(get_db)):
    result = get_summary(db, data_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"data_id : {data_id} not found")
    return result


@router.delete("/{data_id}")
def delete_backtest(data_id: int, db: Session = Depends(get_db)):
    try:
        success = delete_input(db, data_id)
        return {"data_id": data_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))