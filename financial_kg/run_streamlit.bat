@echo off
REM 财务模型知识图谱启动脚本
cd /d "%~dp0"
set PYTHONPATH=%~dp0
streamlit run financial_kg\web\app.py --server.headless=true
pause