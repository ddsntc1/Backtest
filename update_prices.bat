@echo off
pushd /d "C:\Users\ddsnt\OneDrive\Desktop\tripledouble\project"

:: 가상환경 활성화
call "C:\Users\ddsnt\OneDrive\Desktop\tripledouble\backtest\Scripts\activate.bat"

:: PYTHONPATH 환경 변수 설정 후 실행
set PYTHONPATH=C:\Users\ddsnt\OneDrive\Desktop\tripledouble\project
python update_prices.py

pause