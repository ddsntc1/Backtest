from fastapi import FastAPI
from routes import backtest

app = FastAPI(title = "트리플더블 과제테스트")

app.include_router(backtest.router)
