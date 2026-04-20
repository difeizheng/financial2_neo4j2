#!/bin/bash
# 财务模型知识图谱启动脚本
cd "$(dirname "$0")"
export PYTHONPATH="$(dirname "$0")"
streamlit run financial_kg/web/app.py --server.headless=true