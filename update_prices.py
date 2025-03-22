import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import datetime
import logging
from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker
from bs4 import BeautifulSoup
from urllib.request import Request,urlopen


DATABASE_URL = "postgresql://backtest:backtest@127.0.0.1:5432/backtest"

logging.basicConfig(
    filename="update_prices.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding='utf-8'
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind = engine)
session = SessionLocal()

today = datetime.date.today()
now_kst = datetime.datetime.now() 
now_est = now_kst - datetime.timedelta(hours=14)  # KST → EST (UTC-5)
today_est = now_est.date()  # 날짜만 추출

# if today_est.weekday() in [5, 6]:
#     logging.info(f"EST 기준 {today_est}는 주말이므로 가격 업데이트를 실행하지 않습니다. ")
#     exit()  
    
tickers_db = session.execute(text("SELECT DISTINCT ticker FROM prices"))
tickers = [row[0] for row in tickers_db.fetchall()]

def fetch_price(ticker):
    """ ETF 가격 데이터를 가져오는 함수"""
    try:
        url = Request(f"https://finance.yahoo.com/quote/{ticker}/history/", headers={'User-Agent': 'Mozilla/5.0'})
        html = urlopen(url)
        soup = BeautifulSoup(html, "html.parser")
        new_price = float(soup.select('tr td')[5].text)

        return new_price

    except Exception as e:
        logging.error(f"{ticker} 데이터 수집 실패: {e}")
        return None

def update_prices():
    """ 데이터를 DB에 업데이트하는 함수"""
    session = SessionLocal()
    update_rows = 0
    which_tk = []
    try:
        for ticker in tickers:
            new_price = fetch_price(ticker)
            if new_price is None:
                continue  # 가격을 가져오지 못한 경우 건너뜀

            existing_query = text("SELECT id FROM prices WHERE ticker = :ticker AND date = :date")
            existing = session.execute(existing_query, {"ticker": ticker, "date": today_est}).fetchone()


            # 기존 데이터가 없거나 가격이 변동된 경우만 업데이트
            if not existing:
                insert_query = text("""
                    INSERT INTO prices (date, ticker, price) 
                    VALUES (:date, :ticker, :price)
                """)
                session.execute(insert_query, {"date": today_est, "ticker": ticker, "price": new_price})
                update_rows += 1
                which_tk.append(ticker)

        session.commit()
        logging.info(f"{update_rows}개의 가격 데이터가 업데이트 되었습니다. ETF : {[tk for tk in which_tk]} (EST 시간 : {now_est})")

    except Exception as e:
        session.rollback()
        logging.error(f"데이터베이스 업데이트 실패: {e}")

    finally:
        session.close()
        
if __name__ == "__main__":
    update_prices()