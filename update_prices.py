import datetime
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from bs4 import BeautifulSoup
from urllib.request import Request,urlopen
from api.models import ETFPrice

DATABASE_URL = "postgresql://backtest:backtest@127.0.0.1:5432/backtest"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind = engine)
session = SessionLocal()

today = datetime.date.today()

try : 
    tickers = ['SPY','QQQ','GLD','TIP','BIL']
    update_rows = 0
    
    for ticker in tickers:
        url = Request(f"https://finance.yahoo.com/quote/{ticker}/history/", headers={'User-Agent':'Mozilla/5.0'})
        html = urlopen(url)
        soup = BeautifulSoup(html,"html.parser")
        new_price = float(soup.select('tr td')[5].text)
        
        existing = session.query(ETFPrice).filter(
            ETFPrice.ticker == ticker,
            ETFPrice.date == today
        ).first()
        
        if not existing:
            session.add(ETFPrice(ticker=ticker,date=today,price=new_price))
            update_rows += 1
    session.commit()
    print(f"{update_rows}개의 가격 데이터가 업데이트 되었습니다. \n 날짜 : {today}")
    
except Exception as e:
    session.rollback()
    print(f"에러 발생 : {e}")

finally:
    session.close()