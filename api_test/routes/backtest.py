from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db
from services.backtest_crud import calculate_backtest,save_result,get_backtest_list,get_summary,delete_input,test_backtest_df
import models
from datetime import date
from dateutil.relativedelta import relativedelta
from schemas import BacktestRequestSchema

router = APIRouter(prefix="/backtest",)

@router.post("/run")
def run_backtest(rq: BacktestRequestSchema,db: Session = Depends(get_db)):
    
    try:
        input_date = date(rq.start_year, rq.start_month, rq.trade_day)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="입력한 날짜가 잘못되었습니다. 존재하지 않는 날짜이거나 범위 초과입니다."
        )

        
    min_date_db =  db.query(func.min(models.ETFPrice.date)).scalar()
    min_date = input_date - relativedelta(months=rq.weight_months)
    max_date_db = db.query(func.max(models.ETFPrice.date)).scalar()
    
        
    if min_date < min_date_db or input_date > max_date_db:
        raise HTTPException(
            status_code= 400,
            detail=f"데이터가 {min_date_db.strftime('%Y-%m-%d')} 이후부터 {max_date_db.strftime('%Y-%m-%d')} 까지 존재합니다."
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
    
    
@router.post('/test')
def test_backtest(rq:BacktestRequestSchema,db:Session = Depends(get_db)):
    try:
        input_date = date(rq.start_year, rq.start_month, rq.trade_day)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="입력한 날짜가 잘못되었습니다. 존재하지 않는 날짜이거나 범위 초과입니다."
        )
    min_date_db =  db.query(func.min(models.ETFPrice.date)).scalar()
    min_date = input_date - relativedelta(months=rq.weight_months)
    max_date_db = db.query(func.max(models.ETFPrice.date)).scalar()   
    if min_date < min_date_db or input_date > max_date_db:
        raise HTTPException(
            status_code= 400,
            detail=f"데이터가 {min_date_db.strftime('%Y-%m-%d')} 이후부터 {max_date_db.strftime('%Y-%m-%d')} 까지 존재합니다."
        )
        
    return test_backtest_df(
        db=db,
        start_year=rq.start_year,
        start_month=rq.start_month,
        trade_day=rq.trade_day,
        weight_months=rq.weight_months,
        fee_rate=rq.fee_rate
    )