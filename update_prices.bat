@echo off
cd /d "%~dp0"  

:: 가상환경 활성화
call "..\backtest\Scripts\activate.bat"

python update_prices.py
