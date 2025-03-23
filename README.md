# ETF Backtesting API

[자가평가.md](자가평가.md)

## 🔧 가상환경 세팅 및 의존성 설치

### 1. Python 가상환경 생성

```bash
# .bat실행에 문제없도록 'backtest'명의 가상환경을 github와 동일 디렉토리에 설치 부탁드립니다.
# .
# ├── Backtest  -> 가상환경
# ├── Project /
# │   ├── api_test
# │   ├── data
# │   ├── import_price_data
# │   └── ...

python -m venv backtest
```


### 2. 가상환경 활성화

- **Windows**
  ```bash
  backtest\Scripts\activate
  ```

- **Linux**
  ```bash
  source backtest/bin/activate
  ```

### 3. 패키지 설치

```bash
# 프로젝트 폴더/
pip install -r requirements.txt
```

---

## 🏃 프로젝트 실행

### 1. FastAPI 서버 실행

```bash
uvicorn main:app --reload
```

### 2. Swagger 문서 확인
- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🗃️ Database 설정

PostgreSQL에서 `backtest` DB와 유저를 아래와 같이 생성합니다:

```sql
CREATE DATABASE backtest;
CREATE USER backtest WITH PASSWORD 'backtest';
GRANT ALL PRIVILEGES ON DATABASE backtest TO backtest;
```

> DB 연결 정보는 `.env` 또는 `DATABASE_URL` 환경변수로 관리합니다.

> DATABASE_URL = "postgresql://backtest:backtest@127.0.0.1:5432/backtest"

---
## 📦 import_price_data (초기 가격 데이터)
과제 내용 중 주어진 가격데이터를 데이터베이스에 넣는 과정 입니다.
```bash
# 프로젝트 폴더/
python import_price_data.py
```



## 📦 배치 프로그램 (증시 마감 후 가격 업데이트)

ETF 가격을 정기적으로 업데이트하기 위한 배치 스크립트입니다.

### ▶ Windows – `.bat` 파일

**`update_prices.bat` 예시**

```bat
@echo off
cd /d "%~dp0"  
call "..\{가상환경 이름름}\Scripts\activate.bat"
python update_prices.py
```

- 작업 스케줄러(Task Scheduler)에서 `.bat` 파일을 원하는 시간대에 실행 등록

- 크롤링 시 EST 시간으로 진행하기 때문에 현재 시간인 KST(UTC+9) 기준 오전 8시에 실행시키도록 등록하면 됩니다.

### ▶ Linux – `cronjob` 등록

**1. 편집기 열기**
```bash
crontab -e
```

**2. 아래 내용 추가 (KST 기준 매일 오전 8시 실행)**
```cron
0 8 * * * /home/username/가상환경 경로/bin/python /home/username/프로젝트 경로/update_prices.py
```

> `venv` 경로와 `update_prices.py` 경로는 실제 환경에 맞게 수정해주세요.

---
## 📓 Prices 테이블 초기화
테스트 진행 중 bat 파일을 실행시키면 데이터가 입력 될 것이라 생각하여 편리한 테스트를 위해 아래 SQL문을 넣었습니다.
```sql
# psql내 실행 -> 기존 데이터 삭제 및 인덱스 초기화
TRUNCATE TABLE prices RESTART IDENTITY;
```

DB초기화 이후 import_price_data를 다시한번 실행시키면 문제없이 진행 될 것이라 생각합니다.
```
python import_price_data.py
```



## 📁 프로젝트 구조 예시

```

.
├── api_test/
│   ├── main.py
│   ├── database.py
│   ├── schemas.bat
│   ├── routes/
│   ├── services/
│   └── migrations/
├── data/
│   └── price_data.csv
├── requirements.txt
├── update_prices.bat
├── update_prices.log
└── update_prices.py
```

---

## 📌 기타 참고 사항
- 주말(EST 기준)에는 가격이 업데이트되지 않습니다.
---
