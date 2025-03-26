from sqlalchemy.orm import Session
from sqlalchemy import text,desc
from datetime import date,timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np
import models
import calendar

def get_weekday(target_date: date):
    """주말 판별기 -> 주말이면 이전 가까운 평일로 변경"""
    while target_date.weekday() in [5,6]:
        target_date -= timedelta(days=1)
    return target_date

def get_valid_date(base_date: date, trade_day: int):
    """해당 월의 최대 day 값과 입력된 trade_day 비교"""
    year = base_date.year
    month = base_date.month
    last_day = calendar.monthrange(year, month)[1]
    target_day = min(trade_day, last_day)
    target_date = date(year, month, target_day)
    return get_weekday(target_date)

def get_prices(db: Session, start_date: date, weight_months: int):
    """날짜별 ETF 가격 가져오기"""
    from_date = get_weekday(start_date - relativedelta(months=weight_months))
    # ORM 쿼리 사용
    price_data = db.query(models.ETFPrice)\
        .filter(models.ETFPrice.date >= from_date)\
        .order_by(models.ETFPrice.date)\
        .all()
    if not price_data:
        return pd.DataFrame()
    # 리스트를 DataFrame으로 변환
    df = pd.DataFrame(
        [(p.date, p.ticker, float(p.price)) for p in price_data],
        columns=['date', 'ticker', 'price']
    )
    # 피벗
    df_pivot = df.pivot(index='date', columns='ticker', values='price')

    return df_pivot



def calculate_backtest(db : Session, start_year: int, start_month:int, trade_day : int, weight_months:int,fee_rate:float):
    """ 
    지정된 시작일과 조건에 따라 ETF 리밸런싱 백테스트를 수행하고, 성과 지표를 계산하는 함수.

    백테스트 전략:
    - weight_months 만큼 과거 가격을 비교하여 수익률 판단
    - TIP의 수익률이 양수인 경우: 수익률 상위 2개의 ETF에 각각 50% 비중으로 리밸런싱
    - TIP 수익률이 음수인 경우: BIL ETF에 100% 투자자

    주요 수행 로직:
    1. 시작일('start_date')을 계산하고, 과거 'weight_months'개월 포함한 가격 데이터 로드
    
    2. 월별 매매일 기준의 유효한 거래일 목록을 계산
        - 해당 month에 trade_day가 없는 경우 (ex. 2월 31일) 말일로 설정될 수 있도록 get_valid_date 함수 구현
        - trade_day가 매달 정해짐에 따라 주말이 껴있는 경우 get_weekday 함수를 통해 앞 평일로 이동
        
    3. 각 ETF별 'wb_' (수익률), 'rb_' (리밸런싱 비중) 컬럼 생성
        - 'wb_' 칼럼을 이용해 weight_month 전 가격과 비교 -> 'rb_'(리밸런싱) 칼럼 생성
        - 'wb_' 칼럼을 수익률 비교로 사용하기 위해 이전 매매날짜인 1개월 전 매매날짜와 비교해 수익률 비교
    
    4. TIP 수익률에 따라 리밸런싱 로직 적용하여 `rb_` 비중 결정
    
    5. 매 시점마다 수익률 및 수수료를 반영한 NAV 계산 수행:
        
        반복문 수행
        - 초기 NAV = 이전 매매 최종NAV * 각 etf 수익률
        - 목표 NAV = 초기NAv합 * etf별 리밸런싱
        - 수수료 = |매매 전 각 etf NAV - 목표 NAV 각 etf| * fee_rate
        - 수수료 적용 NAV = 초기NAV합 - 수수료 총합
        - 최종 NAV = (수수료 적용 NAV) * 리밸런싱    ==> nav_list에 저장

    6. 전체 기간 NAV 리스트를 기반으로 성과 지표 계산
    
    """
    # 1.
    start_date = get_weekday(date(start_year,start_month,trade_day))
    df_prices = get_prices(db,start_date,weight_months)
    
    if df_prices.empty:
        return {'error':"가격데이터를 찾을 수 없습니다."}
    
    if weight_months >= start_month:
        set_month = start_month - weight_months + 12
        set_year = start_year-1
    else : 
        set_month = start_month - weight_months
        set_year = start_year
    
    # 2.
    trade_dates = pd.date_range(start=pd.Timestamp(set_year,set_month,1), end=df_prices.index[-1],freq='MS')
    trade_dates = [get_valid_date(date,trade_day) for date in trade_dates]
    valid_trade_dates = [d for d in trade_dates if d in df_prices.index]
    
    df = df_prices.loc[valid_trade_dates]
    
    raw_columns = df.columns # 초기 ETFs + TIP 
    
    etfs = raw_columns.drop(['BIL','TIP']) # 투자전략으로 사용될 ETFs

    # 3. 
    for col in raw_columns:
        df[f'prev_{col}'] = df[col].shift(weight_months)

    df_cal = df.loc[start_date:].copy()
    
    for col in raw_columns:
        df_cal[f'wb_{col}'] = (df_cal[col] - df_cal[f'prev_{col}'])/df_cal[f'prev_{col}']
        if col != 'TIP':
            df_cal[f'rb_{col}'] = float(0)
    
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
    
    for col in raw_columns:
        df_cal[f'prev_{col}'] = df[col].shift(1).loc[start_date:]
        df_cal[f'wb_{col}'] = df_cal[col]/df_cal[f'prev_{col}']
     
    balances = raw_columns.drop('TIP') # 헷징수단인 BIL 포함 ETFs
    
    for col in balances:
        df_cal[0,f'wb_{col}'] = 0 
    
    # 4.
    
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

    # 6.
    
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
    
    return {
        "result": {
            "nav_list": nav_list,
            "df_cal": df_cal,
            "balances": balances
        },
        "metrics": {
            "total_return": round(total_return, 4),
            "cagr": round(cagr, 4),
            "vol": round(volatility, 4),
            "sharpe": round(sharpe, 4),
            "mdd": round(mdd, 4),
        },
        "last_rebalance_weight": [
            [etf, float(df_cal[f'rb_{etf}'].iloc[-1])] for etf in balances
        ]
    }
  
def save_result(
    db: Session,
    df_cal: pd.DataFrame,
    nav_list: list[float],
    balances: list[str],
    start_year: int,
    start_month: int,
    initial_balance: int,
    trade_day: int,
    fee_rate: float,
    weight_months: int
):
    """
    입력값 + 백테스트 결과를 DB에 저장하고 data_id 반환
    BacktestRequest에 nav_result, rebalance_result를 JSON으로 저장
    """

    # rebalance_result 생성 (list of dict)
    rebalance_result = []
    for i, row in df_cal.iterrows():
        rebalance_date = i  # index = 날짜
        weights = {
            etf: float(row.get(f"rb_{etf}", 0.0)) for etf in balances
        }
        rebalance_result.append({
            "date": rebalance_date.isoformat(),  # JSON 직렬화를 위한 문자열 처리
            "weights": weights
        })

    # nav_result 생성 (list of dict)
    nav_result = [
        {"date": i.isoformat(), "nav": float(nav)}
        for i, nav in zip(df_cal.index, nav_list)
    ]

    # BacktestRequest에 저장
    request_obj = models.BacktestRequest(
        start_year=start_year,
        start_month=start_month,
        initial_balance=initial_balance,
        trade_day=trade_day,
        fee_rate=fee_rate,
        weight_months=weight_months,
        nav_result=nav_result,
        rebalance_result=rebalance_result
    )
    db.add(request_obj)
    db.commit()
    db.refresh(request_obj)

    return request_obj.data_id


# 목록 불러오기
def get_backtest_list(db: Session):
    records = db.query(models.BacktestRequest).all()
    result = []

    for req in records:
        rebalance_data = req.rebalance_result  # JSON 필드

        if rebalance_data:
            last_entry = max(rebalance_data, key=lambda x: x["date"])
            last_date = last_entry["date"]

            # weights 구조 고려해서 파싱
            weights_dict = last_entry.get("weights", {})
            weights = [(ticker, weight) for ticker, weight in weights_dict.items()]
        else:
            weights = []

        result.append({
            "data_id": req.data_id,
            "last_rebalance_weight": weights
        })

    return result




def get_summary(db: Session, data_id: int):
    """
    1. data_id 유무 조회
    2. BacktestRequest에 저장된 nav_result 기반으로 통계값 계산
    3. rebalance_result로부터 마지막 리밸런싱 비중 추출
    """
    request = db.query(models.BacktestRequest).filter(models.BacktestRequest.data_id == data_id).first()
    if not request:
        return None

    # nav_result에서 NAV 리스트 추출
    nav_data = request.nav_result or []
    if len(nav_data) < 2:
        return None

    # 날짜순 정렬 후 nav만 추출
    sorted_nav = sorted(nav_data, key=lambda x: x["date"])
    nav_list = [float(row["nav"]) for row in sorted_nav]

    # 통계 계산
    total_return = nav_list[-1] / 1000 - 1
    num_years = len(nav_list) / 12
    cagr = (nav_list[-1] / 1000)**(1/num_years) - 1 if num_years > 0 else 0
    monthly_returns = pd.Series(nav_list).pct_change().dropna()
    volatility = monthly_returns.std() * (12 ** 0.5)
    sharpe = cagr / volatility if volatility > 0 else 0
    running_max = np.maximum.accumulate(nav_list)
    drawdowns = [nav / peak - 1 for nav, peak in zip(nav_list, running_max)]
    mdd = min(drawdowns)

    # rebalance_result에서 가장 최근 날짜 추출
    rebalance_data = request.rebalance_result or []
    if rebalance_data:
        # 가장 최근 날짜 entry 가져오기
        last_entry = max(rebalance_data, key=lambda x: x["date"])
        weights_dict = last_entry.get("weights", {})  # weights 딕셔너리 꺼내기
        weights = [(ticker, weight) for ticker, weight in weights_dict.items()]
    else:
        weights = []

    return {
        "input": {
            "start_year": request.start_year,
            "start_month": request.start_month,
            "invest": request.initial_balance,
            "trade_date": request.trade_day,
            "cost": float(request.fee_rate),
            "caculate_month": request.weight_months
        },
        "output": {
            "data_id": data_id,
            "total_return": round(total_return, 4),
            "cagr": round(cagr, 4),
            "vol": round(volatility, 4),
            "sharpe": round(sharpe, 4),
            "mdd": round(mdd, 4)
        },
        "last_rebalance_weight": weights
    }


def delete_input(db: Session, data_id: int):
    """ data_id로 BacktestRequest 모델 조회 및 삭제(타 테이블은 CASCADE)"""
    request = db.query(models.BacktestRequest).filter_by(data_id=data_id).first()
    if not request:
        raise ValueError(f"data_id {data_id} not found")
    db.delete(request) 
    db.commit()
    return True


def test_backtest_df(db : Session, start_year: int, start_month:int, trade_day : int, weight_months:int,fee_rate:float):
    start_date = get_weekday(date(start_year,start_month,trade_day))
    df_prices = get_prices(db,start_date,weight_months)
    if df_prices.empty:
        return {'error':"가격데이터를 찾을 수 없습니다."}
    if weight_months >= start_month:
        set_month = start_month - weight_months + 12
        set_year = start_year-1
    else : 
        set_month = start_month - weight_months
        set_year = start_year
    trade_dates = pd.date_range(start=pd.Timestamp(set_year,set_month,1), end=df_prices.index[-1],freq='MS')
    trade_dates = [get_valid_date(date,trade_day) for date in trade_dates]
    valid_trade_dates = [d for d in trade_dates if d in df_prices.index]
    df = df_prices.loc[valid_trade_dates]
    raw_columns = df.columns 
    etfs = raw_columns.drop(['BIL','TIP']) 
    for col in raw_columns:
        df[f'prev_{col}'] = df[col].shift(weight_months)
    df_cal = df.loc[start_date:].copy()
    for col in raw_columns:
        df_cal[f'wb_{col}'] = (df_cal[col] - df_cal[f'prev_{col}'])/df_cal[f'prev_{col}']
        if col != 'TIP':
            df_cal[f'rb_{col}'] = float(0)
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
    for col in raw_columns:
        df_cal[f'prev_{col}'] = df[col].shift(1).loc[start_date:]
        df_cal[f'wb_{col}'] = df_cal[col]/df_cal[f'prev_{col}']
    balances = raw_columns.drop('TIP') # 헷징수단인 BIL 포함 ETFs
    for col in balances:
        df_cal.loc[df_cal.index[0], f'wb_{col}'] = 0.0
        
    df_t = pd.DataFrame(index=df_cal.index).reset_index()
    df_t.rename(columns={"index": "date"}, inplace=True)

    for col in raw_columns:
        df_t[col] = df_cal[col].values
    for col in balances:
        df_t[f'rb_{col}'] = df_cal[f'rb_{col}'].values
    
    return df_t.round(2).to_dict(orient="records")