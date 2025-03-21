from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date,timedelta
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
import models

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

def calculate_backtest(db : Session, start_year: int, start_month:int, trade_day : int,initial_balance:int, weight_months:int,fee_rate:float):
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
    
    balances = raw_columns.drop('TIP') # TIP는 판단기준이고 나머지를 대상으로 진행하기 리스트 설정
    
    for col in balances:
        df_cal[f'wb_{col}'][0] = 0 # 시작날 수익률 0        
    
    # 초기 NAV = 이전 매매 최종NAV * 각 etf 수익률
    # 목표 NAV = 초기NAv합 * etf별 리밸런싱
    # 수수료 = |매매 전 각 etf NAV - 목표 NAV 각 etf| * fee_rate
    # 수수료 적용 NAV = 초기NAV합 - 수수료 총합
    # 최종 NAV = (수수료 적용 NAV) * 리밸런싱
    nav = 1000
    nav_list = []
    fee_list = []
    prev_weights = {etf: 0.0 for etf in balances}
    prev_navs = {etf: 0.0 for etf in balances}

    for i, row in df_cal.iterrows():
        # 초기 navs
        init_navs = {etf:prev_navs[etf] * float(row[f'wb_{etf}']) for etf in balances}
        nav = sum(init_navs.values())
        if i == start_date:
            nav = 1000
        
        # 목표 nav 
        target_navs = {etf:float(row[f'rb_{etf}'])*nav for etf in balances}
        
        # 수수료 
        fees = {etf : abs(target_navs[etf]-init_navs[etf])*fee_rate for etf in balances}
        nav -= sum(fees.values())
        
        # 매매 후 nav
        after_navs = {etf: float(row[f'rb_{etf}'])*nav for etf in balances}
        
        nav_list.append(sum(after_navs.values()))        
        fee_list.append(sum(fees.values()))
        
        prev_navs = after_navs

    df_cal["nav"] = nav_list
    df_cal["tot_fee"] = fee_list

    # 전체 수익률
    total_return = nav_list[-1] / 1000 - 1

    # 연환산 수익률 (CAGR)
    num_years = len(nav_list) / 12
    cagr = (nav_list[-1] / 1000)**(1/num_years) - 1 if num_years > 0 else 0

    # 연 변동성
    monthly_returns = pd.Series(nav_list).pct_change().dropna()
    volatility = monthly_returns.std() * (12 ** 0.5)

    # 샤프지수
    sharpe = cagr / volatility if volatility > 0 else 0

    # 최대 낙폭 (MDD)
    running_max = np.maximum.accumulate(nav_list)
    drawdowns = [nav / peak - 1 for nav, peak in zip(nav_list, running_max)]
    mdd = min(drawdowns)
    



    # return df_cal
    return {
        "output": {
            "total_return": round(total_return, 4),
            "cagr": round(cagr, 4),
            "vol": round(volatility, 4),
            "sharpe": round(sharpe, 4),
            "mdd": round(mdd, 4),
        },
        "last_nav": [(f"{etf}",df_cal[f'rb_{etf}'][-1]) for etf in balances],
    }
        