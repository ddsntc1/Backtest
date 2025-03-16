import pandas as pd
from sqlalchemy import create_engine
import sqlalchemy.types

def price_data(path):

    DATABASE_URL="postgresql://backtest:backtest@127.0.0.1:5432/backtest"
    engine = create_engine(DATABASE_URL)

    try:
        df = pd.read_csv(path)
        tickers = [col for col in df.columns if col != 'date']
        df['date'] = pd.to_datetime(df['date'])

        df_m = df.melt(
            id_vars=['date'],
            value_vars=tickers,
            var_name='ticker',
            value_name='price'
        )

        dtype = {
            'date' : sqlalchemy.types.Date(),
            'ticker': sqlalchemy.types.VARCHAR(10),
            'price' : sqlalchemy.types.Numeric(13,4)
        }

        total = len(df_m)
        df_m = df_m.dropna()
        if len(df_m) < total:
            print(f'결측치가 {total - len(df_m)}개 제거되었습니다.')
        
        
        df_m.to_sql(
            'prices',
            engine,
            if_exists='append',
            index=False,
            method='multi',
            dtype=dtype,
            chunksize=1000,
            )
        
        print(f'데이터 입력이 완료되었습니다. \n DB 주소 : {DATABASE_URL} \n 입력 데이터 수 : {len(df_m)}')
        
    except Exception as e:
        print(f"에러 발생 : {e}")
        return False
    
if __name__ == "__main__":
    file_path = 'data/price_data.csv'
    price_data(file_path)