from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date,timedelta
import pandas as pd


def get_weekday(db: Session, target_date: date):
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
    df_pivot = df.pivot(index='date',columns='ticker',values='price').reset_index()
    return df_pivot
    
    