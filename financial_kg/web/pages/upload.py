"""上传Excel页面"""
import streamlit as st
import os
import sys
from datetime import datetime
from pathlib import Path

# ===== 设置路径（必须在其他导入之前）=====
# upload.py 位于: project_root/financial_kg/web/pages/upload.py
project_root = Path(__file__).parent.parent.parent.parent  # 往上4层
if str(project_root.resolve()) not in sys.path:
    sys.path.insert(0, str(project_root.resolve()))

from financial_kg.config import get_config
from financial_kg.storage.task_db import TaskDB, Task


def render_upload_page():
    """渲染上传页面"""
    st.title("上传Excel文件")
    st.markdown("上传财务模型Excel文件，系统将解析为知识图谱。")

    config = get_config()
    task_db = TaskDB()

    # 文件上传区域
    uploaded_file = st.file_uploader(
        "选择Excel文件",
        type=["xlsx", "xls"],
        help="支持 .xlsx 和 .xls 格式",
    )

    if uploaded_file is not None:
        # 显示文件信息
        st.success(f"已选择: {uploaded_file.name}")
        st.info(f"文件大小: {uploaded_file.size / 1024:.1f} KB")

        # 保存文件
        save_path = config.uploads_dir / uploaded_file.name
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.session_state["uploaded_file"] = str(save_path)

        # 读取sheet列表
        import openpyxl
        wb = openpyxl.load_workbook(save_path, read_only=True)
        sheet_names = wb.sheetnames
        wb.close()

        # Sheet选择
        st.markdown("### 选择要解析的Sheet")
        st.info(f"Excel共有 {len(sheet_names)} 个sheet")

        # 快速选择按钮
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("选择全部"):
                st.session_state["target_sheets"] = sheet_names
        with col_btn2:
            if st.button("选择参数表"):
                # 查找参数输入表
                param_sheets = [s for s in sheet_names if "参数" in s or "输入" in s]
                if param_sheets:
                    st.session_state["target_sheets"] = param_sheets
        with col_btn3:
            if st.button("清空选择"):
                st.session_state["target_sheets"] = []

        # 获取当前选择（优先使用session_state）
        default_sheets = st.session_state.get("target_sheets", sheet_names[:4] if len(sheet_names) >= 4 else sheet_names)

        target_sheets = st.multiselect(
            "选择目标Sheet",
            sheet_names,
            default=default_sheets,
            help="建议：先选择参数输入表验证，确认无误后再选择全部sheet",
        )

        st.session_state["target_sheets"] = target_sheets

        # 显示选择统计
        if target_sheets:
            st.markdown(f"**已选择 {len(target_sheets)} 个sheet**: {', '.join(target_sheets)}")

            # 预估解析规模
            if len(target_sheets) > 4:
                st.warning(f"⚠️ 选择较多sheet ({len(target_sheets)}个)，解析时间可能较长。建议先解析4个sheet验证效果。")

        # 任务名称
        task_name = st.text_input(
            "任务名称",
            value=f"解析_{uploaded_file.name}_{datetime.now().strftime('%Y%m%d_%H%M')}",
        )

        # 开始解析按钮
        if st.button("开始解析", type="primary"):
            if len(target_sheets) == 0:
                st.error("请选择至少一个Sheet")
            else:
                # 创建任务
                task = Task(
                    name=task_name,
                    source_file=str(save_path),
                    target_sheets=target_sheets,
                    status="pending",
                )
                task_id = task_db.create_task(task)

                st.session_state["current_task_id"] = task_id

                st.success(f"任务已创建! ID: {task_id}")
                st.balloons()

                # 提示跳转
                st.markdown("---")
                st.info("👉 请前往 **解析状态** 页面查看进度")

    # 显示最近上传的文件
    st.markdown("---")
    st.markdown("### 最近上传的文件")

    uploads = list(config.uploads_dir.glob("*.xlsx"))
    if uploads:
        for f in uploads[-5:]:
            st.text(f"{f.name} ({f.stat().st_size / 1024:.1f} KB)")
    else:
        st.text("暂无上传文件")