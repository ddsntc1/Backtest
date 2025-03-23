@echo off
cd /d "%~dp0"  
call "..\backtest\Scripts\activate.bat"
python update_prices.py
