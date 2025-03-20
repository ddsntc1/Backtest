from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date,timedelta
import pandas as pd


def get_weekday(target_date: date):
    """주말 판별기 -> 주말이면 이전 가까운 평일로 변경"""
    while target_date.weekday() in [5,6]:
        target_date -= timedelta(days=1)
    return target_date


def get_prices(db:Session, start_date: date,weight_months: int):
    """날짜별 ETF 가격 가져오기"""
    
    from_date = start_date - timedelta(days= weight_months * 31)
    
    prices_query = text("""
                        SELECT date,ticker,MAX(price)
                        FROM prices
                        WHERE date >= :start_date
                        GROUP BY date,ticker
                        ORDER BY date ASC;
                        """)
    price_data = db.execute(prices_query,{"start_date":from_date})
    df = pd.DataFrame(price_data,columns=['date','ticker','price'])
    df_pivot = df.pivot(index='date',columns='ticker',values='price')
    return df_pivot

# 만약 매달 31일 인 경우 2월 계싼이 끝나면 3/29 이런식으로 바뀌어버림..
# 해결 방법 찾아야 함.

# def calculate_backtest(db : Session, data_id: int, start_year: int, start_month:int, trade_day : int, initial_balance:int, weight_months:int,fee_rate:float):
def calculate_backtest(db : Session, start_year: int, start_month:int, trade_day : int, weight_months:int):
    """ 계산 수행 """
    
    start_date = get_weekday(date(start_year,start_month,trade_day))
    df_prices = get_prices(db,start_date,weight_months)
    
    if df_prices.empty:
        return {'error':"가격데이터를 찾을 수 없습니다."}
    
    if weight_months >= start_month:
        set_month = start_month - weight_months + 12
        set_year = start_year-1
    else : 
        set_month -= weight_months
        set_year = start_year
    
    trade_dates = pd.date_range(start=pd.Timestamp(set_year,set_month,1), end=df_prices.index[-1],freq='MS')
    trade_dates = [get_weekday(date + timedelta(days=trade_day-1)) for date in trade_dates]
    
    df = df_prices.loc[trade_dates]
    
    for col in df.columns:
        df[f'prev_{col}'] = df[col].shift(weight_months)
        
    
    return df.loc[start_date:]
    nav = 1000
    peak_nav =nav
    nav_history = []
    rebalance_weights = []
    
    current_weights = {}
    