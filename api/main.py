from fastapi import FastAPI,Depends
from sqlalchemy.orm import Session
from .database import engine, get_db

app = FastAPI(title = "트리플더블 과제테스트")

@app.get("/")
def read_root():
    return {"message" : "안녕하세요. 지원자 강동욱 입니다."}