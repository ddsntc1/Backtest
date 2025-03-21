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
def calculate_backtest(db : Session, start_year: int, start_month:int, trade_day : int, weight_months:int,fee_rate:float):
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
    
    # 거래 및 비교일 산출
    trade_dates = pd.date_range(start=pd.Timestamp(set_year,set_month,1), end=df_prices.index[-1],freq='MS')
    trade_dates = [get_weekday(date + timedelta(days=trade_day-1)) for date in trade_dates]
    
    # 거래일에 해당하는 내용만 추출출
    df = df_prices.loc[trade_dates]
    
    # weight_months 이전 데이터와 합치기
    raw_columns = df.columns
    etfs = raw_columns.drop(['BIL','TIP'])

    
    for col in raw_columns:
        df[f'prev_{col}'] = df[col].shift(weight_months)
    
    # rebalance 계산
    # df_cal : 계산을 위한 데이터프레임으로 시작일 부터의 데이터가 있음
    # df : 시작일 - weight_months * 31 전부터 데이터가 존재하며 필요한 데이터 끌어올 용도
    
    df_cal = df.loc[start_date:].copy()
    
    # 리밸런싱 산정을 위한 wb_{col} 칼럼 생성 // weight_months 이전과 수익률 비교교
    # -> 향후 1개월 전 가격과 비교한 수익률 칼럼으로 사용예정
    for col in raw_columns:
        df_cal[f'wb_{col}'] = (df_cal[col] - df_cal[f'prev_{col}'])/df_cal[f'prev_{col}']
        if col != 'TIP':
            df_cal[f'rb_{col}'] = float(0)
    
    # 리밸런스 비중 결정 -> rb_{col}로 0, 0.5, 1이 존재
    for i, row in df_cal.iterrows():
        tip_return = row['wb_TIP']
        
        if tip_return >= 0:
            selected = sorted(
                [(etf,row[f'wb_{etf}']) for etf in etfs],
                key= lambda x : x[1],
                reverse= True)[:2]
            for etf,_ in selected:
                df_cal.loc[i, f'rb_{etf}'] = float(0.5)
        else:
            df_cal.loc[i, 'rb_BIL'] = float(1)
    
    # wb_col 칼럼을 1개월 전과 비교하여 수익률 계산에 사용
    # prev_col : 1개월 전 가격
    # wb_col : 1개월 전과 비교한 수익률 칼럼
    for col in raw_columns:
        df_cal[f'prev_{col}'] = df[col].shift(1).loc[start_date:]
        df_cal[f'wb_{col}'] = df_cal[col]/df_cal[f'prev_{col}']
    
    balances = raw_columns.drop('TIP')
    
    for col in balances:
        df_cal[f'wb_{col}'][0] = 0
    
    nav = 1000
    nav_list = []
    peak_nav = nav
    drawdown_list = []
    prev_weights = {col: 0 for col in raw_columns}


    return df_cal
    

    