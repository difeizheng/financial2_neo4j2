"""Streamlit 应用入口"""
import sys
import os

# 确保模块路径正确
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web.app import main

if __name__ == "__main__":
    import streamlit.cli
    streamlit.cli.main_run(os.path.join(os.path.dirname(__file__), "web", "app.py"), [])