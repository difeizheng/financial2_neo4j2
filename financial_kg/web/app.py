"""Streamlit 主应用"""
import streamlit as st
import sys
import os
from pathlib import Path

# ===== 关键：必须在任何其他导入之前设置路径 =====
# app.py 位于: project_root/financial_kg/web/app.py
# 需要 project_root 在 sys.path 中
project_root = Path(__file__).parent.parent.parent  # 往上3层到项目根目录
project_root_str = str(project_root.resolve())
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

# 页面配置
st.set_page_config(
    page_title="财务模型知识图谱",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 导入页面模块（绝对导入）
from financial_kg.web.pages.upload import render_upload_page
from financial_kg.web.pages.parse_status import render_parse_status_page
from financial_kg.web.pages.graph_view import render_graph_view_page
from financial_kg.web.pages.cell_detail import render_cell_detail_page

# 导入配置和数据库
from financial_kg.config import get_config
from financial_kg.storage.task_db import TaskDB

# 侧边栏导航
st.sidebar.title("财务模型知识图谱")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "导航",
    ["上传Excel", "解析状态", "图谱浏览", "单元格详情"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 系统状态")

# 显示系统状态
config = get_config()
task_db = TaskDB()

tasks = task_db.get_tasks(limit=100)
st.sidebar.metric("任务总数", len(tasks))
st.sidebar.metric("已完成", len([t for t in tasks if t.status == "completed"]))

# 根据选择渲染页面
if page == "上传Excel":
    render_upload_page()
elif page == "解析状态":
    render_parse_status_page()
elif page == "图谱浏览":
    render_graph_view_page()
elif page == "单元格详情":
    render_cell_detail_page()